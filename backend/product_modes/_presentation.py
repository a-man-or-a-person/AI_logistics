"""Shared Product presentation mechanics used behind the mode seam."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, TypeAlias

from backend.product_modes.catalog import (
    ModeDataQuality,
    ModePointState,
    ProductWarning,
)
from ml.clustering.base import ClusterPoint, ClusterResult

CandidatePointStatus: TypeAlias = Literal["bear_candidate", "bear_volume_candidate"]


def product_warnings(
    quality: ModeDataQuality,
    *,
    mixed_economic_segments: bool = False,
    economic_unavailable: bool = False,
) -> tuple[ProductWarning, ...]:
    warnings: list[ProductWarning] = []
    if quality.contains_forecast:
        warnings.append(
            ProductWarning(
                "CONTAINS_FORECAST",
                "В анализ включены прогнозные данные Pulse.",
            )
        )
    if mixed_economic_segments and quality.mixed_economic_segments:
        warnings.append(
            ProductWarning(
                "MIXED_ECONOMIC_SEGMENTS",
                (
                    "Различия ₽/км могут быть связаны не только с территорией, "
                    "но и со смешением тарифных сегментов."
                ),
            )
        )
    if quality.unresolved_points:
        warnings.append(
            ProductWarning(
                "COORDINATE_INCOMPLETE",
                "Часть точек не имеет координат и не может быть отображена на карте.",
            )
        )
    if economic_unavailable and quality.economic_unavailable_points:
        warnings.append(
            ProductWarning(
                "ECONOMIC_UNAVAILABLE",
                (
                    "Часть точек не имеет достаточных данных для расчёта ₽/км. "
                    "Они не участвовали в экономической кластеризации."
                ),
            )
        )
    return tuple(warnings)


def preview_point_states(
    points: Iterable[ClusterPoint], *, unavailable_ids: frozenset[str] = frozenset()
) -> tuple[ModePointState, ...]:
    return tuple(
        ModePointState(
            point.id,
            "economic_unavailable" if point.id in unavailable_ids else "ordinary",
        )
        for point in points
    )


def outcome_point_states(
    points: Iterable[ClusterPoint],
    result: ClusterResult,
    *,
    unavailable_ids: frozenset[str] = frozenset(),
    candidate_ids: frozenset[str] = frozenset(),
    candidate_status: CandidatePointStatus | None = None,
) -> tuple[ModePointState, ...]:
    cluster_types = {cluster.cluster_id: cluster.cluster_type for cluster in result.clusters}
    outlier_ids = {item["point_id"] for item in result.outliers}
    states: list[ModePointState] = []
    for point in points:
        cluster_id = result.point_assignments.get(point.id)
        if point.id in unavailable_ids:
            status = "economic_unavailable"
        elif cluster_id is not None and cluster_id >= 0:
            status = cluster_types.get(cluster_id, "normal")
        elif point.id in candidate_ids:
            status = candidate_status or "ordinary"
        elif point.id in outlier_ids:
            status = "spatial_outlier"
        else:
            status = "ordinary"
        states.append(ModePointState(point.id, status))
    return tuple(states)
