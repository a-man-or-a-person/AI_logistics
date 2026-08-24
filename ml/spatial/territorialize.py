"""Grid-based polygonization shared by every clustering algorithm."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from shapely.geometry import box, mapping
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform, unary_union

from ml.clustering.base import ClusterPoint, ClusterResult
from ml.spatial.projection import LocalProjection


@dataclass(frozen=True, slots=True)
class TerritorializationResult:
    zones_geojson: dict[str, Any]
    metrics: dict[str, float | int]


def _component_count(geometry: BaseGeometry) -> int:
    if geometry.geom_type == "Polygon":
        return 1
    if geometry.geom_type == "MultiPolygon":
        return len(geometry.geoms)
    return 0


def territorialize(
    points: list[ClusterPoint],
    cluster_result: ClusterResult,
    region_boundary_wgs84: BaseGeometry,
    projection: LocalProjection,
    *,
    cell_size_m: float = 2_000,
) -> TerritorializationResult:
    """Assign every clipped grid cell to its nearest stable cluster medoid."""
    if cell_size_m <= 0:
        raise ValueError("cell_size_m must be positive")
    if region_boundary_wgs84.is_empty:
        raise ValueError("Region boundary must not be empty")
    if not cluster_result.clusters:
        raise ValueError("At least one non-noise cluster is required")
    point_ids = {point.id for point in points}
    if set(cluster_result.point_assignments) != point_ids:
        raise ValueError("Cluster result assignments do not match points")

    forward = projection.forward_transformer()
    inverse = projection.inverse_transformer()
    region_metric = transform(forward.transform, region_boundary_wgs84)
    if not region_metric.is_valid:
        region_metric = region_metric.buffer(0)
    min_x, min_y, max_x, max_y = region_metric.bounds
    representatives = {
        summary.cluster_id: summary.medoid for summary in cluster_result.clusters
    }
    fragments: dict[int, list[BaseGeometry]] = {
        cluster_id: [] for cluster_id in representatives
    }

    columns = max(1, math.ceil((max_x - min_x) / cell_size_m))
    rows = max(1, math.ceil((max_y - min_y) / cell_size_m))
    for column in range(columns):
        x0 = min_x + column * cell_size_m
        x1 = min(x0 + cell_size_m, max_x)
        for row in range(rows):
            y0 = min_y + row * cell_size_m
            y1 = min(y0 + cell_size_m, max_y)
            clipped = box(x0, y0, x1, y1).intersection(region_metric)
            if clipped.is_empty or clipped.area == 0:
                continue
            center = clipped.representative_point()
            cluster_id = min(
                representatives,
                key=lambda candidate: math.hypot(
                    center.x - representatives[candidate][0],
                    center.y - representatives[candidate][1],
                ),
            )
            fragments[cluster_id].append(clipped)

    zones_metric = {
        cluster_id: unary_union(parts) for cluster_id, parts in fragments.items() if parts
    }
    union = unary_union(list(zones_metric.values()))
    region_area = region_metric.area
    coverage_pct = 100 * union.area / region_area if region_area else 0
    overlap_area = 0.0
    cluster_ids = sorted(zones_metric)
    for index, first_id in enumerate(cluster_ids):
        for second_id in cluster_ids[index + 1 :]:
            overlap_area += zones_metric[first_id].intersection(zones_metric[second_id]).area
    overlap_pct = 100 * overlap_area / region_area if region_area else 0
    components = {
        cluster_id: _component_count(geometry)
        for cluster_id, geometry in zones_metric.items()
    }
    features = []
    for cluster_id in cluster_ids:
        geometry_wgs84 = transform(inverse.transform, zones_metric[cluster_id])
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "cluster_id": cluster_id,
                    "assignment_source": "inferred_nearest_medoid_grid",
                    "connected_components": components[cluster_id],
                },
                "geometry": mapping(geometry_wgs84),
            }
        )
    return TerritorializationResult(
        zones_geojson={"type": "FeatureCollection", "features": features},
        metrics={
            "coverage_pct": round(coverage_pct, 6),
            "overlap_pct": round(overlap_pct, 6),
            "zone_count": len(features),
            "max_connected_components": max(components.values(), default=0),
            "fragmented_zone_count": sum(value > 1 for value in components.values()),
            "cell_size_m": cell_size_m,
        },
    )
