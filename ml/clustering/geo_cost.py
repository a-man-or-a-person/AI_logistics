"""Connectivity-constrained clustering over geography and trip cost."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

import numpy as np
from sklearn.metrics import silhouette_score

from ml.clustering.base import Clusterer, ClusterPoint, ClusterResult, summarize_assignments
from ml.clustering.economics import (
    relative_rate_delta,
    weighted_absolute_deviation,
    weighted_mean,
)
from ml.clustering.geographic import constrained_assignments
from ml.evaluation.geographic import point_compactness_metrics
from ml.spatial.graph import SpatialGraph, SpatialGraphBuilder


def _robust_column(values: np.ndarray) -> tuple[np.ndarray, float, float]:
    median = float(np.median(values))
    q1, q3 = np.percentile(values, [25, 75])
    scale = float(q3 - q1)
    if scale <= 0:
        mad = float(np.median(np.abs(values - median)))
        scale = 1.4826 * mad if mad > 0 else 1.0
    return (values - median) / scale, median, scale


def build_geo_cost_matrix(
    points: list[ClusterPoint], geography_weight: float, economics_weight: float
) -> tuple[np.ndarray, dict[str, float]]:
    if geography_weight <= 0 or economics_weight <= 0:
        raise ValueError("Geography and economics weights must be positive")
    total = geography_weight + economics_weight
    geography_weight /= total
    economics_weight /= total
    rates = [point.weighted_rub_per_km for point in points]
    if any(rate is None for rate in rates):
        missing = [
            point.id
            for point, rate in zip(points, rates, strict=True)
            if rate is None
        ]
        raise ValueError(
            f"Geo+Cost requires weighted_rub_per_km for every point: {missing}"
        )
    x, x_median, x_scale = _robust_column(
        np.array([point.x for point in points], dtype=float)
    )
    y, y_median, y_scale = _robust_column(
        np.array([point.y for point in points], dtype=float)
    )
    cost, cost_median, cost_scale = _robust_column(np.array(rates, dtype=float))
    matrix = np.column_stack(
        (
            x * math.sqrt(geography_weight / 2),
            y * math.sqrt(geography_weight / 2),
            cost * math.sqrt(economics_weight),
        )
    )
    return matrix, {
        "geography_weight": geography_weight,
        "economics_weight": economics_weight,
        "x_median": x_median,
        "x_scale": x_scale,
        "y_median": y_median,
        "y_scale": y_scale,
        "rub_per_km_median": cost_median,
        "rub_per_km_scale": cost_scale,
    }


def _economic_metrics(
    points: list[ClusterPoint], result: ClusterResult
) -> dict[str, float | None]:
    deviations: list[tuple[float | None, int]] = []
    cluster_rates: list[float] = []
    for cluster in result.clusters:
        members = [
            point
            for point in points
            if result.point_assignments[point.id] == cluster.cluster_id
        ]
        deviation = weighted_absolute_deviation(
            (
                (point.weighted_rub_per_km, point.trip_count)
                for point in members
            ),
            cluster.weighted_rub_per_km,
        )
        deviations.append((deviation, cluster.trip_count))
        if cluster.weighted_rub_per_km is not None:
            cluster_rates.append(cluster.weighted_rub_per_km)
    return {
        "within_cluster_weighted_rubkm_mad": weighted_mean(deviations),
        "between_cluster_rate_spread": (
            max(cluster_rates) - min(cluster_rates) if cluster_rates else None
        ),
    }


class GeoCostClusterer(Clusterer):
    algorithm = "connectivity_constrained_agglomerative_geo_cost"

    def __init__(self, graph_builder: SpatialGraphBuilder | None = None) -> None:
        self.graph_builder = graph_builder or SpatialGraphBuilder()

    def fit(
        self, points: list[ClusterPoint], parameters: dict[str, Any]
    ) -> ClusterResult:
        if len(points) < 2:
            raise ValueError("Geo+Cost clustering requires at least two points")
        graph_value = parameters.get("spatial_graph")
        graph = (
            graph_value
            if isinstance(graph_value, SpatialGraph)
            else self.graph_builder.build(points)
        )
        geography_weight = float(parameters.get("geography_weight", 0.70))
        economics_weight = float(parameters.get("economics_weight", 0.30))
        matrix, scaling = build_geo_cost_matrix(
            points, geography_weight, economics_weight
        )
        xy = np.array([(point.x, point.y) for point in points], dtype=float)
        component_count = sum(
            len(component) > 1 for component in graph.connected_components
        )
        available = len(points) - len(graph.isolated_point_ids)
        if component_count == 0:
            raise ValueError("Spatial graph contains no clusterable points")

        requested = parameters.get("n_clusters")
        candidates: list[dict[str, float | int | None]] = []
        if requested is None or requested == "auto":
            k_min = max(int(parameters.get("k_min", 2)), component_count)
            k_max = min(int(parameters.get("k_max", 10)), available - 1)
            if k_min > k_max:
                k_min = k_max = max(component_count, min(available, 2))
            for k in range(k_min, k_max + 1):
                assignments = constrained_assignments(points, graph, k, matrix)
                trial = summarize_assignments(
                    points,
                    assignments,
                    algorithm=self.algorithm,
                    parameters={"n_clusters": k},
                )
                included = [
                    index
                    for index, point in enumerate(points)
                    if assignments[point.id] >= 0
                ]
                labels = [assignments[points[index].id] for index in included]
                geo_score = (
                    float(silhouette_score(xy[included], labels))
                    if 1 < len(set(labels)) < len(labels)
                    else None
                )
                candidates.append(
                    {
                        "k": k,
                        "geographic_silhouette": geo_score,
                        **_economic_metrics(points, trial),
                    }
                )
            geo_values = [
                float(item["geographic_silhouette"])
                for item in candidates
                if item["geographic_silhouette"] is not None
            ]
            mad_values = [
                float(item["within_cluster_weighted_rubkm_mad"])
                for item in candidates
                if item["within_cluster_weighted_rubkm_mad"] is not None
            ]
            for item in candidates:
                geo = float(item["geographic_silhouette"] or 0)
                mad = float(item["within_cluster_weighted_rubkm_mad"] or 0)
                geo_norm = (
                    (geo - min(geo_values)) / (max(geo_values) - min(geo_values))
                    if len(set(geo_values)) > 1
                    else 1.0
                )
                econ_norm = (
                    1
                    - (mad - min(mad_values))
                    / (max(mad_values) - min(mad_values))
                    if len(set(mad_values)) > 1
                    else 1.0
                )
                item["selection_score"] = (
                    scaling["geography_weight"] * geo_norm
                    + scaling["economics_weight"] * econ_norm
                )
            selected_k = int(
                max(
                    candidates,
                    key=lambda item: (
                        float(item["selection_score"]),
                        -int(item["k"]),
                    ),
                )["k"]
            )
            k_mode = "auto"
        else:
            selected_k = int(requested)
            k_mode = "manual"

        assignments = constrained_assignments(points, graph, selected_k, matrix)
        base = summarize_assignments(
            points,
            assignments,
            algorithm=self.algorithm,
            parameters={
                "n_clusters": selected_k,
                "k_mode": k_mode,
                "geography_weight": scaling["geography_weight"],
                "economics_weight": scaling["economics_weight"],
                "robust_scaling": scaling,
                "graph_method": graph.method,
                "graph_parameters": graph.parameters,
                "auto_k_candidates": candidates,
            },
        )
        regional_rate = weighted_mean(
            (point.weighted_rub_per_km, point.trip_count) for point in points
        )
        summaries = tuple(
            replace(
                cluster,
                regional_weighted_rub_per_km=regional_rate,
                relative_rate_delta=relative_rate_delta(
                    cluster.weighted_rub_per_km, regional_rate
                ),
            )
            for cluster in base.clusters
        )
        base = replace(base, clusters=summaries)
        violations = sum(
            not graph.is_connected(
                {
                    point_id
                    for point_id, label in assignments.items()
                    if label == cluster.cluster_id
                }
            )
            for cluster in base.clusters
        )
        if violations:
            raise AssertionError("Geo+Cost produced a disconnected cluster")
        metrics = {
            **point_compactness_metrics(points, base),
            **_economic_metrics(points, base),
            **graph.audit,
            "connectivity_violations": violations,
        }
        return replace(
            base,
            mode="geo_cost",
            internal_algorithm=self.algorithm,
            regional_weighted_rub_per_km=regional_rate,
            metrics=metrics,
            outliers=tuple(
                {"point_id": point_id, "type": "spatial_outlier"}
                for point_id in graph.isolated_point_ids
            ),
        )
