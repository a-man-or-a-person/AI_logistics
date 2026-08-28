"""Algorithm-neutral geographic metrics available before polygonization."""

from __future__ import annotations

import math
import statistics
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


def _weighted_percentile(
    values_and_weights: list[tuple[float, float]], fraction: float
) -> float | None:
    positive = sorted((value, weight) for value, weight in values_and_weights if weight > 0)
    total = sum(weight for _, weight in positive)
    if not positive or total <= 0:
        return None
    threshold = total * fraction
    cumulative = 0.0
    for value, weight in positive:
        cumulative += weight
        if cumulative >= threshold:
            return value
    return positive[-1][0]


def point_compactness_metrics(
    points: list[ClusterPoint], result: ClusterResult
) -> dict[str, float | int | None]:
    """Measure compactness against medoids without claiming polygon coverage."""
    summaries = {cluster.cluster_id: cluster for cluster in result.clusters}
    distances: list[float] = []
    weighted_distances: list[tuple[float, float]] = []
    weighted_distance_sum = 0.0
    total_weight = 0.0
    assigned_weight = 0.0
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
        weight = max(point.shipment_count, 0)
        weighted_distances.append((distance, weight))
        weighted_distance_sum += distance * weight
        total_weight += weight
        assigned_weight += weight

    total = len(points)
    all_shipments = sum(max(point.shipment_count, 0) for point in points)
    shares = [cluster.shipment_share for cluster in result.clusters]
    share_mean = statistics.fmean(shares) if shares else 0
    share_cv = (
        statistics.pstdev(shares) / share_mean if len(shares) > 1 and share_mean else 0
    )
    return {
        "point_coverage_pct": round(100 * assigned / total, 4) if total else 0,
        "noise_pct": round(100 * (total - assigned) / total, 4) if total else 0,
        "mean_distance_to_medoid_m": (
            round(sum(distances) / len(distances), 4) if distances else None
        ),
        "weighted_mean_distance_to_medoid_m": (
            round(weighted_distance_sum / total_weight, 4) if total_weight else None
        ),
        "weighted_p95_distance_to_medoid_m": (
            round(_weighted_percentile(weighted_distances, 0.95) or 0, 4)
            if total_weight
            else None
        ),
        "p95_distance_to_medoid_m": (
            round(_percentile(distances, 0.95) or 0, 4) if distances else None
        ),
        "max_distance_to_medoid_m": round(max(distances), 4) if distances else None,
        "min_cluster_size": min(sizes.values()) if sizes else 0,
        "max_cluster_size": max(sizes.values()) if sizes else 0,
        "shipment_coverage_pct": (
            round(100 * assigned_weight / all_shipments, 4) if all_shipments else 0
        ),
        "min_shipment_share": round(min(shares), 6) if shares else 0,
        "max_shipment_share": round(max(shares), 6) if shares else 0,
        "shipment_share_cv": round(share_cv, 6),
    }
