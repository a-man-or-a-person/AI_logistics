"""Generic interface consumed by experiments and territorialization."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ClusterPoint:
    id: str
    name: str
    region: str
    x: float
    y: float
    trip_count: int = 0
    weighted_price: float | None = None
    weighted_rub_per_km: float | None = None
    data_quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ClusterSummary:
    cluster_id: int
    point_count: int
    trip_count: int
    trip_share: float
    centroid: tuple[float, float]
    medoid_point_id: str
    medoid: tuple[float, float]
    cluster_type: str = "normal"
    weighted_price: float | None = None
    weighted_rub_per_km: float | None = None
    regional_weighted_rub_per_km: float | None = None
    relative_rate_delta: float | None = None
    mean_trip_count: float | None = None
    regional_mean_trip_count: float | None = None
    relative_volume_delta: float | None = None
    point_ids: tuple[str, ...] = ()
    mean_radius_km: float | None = None
    p95_radius_km: float | None = None
    max_radius_km: float | None = None
    connected: bool | None = None

    @property
    def shipment_count(self) -> int:
        """Deprecated compatibility alias; values are trips, never Pulse units."""
        return self.trip_count

    @property
    def shipment_share(self) -> float:
        return self.trip_share


@dataclass(frozen=True, slots=True)
class ClusterResult:
    algorithm: str
    parameters: dict[str, Any]
    point_assignments: dict[str, int]
    clusters: tuple[ClusterSummary, ...]
    noise_point_ids: tuple[str, ...]
    metrics: dict[str, Any]
    mode: str = "legacy"
    internal_algorithm: str | None = None
    regional_weighted_rub_per_km: float | None = None
    filters: dict[str, Any] | None = None
    period_types: tuple[str, ...] = ()
    price_types: tuple[str, ...] = ()
    vehicle_types: tuple[str, ...] = ()
    tonnage_ids: tuple[str, ...] = ()
    contains_forecast: bool = False
    mixed_tariff_segments: bool = False
    mixed_segment_details: dict[str, bool] | None = None
    outliers: tuple[dict[str, Any], ...] = ()
    data_quality: dict[str, Any] | None = None
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "parameters": self.parameters,
            "point_assignments": self.point_assignments,
            "clusters": [asdict(cluster) for cluster in self.clusters],
            "noise_point_ids": list(self.noise_point_ids),
            "metrics": self.metrics,
            "mode": self.mode,
            "internal_algorithm": self.internal_algorithm,
            "regional_weighted_rub_per_km": self.regional_weighted_rub_per_km,
            "filters": self.filters or {},
            "period_types": list(self.period_types),
            "price_types": list(self.price_types),
            "vehicle_types": list(self.vehicle_types),
            "tonnage_ids": list(self.tonnage_ids),
            "contains_forecast": self.contains_forecast,
            "mixed_tariff_segments": self.mixed_tariff_segments,
            "mixed_segment_details": self.mixed_segment_details or {},
            "outliers": list(self.outliers),
            "data_quality": self.data_quality or {},
            "warnings": list(self.warnings),
        }


class Clusterer(ABC):
    algorithm: str

    @abstractmethod
    def fit(self, points: list[ClusterPoint], parameters: dict[str, Any]) -> ClusterResult:
        """Fit one algorithm without depending on frontend or polygonization."""


def _medoid(points: list[ClusterPoint]) -> ClusterPoint:
    return min(
        points,
        key=lambda candidate: sum(
            math.hypot(candidate.x - other.x, candidate.y - other.y) for other in points
        ),
    )


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * 0.95
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize_assignments(
    points: list[ClusterPoint],
    assignments: dict[str, int],
    *,
    algorithm: str,
    parameters: dict[str, Any],
    metrics: dict[str, Any] | None = None,
) -> ClusterResult:
    point_ids = {point.id for point in points}
    if set(assignments) != point_ids:
        missing = sorted(point_ids - set(assignments))
        unexpected = sorted(set(assignments) - point_ids)
        raise ValueError(f"Assignments mismatch: missing={missing}, unexpected={unexpected}")
    grouped: dict[int, list[ClusterPoint]] = {}
    noise: list[str] = []
    for point in points:
        cluster_id = assignments[point.id]
        if cluster_id < 0:
            noise.append(point.id)
        else:
            grouped.setdefault(cluster_id, []).append(point)

    summaries: list[ClusterSummary] = []
    from ml.clustering.economics import weighted_mean

    total_trips = sum(max(point.trip_count, 0) for point in points)
    for cluster_id, cluster_points in sorted(grouped.items()):
        centroid = (
            sum(point.x for point in cluster_points) / len(cluster_points),
            sum(point.y for point in cluster_points) / len(cluster_points),
        )
        medoid = _medoid(cluster_points)
        radii_m = [
            math.hypot(point.x - medoid.x, point.y - medoid.y)
            for point in cluster_points
        ]
        summaries.append(
            ClusterSummary(
                cluster_id=cluster_id,
                point_count=len(cluster_points),
                trip_count=sum(max(point.trip_count, 0) for point in cluster_points),
                trip_share=(
                    sum(max(point.trip_count, 0) for point in cluster_points)
                    / total_trips
                    if total_trips
                    else 0
                ),
                centroid=centroid,
                medoid_point_id=medoid.id,
                medoid=(medoid.x, medoid.y),
                weighted_price=weighted_mean(
                    (point.weighted_price, point.trip_count) for point in cluster_points
                ),
                weighted_rub_per_km=weighted_mean(
                    (point.weighted_rub_per_km, point.trip_count) for point in cluster_points
                ),
                point_ids=tuple(sorted(point.id for point in cluster_points)),
                mean_radius_km=sum(radii_m) / len(radii_m) / 1000,
                p95_radius_km=_p95(radii_m) / 1000,
                max_radius_km=max(radii_m) / 1000,
            )
        )
    return ClusterResult(
        algorithm=algorithm,
        parameters=dict(parameters),
        point_assignments=dict(assignments),
        clusters=tuple(summaries),
        noise_point_ids=tuple(sorted(noise)),
        metrics=dict(metrics or {}),
    )
