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
    shipment_count: float = 0


@dataclass(frozen=True, slots=True)
class ClusterSummary:
    cluster_id: int
    point_count: int
    shipment_count: float
    shipment_share: float
    centroid: tuple[float, float]
    medoid_point_id: str
    medoid: tuple[float, float]


@dataclass(frozen=True, slots=True)
class ClusterResult:
    algorithm: str
    parameters: dict[str, Any]
    point_assignments: dict[str, int]
    clusters: tuple[ClusterSummary, ...]
    noise_point_ids: tuple[str, ...]
    metrics: dict[str, float | int | None]

    def as_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "parameters": self.parameters,
            "point_assignments": self.point_assignments,
            "clusters": [asdict(cluster) for cluster in self.clusters],
            "noise_point_ids": list(self.noise_point_ids),
            "metrics": self.metrics,
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


def summarize_assignments(
    points: list[ClusterPoint],
    assignments: dict[str, int],
    *,
    algorithm: str,
    parameters: dict[str, Any],
    metrics: dict[str, float | int | None] | None = None,
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
    total_shipments = sum(max(point.shipment_count, 0) for point in points)
    for cluster_id, cluster_points in sorted(grouped.items()):
        centroid = (
            sum(point.x for point in cluster_points) / len(cluster_points),
            sum(point.y for point in cluster_points) / len(cluster_points),
        )
        medoid = _medoid(cluster_points)
        summaries.append(
            ClusterSummary(
                cluster_id=cluster_id,
                point_count=len(cluster_points),
                shipment_count=sum(max(point.shipment_count, 0) for point in cluster_points),
                shipment_share=(
                    sum(max(point.shipment_count, 0) for point in cluster_points)
                    / total_shipments
                    if total_shipments
                    else 0
                ),
                centroid=centroid,
                medoid_point_id=medoid.id,
                medoid=(medoid.x, medoid.y),
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
