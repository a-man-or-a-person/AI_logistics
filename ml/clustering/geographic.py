"""Connectivity-constrained geography-only product clustering mode."""

from __future__ import annotations

import statistics
from dataclasses import replace
from typing import Any

import numpy as np
from scipy.sparse import lil_matrix
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)

from ml.clustering.base import Clusterer, ClusterPoint, ClusterResult, summarize_assignments
from ml.evaluation.geographic import point_compactness_metrics
from ml.spatial.graph import SpatialGraph, SpatialGraphBuilder


def _allocate_clusters(components: list[tuple[str, ...]], total: int) -> list[int]:
    if total < len(components) or total > sum(len(component) for component in components):
        raise ValueError(
            "n_clusters must cover every non-isolated graph component and not exceed its points"
        )
    allocation = [1] * len(components)
    remaining = total - len(components)
    while remaining:
        candidates = [
            index for index, component in enumerate(components) if allocation[index] < len(component)
        ]
        selected = max(
            candidates,
            key=lambda index: (
                len(components[index]) / (allocation[index] + 1),
                len(components[index]),
                -index,
            ),
        )
        allocation[selected] += 1
        remaining -= 1
    return allocation


def constrained_assignments(
    points: list[ClusterPoint],
    graph: SpatialGraph,
    n_clusters: int,
    matrix: np.ndarray,
) -> dict[str, int]:
    """Cluster each graph component separately so no merge can cross adjacency."""
    point_index = {point.id: index for index, point in enumerate(points)}
    components = [
        component
        for component in graph.connected_components
        if len(component) > 1
    ]
    if not components:
        raise ValueError("No non-isolated spatial component is available for clustering")
    allocation = _allocate_clusters(components, n_clusters)
    assignments = {point_id: -1 for point_id in graph.isolated_point_ids}
    next_cluster_id = 0
    for component, component_k in zip(components, allocation, strict=True):
        indices = [point_index[point_id] for point_id in component]
        if component_k == 1:
            for point_id in component:
                assignments[point_id] = next_cluster_id
            next_cluster_id += 1
            continue
        connectivity = lil_matrix((len(component), len(component)), dtype=int)
        local_index = {point_id: index for index, point_id in enumerate(component)}
        for point_id in component:
            for neighbor in graph.adjacency[point_id]:
                if neighbor in local_index:
                    connectivity[local_index[point_id], local_index[neighbor]] = 1
        model = AgglomerativeClustering(
            n_clusters=component_k,
            linkage="ward",
            connectivity=connectivity.tocsr(),
        )
        labels = model.fit_predict(matrix[indices])
        label_ids = {
            label: next_cluster_id + offset
            for offset, label in enumerate(sorted(set(int(value) for value in labels)))
        }
        for offset, point_id in enumerate(component):
            assignments[point_id] = label_ids[int(labels[offset])]
        next_cluster_id += component_k
    return assignments


def _quality(
    points: list[ClusterPoint], assignments: dict[str, int], matrix: np.ndarray
) -> dict[str, float | None]:
    included = [index for index, point in enumerate(points) if assignments[point.id] >= 0]
    labels = [assignments[points[index].id] for index in included]
    selected = matrix[included]
    valid = 1 < len(set(labels)) < len(labels)
    return {
        "silhouette": float(silhouette_score(selected, labels)) if valid else None,
        "calinski_harabasz": float(calinski_harabasz_score(selected, labels)) if valid else None,
        "davies_bouldin": float(davies_bouldin_score(selected, labels)) if valid else None,
    }


def cluster_size_diagnostics(result: ClusterResult) -> dict[str, float | int]:
    sizes = [cluster.point_count for cluster in result.clusters]
    mean_size = statistics.fmean(sizes) if sizes else 0.0
    return {
        "tiny_cluster_count": sum(size <= 2 for size in sizes),
        "tiny_cluster_share": (
            sum(size <= 2 for size in sizes) / len(sizes) if sizes else 0.0
        ),
        "cluster_size_cv": (
            statistics.pstdev(sizes) / mean_size
            if len(sizes) > 1 and mean_size
            else 0.0
        ),
    }


def _dominates(
    left: dict[str, Any], right: dict[str, Any]
) -> bool:
    maximize = ("silhouette",)
    minimize = (
        "p95_radius_m",
        "tiny_cluster_share",
        "cluster_size_cv",
        "excessive_k_penalty",
    )
    def metric(candidate: dict[str, Any], key: str, missing: float) -> float:
        value = candidate.get(key)
        return float(value) if value is not None else missing

    better_or_equal = all(
        metric(left, key, float("-inf"))
        >= metric(right, key, float("-inf"))
        for key in maximize
    ) and all(
        metric(left, key, float("inf"))
        <= metric(right, key, float("inf"))
        for key in minimize
    )
    strictly_better = any(
        metric(left, key, float("-inf"))
        > metric(right, key, float("-inf"))
        for key in maximize
    ) or any(
        metric(left, key, float("inf"))
        < metric(right, key, float("inf"))
        for key in minimize
    )
    return better_or_equal and strictly_better


def select_auto_k(
    candidates: list[dict[str, Any]],
    *,
    quality_key: str = "silhouette",
    tolerance: float = 0.02,
) -> int:
    """Pareto-filter, reject avoidable tiny fragmentation, then prefer lower K."""
    pareto = [
        candidate
        for candidate in candidates
        if not any(
            other is not candidate and _dominates(other, candidate)
            for other in candidates
        )
    ]
    for candidate in candidates:
        candidate["pareto_shortlist"] = candidate in pareto
    minimum_tiny_count = min(
        int(candidate["tiny_cluster_count"]) for candidate in pareto
    )
    sane = [
        candidate
        for candidate in pareto
        if int(candidate["tiny_cluster_count"]) == minimum_tiny_count
    ]
    available_quality = [
        float(candidate[quality_key])
        for candidate in sane
        if candidate.get(quality_key) is not None
    ]
    if available_quality:
        best_quality = max(available_quality)
        near_best = [
            candidate
            for candidate in sane
            if candidate.get(quality_key) is not None
            and float(candidate[quality_key]) >= best_quality - tolerance
        ]
    else:
        near_best = sane
    selected = min(near_best, key=lambda candidate: int(candidate["k"]))
    for candidate in candidates:
        candidate["selection_eligible"] = candidate in near_best
        candidate["selected"] = candidate is selected
    return int(selected["k"])


class GeographicClusterer(Clusterer):
    algorithm = "connectivity_constrained_agglomerative"

    def __init__(self, graph_builder: SpatialGraphBuilder | None = None) -> None:
        self.graph_builder = graph_builder or SpatialGraphBuilder()

    def fit(self, points: list[ClusterPoint], parameters: dict[str, Any]) -> ClusterResult:
        if len(points) < 2:
            raise ValueError("Geographic clustering requires at least two points")
        graph_value = parameters.get("spatial_graph")
        graph = graph_value if isinstance(graph_value, SpatialGraph) else self.graph_builder.build(points)
        matrix = np.array([(point.x, point.y) for point in points], dtype=float)
        component_count = sum(len(component) > 1 for component in graph.connected_components)
        available = len(points) - len(graph.isolated_point_ids)
        if available < 2 or component_count == 0:
            raise ValueError("Spatial graph contains no clusterable points")

        requested = parameters.get("n_clusters")
        candidates: list[dict[str, Any]] = []
        if requested is None or requested == "auto":
            k_min = max(int(parameters.get("k_min", 2)), component_count)
            k_max = min(int(parameters.get("k_max", 20)), available - 1)
            if k_min > k_max:
                k_min = k_max = max(component_count, min(available, 2))
            for k in range(k_min, k_max + 1):
                assignments = constrained_assignments(points, graph, k, matrix)
                trial = summarize_assignments(
                    points, assignments, algorithm=self.algorithm, parameters={"n_clusters": k}
                )
                quality = _quality(points, assignments, matrix)
                compactness = point_compactness_metrics(points, trial)
                candidates.append(
                    {
                        "k": k,
                        **quality,
                        "mean_radius_m": compactness["mean_distance_to_medoid_m"],
                        "p95_radius_m": compactness["p95_distance_to_medoid_m"],
                        "max_radius_m": compactness["max_distance_to_medoid_m"],
                        **cluster_size_diagnostics(trial),
                        "excessive_k_penalty": k / available,
                    }
                )
            selected_k = select_auto_k(candidates)
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
                "graph_method": graph.method,
                "graph_parameters": graph.parameters,
                "auto_k_candidates": candidates,
            },
        )
        violations = sum(
            not graph.is_connected(
                {point_id for point_id, label in assignments.items() if label == cluster.cluster_id}
            )
            for cluster in base.clusters
        )
        summaries = tuple(replace(cluster, connected=True) for cluster in base.clusters)
        base = replace(base, clusters=summaries)
        metrics = {
            **point_compactness_metrics(points, base),
            **_quality(points, assignments, matrix),
            **graph.audit,
            "connectivity_violations": violations,
        }
        if violations:
            raise AssertionError("Connectivity-constrained clustering produced a disconnected cluster")
        return replace(
            base,
            mode="geography",
            internal_algorithm=self.algorithm,
            metrics=metrics,
            outliers=tuple(
                {"point_id": point_id, "type": "spatial_outlier"}
                for point_id in graph.isolated_point_ids
            ),
        )
