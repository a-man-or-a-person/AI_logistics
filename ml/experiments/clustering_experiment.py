"""Run reproducible geo-only and shipment-weighted clustering sweeps."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sklearn.metrics import adjusted_rand_score

from ml.clustering.base import ClusterPoint, ClusterResult
from ml.clustering.kmeans import KMeansClusterer
from ml.spatial.boundaries import load_region_boundary
from ml.spatial.boundary_manifest import load_boundary_manifest
from ml.spatial.projection import LocalProjection
from ml.spatial.territorialize import TerritorializationResult, territorialize


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _load_points(
    path: Path,
) -> tuple[list[ClusterPoint], list[dict[str, Any]], LocalProjection, dict[str, float]]:
    raw_locations = json.loads(path.read_text(encoding="utf-8"))
    resolved = [
        location
        for location in raw_locations
        if location.get("latitude") is not None and location.get("longitude") is not None
    ]
    if len(resolved) < 2:
        raise ValueError("At least two resolved locations are required")
    projection = LocalProjection.from_coordinates(
        (float(location["latitude"]), float(location["longitude"])) for location in resolved
    )
    points: list[ClusterPoint] = []
    for location in resolved:
        x, y = projection.project(float(location["latitude"]), float(location["longitude"]))
        points.append(
            ClusterPoint(
                id=str(location["id"]),
                name=str(location["name"]),
                region=str(location["region"]),
                x=x,
                y=y,
                shipment_count=float(location.get("shipment_count") or 0),
            )
        )
    total_shipments = sum(float(location.get("shipment_count") or 0) for location in raw_locations)
    resolved_shipments = sum(point.shipment_count for point in points)
    coverage = {
        "coordinate_coverage_pct": round(100 * len(resolved) / len(raw_locations), 4)
        if raw_locations
        else 0,
        "coordinate_shipment_coverage_pct": round(
            100 * resolved_shipments / total_shipments, 4
        )
        if total_shipments
        else 0,
    }
    return points, resolved, projection, coverage


def _stability_metrics(
    points: list[ClusterPoint], parameters: dict[str, Any], seeds: list[int]
) -> tuple[ClusterResult, dict[str, float | int | None]]:
    clusterer = KMeansClusterer()
    results = [clusterer.fit(points, {**parameters, "random_state": seed}) for seed in seeds]
    point_ids = [point.id for point in points]
    scores = [
        adjusted_rand_score(
            [left.point_assignments[point_id] for point_id in point_ids],
            [right.point_assignments[point_id] for point_id in point_ids],
        )
        for index, left in enumerate(results)
        for right in results[index + 1 :]
    ]
    return results[0], {
        "stability_runs": len(seeds),
        "stability_mean_ari": round(sum(scores) / len(scores), 6) if scores else 1.0,
        "stability_min_ari": round(min(scores), 6) if scores else 1.0,
    }


def _experiment_metadata(
    result: ClusterResult,
    *,
    dataset_hash: str,
    source_path: Path,
    region: str,
    origin_fias: str | None,
    projection: LocalProjection,
    coverage: dict[str, float],
    stability: dict[str, float | int | None],
) -> dict[str, Any]:
    identity = json.dumps(
        {"dataset_hash": dataset_hash, "algorithm": result.algorithm, **result.parameters},
        sort_keys=True,
    )
    return {
        "experiment_id": hashlib.sha256(identity.encode()).hexdigest()[:16],
        "git_commit": _git_commit(),
        "dataset_hash": dataset_hash,
        "source": "pulse_clustering_dataset",
        "source_path": str(source_path.resolve()),
        "region": region,
        "origin_fias": origin_fias,
        "algorithm": result.algorithm,
        "parameters": result.parameters,
        "location_count": len(result.point_assignments),
        "cluster_count": len(result.clusters),
        "cluster_metrics": {**result.metrics, **coverage, **stability},
        "projection": {
            "name": "local_azimuthal_equidistant",
            "center_latitude": projection.center_latitude,
            "center_longitude": projection.center_longitude,
        },
        "created_at_utc": datetime.now(UTC).isoformat(),
    }


def _write_run(
    output_dir: Path,
    result: ClusterResult,
    metadata: dict[str, Any],
    points: list[ClusterPoint],
    raw_locations: list[dict[str, Any]],
    territorialization: TerritorializationResult | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    location_by_id = {str(location["id"]): location for location in raw_locations}
    payload = {
        **metadata,
        "clusters": [
            {
                "cluster_id": cluster.cluster_id,
                "point_count": cluster.point_count,
                "shipment_count": cluster.shipment_count,
                "shipment_share": cluster.shipment_share,
                "centroid": cluster.centroid,
                "medoid_point_id": cluster.medoid_point_id,
                "medoid": cluster.medoid,
            }
            for cluster in result.clusters
        ],
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    boundary_metadata = metadata.get("boundary")
    if isinstance(boundary_metadata, dict) and isinstance(
        boundary_metadata.get("provenance"), dict
    ):
        (output_dir / "boundary_manifest.json").write_text(
            json.dumps(boundary_metadata["provenance"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if territorialization is not None:
        (output_dir / "zones.geojson").write_text(
            json.dumps(territorialization.zones_geojson, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    fields = [
        "id", "name", "region", "latitude", "longitude", "x", "y",
        "shipment_count", "cluster_id",
    ]
    with (output_dir / "assignments.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for point in points:
            raw = location_by_id[point.id]
            writer.writerow(
                {
                    "id": point.id,
                    "name": point.name,
                    "region": point.region,
                    "latitude": raw["latitude"],
                    "longitude": raw["longitude"],
                    "x": round(point.x, 4),
                    "y": round(point.y, 4),
                    "shipment_count": point.shipment_count,
                    "cluster_id": result.point_assignments[point.id],
                }
            )


def _pareto_shortlist(rows: list[dict[str, Any]]) -> list[str]:
    """Return non-dominated clustering runs across quality dimensions."""
    def high(row: dict[str, Any], key: str) -> float:
        return float(row[key]) if row[key] is not None else float("-inf")

    def low(row: dict[str, Any], key: str) -> float:
        return float(row[key]) if row[key] is not None else float("inf")

    def dominates(left: dict[str, Any], right: dict[str, Any]) -> bool:
        maximize = ("stability_mean_ari", "silhouette")
        minimize = ("weighted_p95_radius_km", "shipment_share_cv")
        better_or_equal = all(high(left, key) >= high(right, key) for key in maximize) and all(
            low(left, key) <= low(right, key) for key in minimize
        )
        strictly_better = any(high(left, key) > high(right, key) for key in maximize) or any(
            low(left, key) < low(right, key) for key in minimize
        )
        return better_or_equal and strictly_better

    return [
        row["experiment_id"]
        for row in rows
        if not any(other is not row and dominates(other, row) for other in rows)
    ]


def _to_km(value: object) -> float | None:
    return round(float(value) / 1000, 4) if value is not None else None


def run_kmeans_sweep(
    locations_path: str | Path,
    *,
    output_dir: str | Path,
    k_values: range | list[int],
    weight_mode: str = "both",
    random_state: int = 42,
    stability_runs: int = 5,
    region: str | None = None,
    origin_fias: str | None = None,
    boundary_path: str | Path | None = None,
    boundary_region_name: str | None = None,
    boundary_manifest_path: str | Path | None = None,
    require_official_boundary: bool = False,
    cell_size_m: float = 2_000,
) -> list[dict[str, Any]]:
    source_path = Path(locations_path)
    destination = Path(output_dir)
    points, raw_locations, projection, coordinate_coverage = _load_points(source_path)
    selected_region = region or points[0].region
    dataset_hash = _file_hash(source_path)
    modes = ["none", "shipment_count"] if weight_mode == "both" else [weight_mode]
    if any(mode not in {"none", "shipment_count"} for mode in modes):
        raise ValueError("weight_mode must be none, shipment_count, or both")
    seeds = list(range(random_state, random_state + max(stability_runs, 1)))
    boundary_source = Path(boundary_path) if boundary_path is not None else None
    boundary = (
        load_region_boundary(boundary_source, region_name=boundary_region_name)
        if boundary_source is not None
        else None
    )
    boundary_manifest = (
        load_boundary_manifest(
            boundary_manifest_path,
            boundary_path=boundary_source,
            require_official=require_official_boundary,
        )
        if boundary_manifest_path is not None
        else None
    )
    if require_official_boundary and boundary is not None and boundary_manifest is None:
        raise ValueError("Official territorialization requires --boundary-manifest")
    leaderboard: list[dict[str, Any]] = []
    results_by_key: dict[tuple[int, str], ClusterResult] = {}

    for k in k_values:
        for mode in modes:
            result, stability = _stability_metrics(
                points, {"n_clusters": k, "weight_mode": mode}, seeds
            )
            results_by_key[(k, mode)] = result
            metadata = _experiment_metadata(
                result,
                dataset_hash=dataset_hash,
                source_path=source_path,
                region=selected_region,
                origin_fias=origin_fias,
                projection=projection,
                coverage=coordinate_coverage,
                stability=stability,
            )
            territorialization = None
            if boundary is not None:
                territorialization = territorialize(
                    points, result, boundary, projection, cell_size_m=cell_size_m
                )
                metadata["boundary"] = {
                    "source_path": str(boundary_source.resolve()),
                    "sha256": _file_hash(boundary_source),
                    "region_name_selector": boundary_region_name,
                    "provenance": (
                        {
                            "region": boundary_manifest.region,
                            "authority": boundary_manifest.authority,
                            "source_type": boundary_manifest.source_type,
                            "retrieved_at": boundary_manifest.retrieved_at,
                            "effective_date": boundary_manifest.effective_date,
                            "crs": boundary_manifest.crs,
                            "sha256": boundary_manifest.sha256,
                            "status": boundary_manifest.status,
                            "official": boundary_manifest.official,
                        }
                        if boundary_manifest
                        else {"status": "unknown", "official": False}
                    ),
                }
                metadata["territorialization_metrics"] = territorialization.metrics
            run_name = f"kmeans_k{k}_{mode}" if len(modes) > 1 else f"kmeans_k{k}"
            _write_run(
                destination / run_name, result, metadata, points, raw_locations, territorialization
            )
            metrics = {**result.metrics, **coordinate_coverage, **stability}
            leaderboard.append(
                {
                    "experiment_id": metadata["experiment_id"],
                    "algorithm": result.algorithm,
                    "K": k,
                    "weight_mode": mode,
                    "silhouette": metrics["silhouette"],
                    "mean_radius_km": _to_km(metrics["mean_distance_to_medoid_m"]),
                    "p95_radius_km": _to_km(metrics["p95_distance_to_medoid_m"]),
                    "max_radius_km": _to_km(metrics["max_distance_to_medoid_m"]),
                    "weighted_mean_radius_km": _to_km(
                        metrics["weighted_mean_distance_to_medoid_m"]
                    ),
                    "weighted_p95_radius_km": _to_km(
                        metrics["weighted_p95_distance_to_medoid_m"]
                    ),
                    "min_cluster_points": metrics["min_cluster_size"],
                    "max_cluster_points": metrics["max_cluster_size"],
                    "min_shipment_share": metrics["min_shipment_share"],
                    "max_shipment_share": metrics["max_shipment_share"],
                    "shipment_share_cv": metrics["shipment_share_cv"],
                    "point_coverage_pct": metrics["point_coverage_pct"],
                    "shipment_coverage_pct": metrics["shipment_coverage_pct"],
                    "coordinate_coverage_pct": metrics["coordinate_coverage_pct"],
                    "coordinate_shipment_coverage_pct": metrics[
                        "coordinate_shipment_coverage_pct"
                    ],
                    "stability_mean_ari": metrics["stability_mean_ari"],
                    "stability_min_ari": metrics["stability_min_ari"],
                    "weight_sensitivity_ari": None,
                    "weight_sensitivity_p95_radius_delta_km": None,
                    "weight_sensitivity_weighted_radius_delta_km": None,
                    "weight_sensitivity_shipment_balance_cv_delta": None,
                    "polygon_status": "generated" if territorialization else "not_requested",
                    "polygon_coverage_pct": territorialization.metrics["coverage_pct"]
                    if territorialization
                    else None,
                    "polygon_overlap_pct": territorialization.metrics["overlap_pct"]
                    if territorialization
                    else None,
                    "fragmented_zone_count": territorialization.metrics[
                        "fragmented_zone_count"
                    ]
                    if territorialization
                    else None,
                }
            )

    for k in k_values:
        if (k, "none") not in results_by_key or (k, "shipment_count") not in results_by_key:
            continue
        left = results_by_key[(k, "none")]
        right = results_by_key[(k, "shipment_count")]
        point_ids = [point.id for point in points]
        ari = round(
            adjusted_rand_score(
                [left.point_assignments[item] for item in point_ids],
                [right.point_assignments[item] for item in point_ids],
            ),
            6,
        )
        for row in leaderboard:
            if row["K"] == k:
                row["weight_sensitivity_ari"] = ari
        by_mode = {row["weight_mode"]: row for row in leaderboard if row["K"] == k}
        plain, weighted = by_mode["none"], by_mode["shipment_count"]
        p95_delta = weighted["p95_radius_km"] - plain["p95_radius_km"]
        weighted_delta = (
            weighted["weighted_p95_radius_km"] - plain["weighted_p95_radius_km"]
        )
        balance_delta = weighted["shipment_share_cv"] - plain["shipment_share_cv"]
        for row in by_mode.values():
            row["weight_sensitivity_p95_radius_delta_km"] = round(p95_delta, 4)
            row["weight_sensitivity_weighted_radius_delta_km"] = round(weighted_delta, 4)
            row["weight_sensitivity_shipment_balance_cv_delta"] = round(balance_delta, 6)

    shortlist = _pareto_shortlist(leaderboard)
    for row in leaderboard:
        row["pareto_shortlist"] = row["experiment_id"] in shortlist
    destination.mkdir(parents=True, exist_ok=True)
    with (destination / "leaderboard.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(leaderboard[0]) if leaderboard else ["algorithm"])
        writer.writeheader()
        writer.writerows(leaderboard)
    decision_gate = {
        "data_readiness": coordinate_coverage,
        "candidate_runs": [row["experiment_id"] for row in leaderboard],
        "stability": {row["experiment_id"]: row["stability_mean_ari"] for row in leaderboard},
        "geographic_quality": {
            row["experiment_id"]: row["weighted_p95_radius_km"] for row in leaderboard
        },
        "volume_balance": {
            row["experiment_id"]: row["shipment_share_cv"] for row in leaderboard
        },
        "territorialization": {
            "status": "evaluated" if boundary is not None else "optional_not_provided"
        },
        "shortlist": shortlist,
        "blockers": [],
    }
    (destination / "decision_gate_clustering.json").write_text(
        json.dumps(decision_gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return leaderboard


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locations", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--k-min", type=int, default=2)
    parser.add_argument("--k-max", type=int, default=10)
    parser.add_argument(
        "--weight-mode", choices=("none", "shipment_count", "both"), default="both"
    )
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--stability-runs", type=int, default=5)
    parser.add_argument("--region")
    parser.add_argument("--origin-fias")
    parser.add_argument("--boundary", type=Path)
    parser.add_argument("--boundary-region-name")
    parser.add_argument("--boundary-manifest", type=Path)
    parser.add_argument("--require-official-boundary", action="store_true")
    parser.add_argument("--cell-size-m", type=float, default=2_000)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    leaderboard = run_kmeans_sweep(
        args.locations,
        output_dir=args.output_dir,
        k_values=range(args.k_min, args.k_max + 1),
        weight_mode=args.weight_mode,
        random_state=args.random_state,
        stability_runs=args.stability_runs,
        region=args.region,
        origin_fias=args.origin_fias,
        boundary_path=args.boundary,
        boundary_region_name=args.boundary_region_name,
        boundary_manifest_path=args.boundary_manifest,
        require_official_boundary=args.require_official_boundary,
        cell_size_m=args.cell_size_m,
    )
    print(f"Completed {len(leaderboard)} K-Means experiments")
    print(f"Leaderboard: {args.output_dir / 'leaderboard.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
