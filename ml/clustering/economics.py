"""Shared trip-weighted economics for points, clusters, zones and regions."""

from __future__ import annotations

from collections.abc import Iterable


def weighted_mean(values_and_weights: Iterable[tuple[float | None, int | float]]) -> float | None:
    """Return a mean over valid values with strictly positive weights."""
    numerator = 0.0
    denominator = 0.0
    for value, weight in values_and_weights:
        if value is None or weight <= 0:
            continue
        numerator += value * weight
        denominator += weight
    return numerator / denominator if denominator else None


def relative_rate_delta(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None or baseline <= 0:
        return None
    return value / baseline - 1.0


def weighted_absolute_deviation(
    values_and_weights: Iterable[tuple[float | None, int | float]],
    center: float | None = None,
) -> float | None:
    values = [(value, weight) for value, weight in values_and_weights if value is not None and weight > 0]
    if not values:
        return None
    selected_center = center if center is not None else weighted_mean(values)
    if selected_center is None:
        return None
    return weighted_mean((abs(value - selected_center), weight) for value, weight in values)
