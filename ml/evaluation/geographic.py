"""Algorithm-neutral geographic metrics available before polygonization."""

from __future__ import annotations

import math
from collections import Counter

from ml.clustering.base import ClusterPoint, ClusterResult


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def point_compactness_metrics(
    points: list[ClusterPoint], result: ClusterResult
) -> dict[str, float | int | None]:
    """Measure compactness against medoids without claiming polygon coverage."""
    summaries = {cluster.cluster_id: cluster for cluster in result.clusters}
    distances: list[float] = []
    weighted_distance_sum = 0.0
    total_weight = 0
    sizes: Counter[int] = Counter()
    assigned = 0
    for point in points:
        cluster_id = result.point_assignments[point.id]
        if cluster_id < 0:
            continue
        assigned += 1
        sizes[cluster_id] += 1
        medoid = summaries[cluster_id].medoid
        distance = math.hypot(point.x - medoid[0], point.y - medoid[1])
        distances.append(distance)
        weight = max(point.trip_count, 1)
        weighted_distance_sum += distance * weight
        total_weight += weight

    total = len(points)
    return {
        "point_coverage_pct": round(100 * assigned / total, 4) if total else 0,
        "noise_pct": round(100 * (total - assigned) / total, 4) if total else 0,
        "mean_distance_to_medoid_m": (
            round(sum(distances) / len(distances), 4) if distances else None
        ),
        "weighted_mean_distance_to_medoid_m": (
            round(weighted_distance_sum / total_weight, 4) if total_weight else None
        ),
        "p95_distance_to_medoid_m": (
            round(_percentile(distances, 0.95) or 0, 4) if distances else None
        ),
        "max_distance_to_medoid_m": round(max(distances), 4) if distances else None,
        "min_cluster_size": min(sizes.values()) if sizes else 0,
        "max_cluster_size": max(sizes.values()) if sizes else 0,
        "polygon_coverage_pct": None,
        "polygon_overlap_pct": None,
        "fragmentation": None,
    }
