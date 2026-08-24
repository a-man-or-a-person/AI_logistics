"""Run reproducible geography-only clustering sweeps on canonical locations."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ml.clustering.base import ClusterPoint, ClusterResult
from ml.clustering.kmeans import KMeansClusterer
from ml.spatial.projection import LocalProjection


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _load_points(
    path: Path,
) -> tuple[list[ClusterPoint], list[dict[str, Any]], LocalProjection]:
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
    points = []
    for location in resolved:
        x, y = projection.project(float(location["latitude"]), float(location["longitude"]))
        points.append(
            ClusterPoint(
                id=str(location["id"]),
                name=str(location["name"]),
                region=str(location["region"]),
                x=x,
                y=y,
                trip_count=int(location.get("trip_count") or 0),
            )
        )
    return points, resolved, projection


def _experiment_metadata(
    result: ClusterResult,
    *,
    dataset_hash: str,
    source_path: Path,
    region: str,
    origin_fias: str | None,
    projection: LocalProjection,
) -> dict[str, Any]:
    identity = json.dumps(
        {"dataset_hash": dataset_hash, "algorithm": result.algorithm, **result.parameters},
        sort_keys=True,
    )
    experiment_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return {
        "experiment_id": experiment_id,
        "git_commit": _git_commit(),
        "dataset_hash": dataset_hash,
        "source": "pulse",
        "source_path": str(source_path.resolve()),
        "region": region,
        "origin_fias": origin_fias,
        "period": "all",
        "algorithm": result.algorithm,
        "parameters": result.parameters,
        "location_count": len(result.point_assignments),
        "cluster_count": len(result.clusters),
        "metrics": result.metrics,
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
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    location_by_id = {str(location["id"]): location for location in raw_locations}
    (output_dir / "metrics.json").write_text(
        json.dumps({**metadata, "clusters": [
            {
                "cluster_id": cluster.cluster_id,
                "point_count": cluster.point_count,
                "trip_count": cluster.trip_count,
                "centroid": cluster.centroid,
                "medoid_point_id": cluster.medoid_point_id,
                "medoid": cluster.medoid,
            }
            for cluster in result.clusters
        ]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    fieldnames = [
        "id",
        "name",
        "region",
        "latitude",
        "longitude",
        "x",
        "y",
        "trip_count",
        "cluster_id",
    ]
    with (output_dir / "assignments.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
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
                    "trip_count": point.trip_count,
                    "cluster_id": result.point_assignments[point.id],
                }
            )


def run_kmeans_sweep(
    locations_path: str | Path,
    *,
    output_dir: str | Path,
    k_values: range | list[int],
    weight_mode: str = "none",
    random_state: int = 42,
    region: str | None = None,
    origin_fias: str | None = None,
) -> list[dict[str, Any]]:
    source_path = Path(locations_path)
    destination = Path(output_dir)
    points, raw_locations, projection = _load_points(source_path)
    selected_region = region or points[0].region
    dataset_hash = _file_hash(source_path)
    clusterer = KMeansClusterer()
    leaderboard: list[dict[str, Any]] = []
    for k in k_values:
        result = clusterer.fit(
            points,
            {"n_clusters": k, "weight_mode": weight_mode, "random_state": random_state},
        )
        metadata = _experiment_metadata(
            result,
            dataset_hash=dataset_hash,
            source_path=source_path,
            region=selected_region,
            origin_fias=origin_fias,
            projection=projection,
        )
        _write_run(destination / f"kmeans_k{k}", result, metadata, points, raw_locations)
        leaderboard.append(
            {
                "experiment_id": metadata["experiment_id"],
                "algorithm": result.algorithm,
                "parameters": json.dumps(result.parameters, ensure_ascii=False, sort_keys=True),
                "zones": len(result.clusters),
                "noise_pct": result.metrics["noise_pct"],
                "silhouette": result.metrics["silhouette"],
                "mean_radius_km": round(
                    float(result.metrics["mean_distance_to_medoid_m"]) / 1000, 4
                ),
                "p95_radius_km": round(
                    float(result.metrics["p95_distance_to_medoid_m"]) / 1000, 4
                ),
                "max_radius_km": round(
                    float(result.metrics["max_distance_to_medoid_m"]) / 1000, 4
                ),
                "point_coverage_pct": result.metrics["point_coverage_pct"],
                "polygon_coverage_pct": None,
                "wape": None,
                "stability": None,
                "fragmentation": None,
            }
        )
    destination.mkdir(parents=True, exist_ok=True)
    leaderboard_path = destination / "leaderboard.csv"
    with leaderboard_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(leaderboard[0]) if leaderboard else ["algorithm"])
        writer.writeheader()
        writer.writerows(leaderboard)
    return leaderboard


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locations", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--k-min", type=int, default=2)
    parser.add_argument("--k-max", type=int, default=10)
    parser.add_argument("--weight-mode", choices=("none", "trip_count"), default="none")
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--region")
    parser.add_argument("--origin-fias")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    leaderboard = run_kmeans_sweep(
        args.locations,
        output_dir=args.output_dir,
        k_values=range(args.k_min, args.k_max + 1),
        weight_mode=args.weight_mode,
        random_state=args.random_state,
        region=args.region,
        origin_fias=args.origin_fias,
    )
    print(f"Completed {len(leaderboard)} K-Means experiments")
    print(f"Leaderboard: {args.output_dir / 'leaderboard.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
