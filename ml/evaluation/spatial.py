"""Spatial graph method and adaptive-pruning sensitivity diagnostics."""

from __future__ import annotations

from typing import Any

from ml.clustering.base import ClusterPoint
from ml.spatial.graph import SpatialGraphBuilder

DEFAULT_PRUNING_MULTIPLIERS = (1.5, 2.0, 2.5, 3.0, 3.5, 4.0)


def graph_pruning_sensitivity(
    points: list[ClusterPoint],
    *,
    multipliers: tuple[float, ...] = DEFAULT_PRUNING_MULTIPLIERS,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    previous_components: int | None = None
    for multiplier in multipliers:
        graph = SpatialGraphBuilder(
            method="delaunay", edge_mad_multiplier=multiplier
        ).build(points)
        component_count = int(graph.audit["graph_component_count"] or 0)
        rows.append(
            {
                "edge_mad_multiplier": multiplier,
                "graph_threshold_m": graph.audit[
                    "adaptive_edge_threshold_m"
                ],
                "component_count": component_count,
                "component_count_delta": (
                    component_count - previous_components
                    if previous_components is not None
                    else None
                ),
                "isolated_point_count": graph.audit["isolated_point_count"],
                "edge_count": graph.audit["edge_count"],
                "mean_edge_m": graph.audit["mean_edge_m"],
                "p95_edge_m": graph.audit["p95_edge_m"],
                "max_edge_m": graph.audit["max_edge_m"],
            }
        )
        previous_components = component_count
    return rows
