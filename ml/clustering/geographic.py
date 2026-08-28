"""Connectivity-constrained geography-only product clustering mode."""

from __future__ import annotations

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


def _candidate_rank(candidates: list[dict[str, float | int | None]]) -> int:
    keys = (("silhouette", True), ("calinski_harabasz", True), ("davies_bouldin", False), ("p95_radius", False))
    scores = [0] * len(candidates)
    for key, descending in keys:
        ordered = sorted(
            range(len(candidates)),
            key=lambda index: (
                candidates[index][key] is None,
                -(float(candidates[index][key])) if descending and candidates[index][key] is not None else (
                    float(candidates[index][key]) if candidates[index][key] is not None else 0
                ),
                int(candidates[index]["k"]),
            ),
        )
        for rank, index in enumerate(ordered):
            scores[index] += rank
    return min(range(len(candidates)), key=lambda index: (scores[index], int(candidates[index]["k"])))


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
        candidates: list[dict[str, float | int | None]] = []
        if requested is None or requested == "auto":
            k_min = max(int(parameters.get("k_min", 2)), component_count)
            k_max = min(int(parameters.get("k_max", 10)), available - 1)
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
                        "p95_radius": compactness["p95_distance_to_medoid_m"],
                    }
                )
            selected_k = int(candidates[_candidate_rank(candidates)]["k"])
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
