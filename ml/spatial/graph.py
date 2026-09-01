"""Reusable deterministic spatial adjacency graphs for clustering modes."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.spatial import Delaunay, QhullError

from ml.clustering.base import ClusterPoint


@dataclass(frozen=True, slots=True)
class SpatialEdge:
    first_id: str
    second_id: str
    distance_m: float


@dataclass(frozen=True, slots=True)
class SpatialGraph:
    node_ids: tuple[str, ...]
    edges: tuple[SpatialEdge, ...]
    adjacency: dict[str, frozenset[str]]
    connected_components: tuple[tuple[str, ...], ...]
    isolated_point_ids: tuple[str, ...]
    method: str
    parameters: dict[str, Any]
    audit: dict[str, float | int | None]

    def induced_components(self, point_ids: set[str]) -> tuple[tuple[str, ...], ...]:
        remaining = set(point_ids) & set(self.node_ids)
        components: list[tuple[str, ...]] = []
        while remaining:
            start = min(remaining)
            stack = [start]
            seen = {start}
            while stack:
                current = stack.pop()
                for neighbor in self.adjacency[current]:
                    if neighbor in remaining and neighbor not in seen:
                        seen.add(neighbor)
                        stack.append(neighbor)
            remaining -= seen
            components.append(tuple(sorted(seen)))
        return tuple(sorted(components, key=lambda item: item[0]))

    def is_connected(self, point_ids: set[str]) -> bool:
        return len(point_ids) <= 1 or len(self.induced_components(point_ids)) == 1

    def induced_subgraph(self, point_ids: set[str]) -> SpatialGraph:
        """Return a node-induced graph without ever creating a new spatial edge."""
        selected = tuple(point_id for point_id in self.node_ids if point_id in point_ids)
        selected_set = set(selected)
        edges = tuple(
            edge
            for edge in self.edges
            if edge.first_id in selected_set and edge.second_id in selected_set
        )
        mutable_adjacency: dict[str, set[str]] = {point_id: set() for point_id in selected}
        for edge in edges:
            mutable_adjacency[edge.first_id].add(edge.second_id)
            mutable_adjacency[edge.second_id].add(edge.first_id)
        adjacency = {
            point_id: frozenset(sorted(neighbors))
            for point_id, neighbors in mutable_adjacency.items()
        }
        components = _components(selected, adjacency)
        isolated = tuple(point_id for point_id in selected if not adjacency[point_id])
        degrees = [float(len(adjacency[point_id])) for point_id in selected]
        edge_lengths = [edge.distance_m for edge in edges]
        audit: dict[str, float | int | None] = {
            "node_count": len(selected),
            "edge_count": len(edges),
            "candidate_edge_count": len(edges),
            "pruned_edge_count": 0,
            "graph_component_count": len(components),
            "isolated_point_count": len(isolated),
            "mean_degree": statistics.fmean(degrees) if degrees else 0.0,
            "p95_degree": _percentile(degrees, 0.95),
            "mean_edge_m": statistics.fmean(edge_lengths) if edge_lengths else None,
            "p95_edge_m": _percentile(edge_lengths, 0.95),
            "max_edge_m": max(edge_lengths) if edge_lengths else None,
            "adaptive_edge_threshold_m": self.audit.get("adaptive_edge_threshold_m"),
            "induced_from_node_count": len(self.node_ids),
            "induced_from_edge_count": len(self.edges),
        }
        return SpatialGraph(
            node_ids=selected,
            edges=edges,
            adjacency=adjacency,
            connected_components=components,
            isolated_point_ids=isolated,
            method=self.method,
            parameters={**self.parameters, "induced_subgraph": True},
            audit=audit,
        )


def _percentile(values: list[float], fraction: float) -> float | None:
    return float(np.percentile(values, fraction * 100)) if values else None


def _components(
    node_ids: tuple[str, ...], adjacency: dict[str, frozenset[str]]
) -> tuple[tuple[str, ...], ...]:
    remaining = set(node_ids)
    result: list[tuple[str, ...]] = []
    while remaining:
        start = min(remaining)
        stack = [start]
        seen = {start}
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in remaining and neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        remaining -= seen
        result.append(tuple(sorted(seen)))
    return tuple(sorted(result, key=lambda item: item[0]))


class SpatialGraphBuilder:
    """Build Delaunay+pruning (default) or mutual-kNN benchmark graphs."""

    def __init__(
        self,
        *,
        method: str = "delaunay",
        knn_k: int = 5,
        edge_mad_multiplier: float = 3.0,
        max_edge_m: float | None = None,
    ) -> None:
        if method not in {"delaunay", "mutual_knn"}:
            raise ValueError("method must be delaunay or mutual_knn")
        if knn_k < 1:
            raise ValueError("knn_k must be positive")
        if edge_mad_multiplier <= 0:
            raise ValueError("edge_mad_multiplier must be positive")
        self.method = method
        self.knn_k = knn_k
        self.edge_mad_multiplier = edge_mad_multiplier
        self.max_edge_m = max_edge_m

    @staticmethod
    def _matrix(points: list[ClusterPoint]) -> tuple[list[ClusterPoint], np.ndarray]:
        ordered = sorted(points, key=lambda point: point.id)
        if len({point.id for point in ordered}) != len(ordered):
            raise ValueError("Spatial graph point ids must be unique")
        matrix = np.array([(point.x, point.y) for point in ordered], dtype=float)
        if not np.isfinite(matrix).all():
            raise ValueError("Spatial graph coordinates must be finite")
        return ordered, matrix

    @staticmethod
    def _distances(matrix: np.ndarray) -> np.ndarray:
        if not len(matrix):
            return np.empty((0, 0), dtype=float)
        differences = matrix[:, None, :] - matrix[None, :, :]
        return np.sqrt(np.sum(differences * differences, axis=2))

    def _adaptive_threshold(self, distances: np.ndarray) -> float:
        if len(distances) <= 1:
            return 0.0
        masked = distances.copy()
        np.fill_diagonal(masked, np.inf)
        nearest = np.min(masked, axis=1).tolist()
        median = statistics.median(nearest)
        deviations = [abs(value - median) for value in nearest]
        mad = statistics.median(deviations)
        threshold = median + self.edge_mad_multiplier * 1.4826 * mad
        if mad == 0:
            threshold = median * self.edge_mad_multiplier
        if self.max_edge_m is not None:
            threshold = min(threshold, self.max_edge_m)
        return max(float(threshold), 0.0)

    @staticmethod
    def _chain_candidates(matrix: np.ndarray) -> set[tuple[int, int]]:
        if len(matrix) < 2:
            return set()
        order = sorted(range(len(matrix)), key=lambda index: (matrix[index, 0], matrix[index, 1], index))
        return {
            (min(left, right), max(left, right))
            for left, right in zip(order, order[1:], strict=False)
        }

    def _delaunay_candidates(self, matrix: np.ndarray) -> set[tuple[int, int]]:
        if len(matrix) < 3:
            return self._chain_candidates(matrix)
        try:
            triangulation = Delaunay(matrix)
        except QhullError:
            return self._chain_candidates(matrix)
        edges: set[tuple[int, int]] = set()
        for simplex in triangulation.simplices:
            for offset, left in enumerate(simplex):
                for right in simplex[offset + 1 :]:
                    edges.add((min(int(left), int(right)), max(int(left), int(right))))
        return edges

    def _mutual_knn_candidates(self, distances: np.ndarray) -> set[tuple[int, int]]:
        if len(distances) < 2:
            return set()
        k = min(self.knn_k, len(distances) - 1)
        neighbors: list[set[int]] = []
        for index, row in enumerate(distances):
            ranked = sorted(
                (candidate for candidate in range(len(row)) if candidate != index),
                key=lambda candidate: (row[candidate], candidate),
            )
            neighbors.append(set(ranked[:k]))
        return {
            (left, right)
            for left in range(len(distances))
            for right in neighbors[left]
            if left < right and left in neighbors[right]
        }

    def build(self, points: list[ClusterPoint]) -> SpatialGraph:
        ordered, matrix = self._matrix(points)
        node_ids = tuple(point.id for point in ordered)
        distances = self._distances(matrix)
        candidates = (
            self._delaunay_candidates(matrix)
            if self.method == "delaunay"
            else self._mutual_knn_candidates(distances)
        )
        threshold = self._adaptive_threshold(distances)
        kept = sorted(
            (left, right)
            for left, right in candidates
            if distances[left, right] <= threshold and distances[left, right] > 0
        )
        edges = tuple(
            SpatialEdge(node_ids[left], node_ids[right], float(distances[left, right]))
            for left, right in kept
        )
        mutable_adjacency: dict[str, set[str]] = {point_id: set() for point_id in node_ids}
        for edge in edges:
            mutable_adjacency[edge.first_id].add(edge.second_id)
            mutable_adjacency[edge.second_id].add(edge.first_id)
        adjacency = {
            point_id: frozenset(sorted(neighbors))
            for point_id, neighbors in mutable_adjacency.items()
        }
        components = _components(node_ids, adjacency)
        isolated = tuple(point_id for point_id in node_ids if not adjacency[point_id])
        degrees = [float(len(adjacency[point_id])) for point_id in node_ids]
        edge_lengths = [edge.distance_m for edge in edges]
        audit: dict[str, float | int | None] = {
            "node_count": len(node_ids),
            "edge_count": len(edges),
            "candidate_edge_count": len(candidates),
            "pruned_edge_count": len(candidates) - len(edges),
            "graph_component_count": len(components),
            "isolated_point_count": len(isolated),
            "mean_degree": statistics.fmean(degrees) if degrees else 0.0,
            "p95_degree": _percentile(degrees, 0.95),
            "mean_edge_m": statistics.fmean(edge_lengths) if edge_lengths else None,
            "p95_edge_m": _percentile(edge_lengths, 0.95),
            "max_edge_m": max(edge_lengths) if edge_lengths else None,
            "adaptive_edge_threshold_m": threshold,
        }
        return SpatialGraph(
            node_ids=node_ids,
            edges=edges,
            adjacency=adjacency,
            connected_components=components,
            isolated_point_ids=isolated,
            method=self.method,
            parameters={
                "knn_k": self.knn_k,
                "edge_mad_multiplier": self.edge_mad_multiplier,
                "max_edge_m": self.max_edge_m,
            },
            audit=audit,
        )
