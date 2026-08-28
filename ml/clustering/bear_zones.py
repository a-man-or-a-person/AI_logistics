"""Detect connected high-cost territories without forcing a K partition."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ml.clustering.base import Clusterer, ClusterPoint, ClusterResult, summarize_assignments
from ml.clustering.economics import relative_rate_delta, weighted_mean
from ml.spatial.graph import SpatialGraph, SpatialGraphBuilder


class BearZoneDetector(Clusterer):
    algorithm = "connected_high_cost_components"

    def __init__(self, graph_builder: SpatialGraphBuilder | None = None) -> None:
        self.graph_builder = graph_builder or SpatialGraphBuilder()

    def fit(
        self, points: list[ClusterPoint], parameters: dict[str, Any]
    ) -> ClusterResult:
        if not points:
            raise ValueError("Bear zone detection requires points")
        graph_value = parameters.get("spatial_graph")
        graph = (
            graph_value
            if isinstance(graph_value, SpatialGraph)
            else self.graph_builder.build(points)
        )
        bear_threshold = float(parameters.get("bear_threshold", 0.35))
        singleton_threshold = float(parameters.get("singleton_threshold", 0.70))
        if bear_threshold < 0 or singleton_threshold < bear_threshold:
            raise ValueError("Thresholds must satisfy 0 <= bear <= singleton")

        regional_rate = weighted_mean(
            (point.weighted_rub_per_km, point.trip_count) for point in points
        )
        if regional_rate is None or regional_rate <= 0:
            raise ValueError("Bear zones require positive regional weighted rub_per_km")
        point_by_id = {point.id: point for point in points}
        deltas = {
            point.id: relative_rate_delta(point.weighted_rub_per_km, regional_rate)
            for point in points
        }
        candidates = {
            point.id
            for point in points
            if deltas[point.id] is not None and deltas[point.id] >= bear_threshold
        }
        assignments = {point.id: -1 for point in points}
        cluster_types: dict[int, str] = {}
        next_cluster = 0
        candidate_components = graph.induced_components(candidates)
        singleton_ids: set[str] = set()
        for component in candidate_components:
            if len(component) < 2:
                singleton_ids.update(component)
                continue
            zone_rate = weighted_mean(
                (
                    point_by_id[point_id].weighted_rub_per_km,
                    point_by_id[point_id].trip_count,
                )
                for point_id in component
            )
            if (
                zone_rate is None
                or relative_rate_delta(zone_rate, regional_rate) is None
                or relative_rate_delta(zone_rate, regional_rate) < bear_threshold
            ):
                continue
            for point_id in component:
                assignments[point_id] = next_cluster
            cluster_types[next_cluster] = "bear_zone"
            next_cluster += 1

        for point_id in sorted(singleton_ids):
            if (
                deltas[point_id] is not None
                and deltas[point_id] >= singleton_threshold
            ):
                assignments[point_id] = next_cluster
                cluster_types[next_cluster] = "expensive_singleton"
                next_cluster += 1

        base = summarize_assignments(
            points,
            assignments,
            algorithm=self.algorithm,
            parameters={
                "bear_threshold": bear_threshold,
                "bear_threshold_pct": 100 * bear_threshold,
                "singleton_threshold": singleton_threshold,
                "singleton_threshold_pct": 100 * singleton_threshold,
                "graph_method": graph.method,
                "graph_parameters": graph.parameters,
            },
        )
        summaries = tuple(
            replace(
                cluster,
                cluster_type=cluster_types[cluster.cluster_id],
                regional_weighted_rub_per_km=regional_rate,
                relative_rate_delta=relative_rate_delta(
                    cluster.weighted_rub_per_km, regional_rate
                ),
                connected=True,
            )
            for cluster in base.clusters
        )
        violations = sum(
            cluster.cluster_type == "bear_zone"
            and not graph.is_connected(
                {
                    point_id
                    for point_id, label in assignments.items()
                    if label == cluster.cluster_id
                }
            )
            for cluster in summaries
        )
        if violations:
            raise AssertionError("Bear detector produced a disconnected zone")

        typed_outliers: list[dict[str, Any]] = [
            {"point_id": point_id, "type": "spatial_outlier"}
            for point_id in graph.isolated_point_ids
        ]
        assigned_trips = sum(
            point.trip_count for point in points if assignments[point.id] >= 0
        )
        total_trips = sum(max(point.trip_count, 0) for point in points)
        zone_sizes = [
            cluster.point_count
            for cluster in summaries
            if cluster.cluster_type == "bear_zone"
        ]
        metrics = {
            **graph.audit,
            "candidate_count": len(candidates),
            "bear_zone_count": sum(value == "bear_zone" for value in cluster_types.values()),
            "singleton_count": sum(
                value == "expensive_singleton" for value in cluster_types.values()
            ),
            "covered_point_count": sum(assignments[point.id] >= 0 for point in points),
            "covered_trip_count": assigned_trips,
            "mean_zone_size": (
                sum(zone_sizes) / len(zone_sizes) if zone_sizes else 0.0
            ),
            "max_zone_size": max(zone_sizes, default=0),
            "zone_relative_rate_deltas": [
                cluster.relative_rate_delta
                for cluster in summaries
                if cluster.cluster_type == "bear_zone"
            ],
            "trip_coverage_pct": (
                100 * assigned_trips / total_trips if total_trips else 0.0
            ),
            "connectivity_violations": violations,
        }
        return replace(
            base,
            clusters=summaries,
            mode="bear_zones",
            internal_algorithm=self.algorithm,
            regional_weighted_rub_per_km=regional_rate,
            metrics=metrics,
            outliers=tuple(typed_outliers),
        )
