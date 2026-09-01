"""Detect connected territories with anomalously high trip volume."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ml.clustering.base import Clusterer, ClusterPoint, ClusterResult, summarize_assignments
from ml.spatial.graph import SpatialGraph, SpatialGraphBuilder


def _delta(value: float, baseline: float) -> float | None:
    return value / baseline - 1 if baseline > 0 else None


class BearVolumeZoneDetector(Clusterer):
    algorithm = "connected_high_volume_components"

    def __init__(self, graph_builder: SpatialGraphBuilder | None = None) -> None:
        self.graph_builder = graph_builder or SpatialGraphBuilder()

    def fit(
        self, points: list[ClusterPoint], parameters: dict[str, Any]
    ) -> ClusterResult:
        if not points:
            raise ValueError("Bear volume detection requires points")
        graph_value = parameters.get("spatial_graph")
        graph = (
            graph_value
            if isinstance(graph_value, SpatialGraph)
            else self.graph_builder.build(points)
        )
        volume_threshold = float(parameters.get("volume_threshold", 0.35))
        singleton_threshold = float(parameters.get("singleton_threshold", 0.70))
        if volume_threshold < 0 or singleton_threshold < volume_threshold:
            raise ValueError("Thresholds must satisfy 0 <= volume <= singleton")
        regional_mean = sum(point.trip_count for point in points) / len(points)
        if regional_mean <= 0:
            raise ValueError("Bear volume zones require positive trip volume")
        point_by_id = {point.id: point for point in points}
        deltas = {
            point.id: _delta(point.trip_count, regional_mean) for point in points
        }
        candidates = {
            point.id
            for point in points
            if deltas[point.id] is not None
            and deltas[point.id] >= volume_threshold
        }
        assignments = {point.id: -1 for point in points}
        cluster_types: dict[int, str] = {}
        next_cluster = 0
        singleton_ids: set[str] = set()
        for component in graph.induced_components(candidates):
            if len(component) < 2:
                singleton_ids.update(component)
                continue
            zone_mean = sum(point_by_id[item].trip_count for item in component) / len(
                component
            )
            if (_delta(zone_mean, regional_mean) or 0) < volume_threshold:
                continue
            for point_id in component:
                assignments[point_id] = next_cluster
            cluster_types[next_cluster] = "bear_volume_zone"
            next_cluster += 1
        for point_id in sorted(singleton_ids):
            if (deltas[point_id] or 0) >= singleton_threshold:
                assignments[point_id] = next_cluster
                cluster_types[next_cluster] = "high_volume_singleton"
                next_cluster += 1
        base = summarize_assignments(
            points,
            assignments,
            algorithm=self.algorithm,
            parameters={
                "volume_threshold": volume_threshold,
                "volume_threshold_pct": 100 * volume_threshold,
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
                mean_trip_count=cluster.trip_count / cluster.point_count,
                regional_mean_trip_count=regional_mean,
                relative_volume_delta=_delta(
                    cluster.trip_count / cluster.point_count, regional_mean
                ),
                connected=True,
            )
            for cluster in base.clusters
        )
        violations = sum(
            cluster.cluster_type == "bear_volume_zone"
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
            raise AssertionError("Bear volume detector produced a disconnected zone")
        assigned_trips = sum(
            point.trip_count for point in points if assignments[point.id] >= 0
        )
        total_trips = sum(point.trip_count for point in points)
        metrics = {
            **graph.audit,
            "regional_mean_trip_count": regional_mean,
            "candidate_count": len(candidates),
            "bear_zone_count": sum(
                value == "bear_volume_zone" for value in cluster_types.values()
            ),
            "singleton_count": sum(
                value == "high_volume_singleton" for value in cluster_types.values()
            ),
            "covered_point_count": sum(
                assignments[point.id] >= 0 for point in points
            ),
            "covered_trip_count": assigned_trips,
            "zone_relative_volume_deltas": [
                cluster.relative_volume_delta
                for cluster in summaries
                if cluster.cluster_type == "bear_volume_zone"
            ],
            "trip_coverage_pct": (
                100 * assigned_trips / total_trips if total_trips else 0.0
            ),
            "connectivity_violations": violations,
        }
        return replace(
            base,
            clusters=summaries,
            mode="bear_volume_zones",
            internal_algorithm=self.algorithm,
            metrics=metrics,
            outliers=tuple(
                {"point_id": point_id, "type": "spatial_outlier"}
                for point_id in graph.isolated_point_ids
            ),
        )
