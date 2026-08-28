"""Facts-only Bear Zone threshold sensitivity diagnostics."""

from __future__ import annotations

from typing import Any

from ml.clustering.base import ClusterPoint
from ml.clustering.bear_zones import BearZoneDetector
from ml.spatial.graph import SpatialGraph, SpatialGraphBuilder

DEFAULT_BEAR_THRESHOLDS = (0.20, 0.25, 0.30, 0.35, 0.40, 0.50)


def bear_threshold_sensitivity(
    points: list[ClusterPoint],
    *,
    graph: SpatialGraph | None = None,
    thresholds: tuple[float, ...] = DEFAULT_BEAR_THRESHOLDS,
    singleton_threshold: float = 0.70,
) -> list[dict[str, Any]]:
    """Evaluate thresholds without selecting or recommending a winner."""
    selected_graph = graph or SpatialGraphBuilder().build(points)
    detector = BearZoneDetector()
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        result = detector.fit(
            points,
            {
                "spatial_graph": selected_graph,
                "bear_threshold": threshold,
                "singleton_threshold": singleton_threshold,
            },
        )
        zones = [
            cluster for cluster in result.clusters if cluster.cluster_type == "bear_zone"
        ]
        singletons = [
            cluster
            for cluster in result.clusters
            if cluster.cluster_type == "expensive_singleton"
        ]
        rows.append(
            {
                "bear_threshold_pct": 100 * threshold,
                "candidate_count": result.metrics["candidate_count"],
                "zone_count": len(zones),
                "singleton_count": len(singletons),
                "covered_points": result.metrics["covered_point_count"],
                "covered_trip_count": result.metrics["covered_trip_count"],
                "mean_zone_size": result.metrics["mean_zone_size"],
                "max_zone_size": result.metrics["max_zone_size"],
                "zones": [
                    {
                        "cluster_id": cluster.cluster_id,
                        "point_ids": list(cluster.point_ids),
                        "point_count": cluster.point_count,
                        "trip_count": cluster.trip_count,
                        "weighted_rub_per_km": cluster.weighted_rub_per_km,
                        "relative_rate_delta": cluster.relative_rate_delta,
                    }
                    for cluster in zones
                ],
                "singletons": [
                    {
                        "point_id": cluster.point_ids[0],
                        "trip_count": cluster.trip_count,
                        "weighted_rub_per_km": cluster.weighted_rub_per_km,
                        "relative_rate_delta": cluster.relative_rate_delta,
                    }
                    for cluster in singletons
                ],
            }
        )
    return rows
