"""Run Geography, Geo+Cost and Bear Zones on one shared point/filter context."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ml.clustering.base import ClusterPoint, ClusterResult
from ml.clustering.bear_zones import BearZoneDetector
from ml.clustering.geo_cost import GeoCostClusterer
from ml.clustering.geographic import GeographicClusterer
from ml.evaluation.bear import bear_threshold_sensitivity
from ml.evaluation.spatial import graph_pruning_sensitivity
from ml.spatial.graph import SpatialGraphBuilder


def _git_sha() -> str | None:
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


def _hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _apply_context(
    result: ClusterResult, filters: dict[str, Any], data_quality: dict[str, Any]
) -> ClusterResult:
    periods = tuple(sorted(filters.get("period_types") or ()))
    prices = tuple(sorted(filters.get("price_types") or ()))
    vehicles = tuple(sorted(filters.get("vehicle_types") or ()))
    tonnages = tuple(sorted(filters.get("tonnage_ids") or ()))
    segment_details = {
        "mixed_price_types": len(prices) > 1,
        "mixed_vehicle_types": len(vehicles) > 1,
        "mixed_tonnages": len(tonnages) > 1,
    }
    warnings = []
    if "forecast" in periods:
        warnings.append("contains_forecast")
    if any(segment_details.values()):
        warnings.append("mixed_tariff_segments")
    return replace(
        result,
        filters=dict(filters),
        period_types=periods,
        price_types=prices,
        vehicle_types=vehicles,
        tonnage_ids=tonnages,
        contains_forecast="forecast" in periods,
        mixed_tariff_segments=any(segment_details.values()),
        mixed_segment_details=segment_details,
        data_quality=data_quality,
        warnings=tuple(warnings),
    )


def _mode_facts(result: ClusterResult) -> dict[str, Any]:
    return {
        "mode": result.mode,
        "clusters_or_zones": len(result.clusters),
        "spatial_outliers": sum(
            item.get("type") == "spatial_outlier" for item in result.outliers
        ),
        "mean_radius_m": result.metrics.get("mean_distance_to_medoid_m"),
        "p95_radius_m": result.metrics.get("p95_distance_to_medoid_m"),
        "rate_spread": result.metrics.get("between_cluster_rate_spread"),
        "trip_coverage_pct": result.metrics.get(
            "trip_coverage_pct", result.metrics.get("shipment_coverage_pct")
        ),
        "connectivity_violations": result.metrics.get("connectivity_violations"),
    }


def run_clustering_modes(
    points: list[ClusterPoint],
    *,
    filters: dict[str, Any],
    output_dir: str | Path | None = None,
    n_clusters: int | str = "auto",
    graph_method: str = "delaunay",
    graph_parameters: dict[str, Any] | None = None,
    source_data_quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not filters.get("origin_fias"):
        raise ValueError("filters.origin_fias is required")
    if not filters.get("destination_region"):
        raise ValueError("filters.destination_region is required")
    if len({point.region for point in points}) > 1:
        raise ValueError("All points must belong to one destination region")
    graph_options = dict(graph_parameters or {})
    graph_builder = SpatialGraphBuilder(method=graph_method, **graph_options)
    graph = graph_builder.build(points)
    default_graph_parameters = {"spatial_graph": graph, "n_clusters": n_clusters}
    data_quality = {
        **(source_data_quality or {}),
        "point_count": len(points),
        "missing_economics_point_count": sum(
            point.weighted_rub_per_km is None for point in points
        ),
        "zero_or_missing_trip_count_point_count": sum(
            point.trip_count <= 0 for point in points
        ),
        "flag_counts": {
            flag: sum(flag in point.data_quality_flags for point in points)
            for flag in sorted(
                {flag for point in points for flag in point.data_quality_flags}
            )
        },
    }
    geography = _apply_context(
        GeographicClusterer(graph_builder).fit(points, default_graph_parameters),
        filters,
        data_quality,
    )
    geo_cost_results = [
        _apply_context(
            GeoCostClusterer(graph_builder).fit(
                points,
                {
                    **default_graph_parameters,
                    "geography_weight": geography_weight,
                    "economics_weight": economics_weight,
                },
            ),
            filters,
            data_quality,
        )
        for geography_weight, economics_weight in ((0.8, 0.2), (0.7, 0.3), (0.6, 0.4))
    ]
    bear = _apply_context(
        BearZoneDetector(graph_builder).fit(
            points,
            {
                "spatial_graph": graph,
                "bear_threshold": 0.35,
                "singleton_threshold": 0.70,
            },
        ),
        filters,
        data_quality,
    )

    graph_study = {}
    for method, options in (
        ("delaunay", graph_options),
        ("mutual_knn", {**graph_options, "knn_k": graph_options.get("knn_k", 5)}),
    ):
        graph_study[method] = SpatialGraphBuilder(method=method, **options).build(points).audit
    points_payload = [asdict(point) for point in sorted(points, key=lambda item: item.id)]
    metadata = {
        "git_sha": _git_sha(),
        "dataset_hash": _hash(points_payload),
        "coordinate_hash": _hash(
            [(point.id, point.x, point.y) for point in sorted(points, key=lambda item: item.id)]
        ),
        "origin_fias": filters["origin_fias"],
        "destination_region": filters["destination_region"],
        "filters": filters,
        "graph_method": graph_method,
        "graph_parameters": graph.parameters,
        "graph_threshold_m": graph.audit["adaptive_edge_threshold_m"],
        "created_at": datetime.now(UTC).isoformat(),
    }
    report = {
        "metadata": metadata,
        "graph_study": graph_study,
        "graph_pruning_sensitivity": graph_pruning_sensitivity(points),
        "bear_threshold_sensitivity": bear_threshold_sensitivity(
            points, graph=graph
        ),
        "comparison": [
            _mode_facts(geography),
            *[_mode_facts(result) for result in geo_cost_results],
            _mode_facts(bear),
        ],
        "results": {
            "geography": geography.as_dict(),
            "geo_cost_sensitivity": [result.as_dict() for result in geo_cost_results],
            "bear_zones": bear.as_dict(),
        },
        "winner": None,
        "winner_policy": "facts_only; automatic product-mode selection is frozen",
    }
    if output_dir is not None:
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "clustering_modes.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report


def _csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_points(path: Path) -> tuple[list[ClusterPoint], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    points = []
    for item in payload:
        if item.get("x") is None or item.get("y") is None:
            continue
        points.append(
            ClusterPoint(
                id=str(item["id"]),
                name=str(item["name"]),
                region=str(item["region"]),
                x=float(item["x"]),
                y=float(item["y"]),
                trip_count=int(item.get("trip_count") or 0),
                weighted_price=(
                    float(item["weighted_price"])
                    if item.get("weighted_price") is not None
                    else None
                ),
                weighted_rub_per_km=(
                    float(item["weighted_rub_per_km"])
                    if item.get("weighted_rub_per_km") is not None
                    else None
                ),
                data_quality_flags=tuple(item.get("data_quality_flags") or ()),
            )
        )
    total_trips = sum(int(item.get("trip_count") or 0) for item in payload)
    resolved_trips = sum(point.trip_count for point in points)
    return points, {
        "destination_points_total": len(payload),
        "resolved_points": len(points),
        "unresolved_points": len(payload) - len(points),
        "point_coverage_pct": (
            100 * len(points) / len(payload) if payload else 0.0
        ),
        "trip_weight_coverage_pct": (
            100 * resolved_trips / total_trips if total_trips else 0.0
        ),
        "coordinate_source_distribution": {
            source: sum(
                item.get("coordinate_source") == source for item in payload
            )
            for source in sorted(
                {
                    str(item.get("coordinate_source") or "unknown")
                    for item in payload
                }
            )
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locations", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--origin-fias", required=True)
    parser.add_argument("--destination-region", required=True)
    parser.add_argument("--period-types", type=_csv_list, default=[])
    parser.add_argument("--price-types", type=_csv_list, default=[])
    parser.add_argument("--vehicle-types", type=_csv_list, default=[])
    parser.add_argument("--tonnage-ids", type=_csv_list, default=[])
    parser.add_argument("--n-clusters", default="auto")
    parser.add_argument("--graph-method", choices=("delaunay", "mutual_knn"), default="delaunay")
    parser.add_argument("--knn-k", type=int, default=5)
    parser.add_argument("--edge-mad-multiplier", type=float, default=3.0)
    parser.add_argument("--max-edge-m", type=float)
    args = parser.parse_args()
    n_clusters: int | str = (
        args.n_clusters
        if args.n_clusters == "auto"
        else int(args.n_clusters)
    )
    points, source_data_quality = _load_points(args.locations)
    report = run_clustering_modes(
        points,
        filters={
            "origin_fias": args.origin_fias,
            "destination_region": args.destination_region,
            "period_types": args.period_types,
            "price_types": args.price_types,
            "vehicle_types": args.vehicle_types,
            "tonnage_ids": args.tonnage_ids,
        },
        output_dir=args.output_dir,
        n_clusters=n_clusters,
        graph_method=args.graph_method,
        graph_parameters={
            "knn_k": args.knn_k,
            "edge_mad_multiplier": args.edge_mad_multiplier,
            "max_edge_m": args.max_edge_m,
        },
        source_data_quality=source_data_quality,
    )
    print(f"Completed {len(report['comparison'])} mode/sensitivity runs")
    print(f"Report: {args.output_dir / 'clustering_modes.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
