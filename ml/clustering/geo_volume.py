"""Connectivity-constrained clustering over geography and trip volume."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

from ml.clustering.base import Clusterer, ClusterPoint, ClusterResult, summarize_assignments
from ml.clustering.geo_cost import GeoCostClusterer
from ml.spatial.graph import SpatialGraph, SpatialGraphBuilder


def _relative_delta(value: float, baseline: float) -> float | None:
    return value / baseline - 1 if baseline > 0 else None


def _volume_metrics(
    points: list[ClusterPoint], result: ClusterResult
) -> dict[str, Any]:
    regional_mean = sum(point.trip_count for point in points) / len(points)
    cluster_means: list[float] = []
    absolute_deviations: list[float] = []
    within_squared: list[float] = []
    for cluster in result.clusters:
        members = [
            point
            for point in points
            if result.point_assignments[point.id] == cluster.cluster_id
        ]
        cluster_mean = sum(point.trip_count for point in members) / len(members)
        cluster_means.append(cluster_mean)
        absolute_deviations.extend(
            abs(point.trip_count - cluster_mean) for point in members
        )
        within_squared.extend(
            (point.trip_count - cluster_mean) ** 2 for point in members
        )
    within_variance = (
        sum(within_squared) / len(within_squared) if within_squared else None
    )
    between_variance = (
        sum((value - regional_mean) ** 2 for value in cluster_means)
        / len(cluster_means)
        if cluster_means
        else None
    )
    return {
        "regional_mean_trip_count": regional_mean,
        "within_cluster_trip_count_mad": (
            sum(absolute_deviations) / len(absolute_deviations)
            if absolute_deviations
            else None
        ),
        "within_cluster_trip_count_variance": within_variance,
        "between_cluster_mean_trip_variance": between_variance,
        "between_within_volume_variance_ratio": (
            between_variance / within_variance
            if between_variance is not None
            and within_variance is not None
            and within_variance > 0
            else None
        ),
        "between_cluster_mean_trip_spread": (
            max(cluster_means) - min(cluster_means) if cluster_means else None
        ),
        "cluster_mean_trip_count": cluster_means,
    }


class GeoVolumeClusterer(Clusterer):
    """Use log-volume as a merge priority without creating spatial edges."""

    algorithm = "connectivity_constrained_agglomerative_geo_volume"

    def __init__(self, graph_builder: SpatialGraphBuilder | None = None) -> None:
        self.graph_builder = graph_builder or SpatialGraphBuilder()
        self.delegate = GeoCostClusterer(self.graph_builder)

    def fit(
        self, points: list[ClusterPoint], parameters: dict[str, Any]
    ) -> ClusterResult:
        if len(points) < 2:
            raise ValueError("Geo+Volume clustering requires at least two points")
        graph_value = parameters.get("spatial_graph")
        graph = (
            graph_value
            if isinstance(graph_value, SpatialGraph)
            else self.graph_builder.build(points)
        )
        geography_weight = float(parameters.get("geography_weight", 0.70))
        volume_weight = float(parameters.get("volume_weight", 0.30))
        proxy_points = [
            replace(
                point,
                trip_count=1,
                weighted_price=None,
                weighted_rub_per_km=math.log1p(max(point.trip_count, 0)),
            )
            for point in points
        ]
        proxy_result = self.delegate.fit(
            proxy_points,
            {
                **parameters,
                "spatial_graph": graph,
                "geography_weight": geography_weight,
                "economics_weight": volume_weight,
            },
        )
        proxy_parameters = proxy_result.parameters
        scaling = dict(proxy_parameters.get("robust_scaling", {}))
        if "rub_per_km_median" in scaling:
            scaling["log_trip_count_median"] = scaling.pop("rub_per_km_median")
        if "rub_per_km_scale" in scaling:
            scaling["log_trip_count_scale"] = scaling.pop("rub_per_km_scale")
        scaling.pop("economics_weight", None)
        scaling["volume_weight"] = volume_weight
        base = summarize_assignments(
            points,
            proxy_result.point_assignments,
            algorithm=self.algorithm,
            parameters={
                "n_clusters": proxy_parameters["n_clusters"],
                "k_mode": proxy_parameters["k_mode"],
                "geography_weight": geography_weight,
                "volume_weight": volume_weight,
                "volume_transform": "log1p",
                "robust_scaling": scaling,
                "graph_method": graph.method,
                "graph_parameters": graph.parameters,
            },
        )
        regional_mean = sum(point.trip_count for point in points) / len(points)
        summaries = tuple(
            replace(
                cluster,
                mean_trip_count=cluster.trip_count / cluster.point_count,
                regional_mean_trip_count=regional_mean,
                relative_volume_delta=_relative_delta(
                    cluster.trip_count / cluster.point_count, regional_mean
                ),
                connected=True,
            )
            for cluster in base.clusters
        )
        violations = sum(
            not graph.is_connected(
                {
                    point_id
                    for point_id, label in base.point_assignments.items()
                    if label == cluster.cluster_id
                }
            )
            for cluster in summaries
        )
        if violations:
            raise AssertionError("Geo+Volume produced a disconnected cluster")
        metrics = {
            key: value
            for key, value in proxy_result.metrics.items()
            if "rubkm" not in key and "rate" not in key
        }
        result = replace(base, clusters=summaries)
        metrics.update(_volume_metrics(points, result))
        metrics["connectivity_violations"] = violations
        return replace(
            result,
            mode="geo_volume",
            internal_algorithm=self.algorithm,
            metrics=metrics,
            outliers=tuple(
                {"point_id": point_id, "type": "spatial_outlier"}
                for point_id in graph.isolated_point_ids
            ),
        )
