"""Product adapter for economic Bear zones."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from backend.product_modes._bear import (
    DEFAULT_THRESHOLD,
    SINGLETON_THRESHOLD,
    THRESHOLD_CHOICES,
    fixed_singleton,
    number,
)
from backend.product_modes._presentation import (
    outcome_point_states,
    preview_point_states,
    product_warnings,
)
from backend.product_modes.catalog import (
    ModeCapabilities,
    ModeDataset,
    ModeOperation,
    ModeOutcome,
    ModeParameterCapability,
    ModeParameterValue,
    ModePreview,
    ModeSelection,
)
from backend.product_modes.errors import ProductClusteringError
from ml.clustering.base import Clusterer
from ml.clustering.economics import relative_rate_delta


@dataclass(frozen=True, slots=True)
class BearZonesParameters:
    bear_threshold: float
    singleton_threshold: float

    @classmethod
    def from_raw(cls, parameters: Mapping[str, ModeParameterValue]) -> BearZonesParameters:
        unknown = set(parameters) - {"bear_threshold", "singleton_threshold"}
        if unknown:
            raise ProductClusteringError(
                "INVALID_MODE_PARAMETERS",
                f"Неизвестные parameters: {', '.join(sorted(unknown))}.",
                400,
            )
        bear_threshold = number(
            parameters.get("bear_threshold", DEFAULT_THRESHOLD),
            "Порог Bear должен быть числом.",
        )
        singleton_threshold = fixed_singleton(
            parameters.get("singleton_threshold", SINGLETON_THRESHOLD)
        )
        if not any(abs(bear_threshold - option) < 1e-9 for option in THRESHOLD_CHOICES):
            raise ProductClusteringError(
                "INVALID_MODE_PARAMETERS",
                "Допустимые пороги Bear: +20%, +25%, +30%, +35%, +40% или +50%.",
                400,
            )
        return cls(bear_threshold, singleton_threshold)

    @classmethod
    def from_selection(cls, selection: ModeSelection) -> BearZonesParameters:
        values = selection.as_parameters()
        return cls(
            cast(float, values["bear_threshold"]),
            cast(float, values["singleton_threshold"]),
        )

    def selection(self) -> ModeSelection:
        return ModeSelection.from_mapping(
            "bear_zones",
            {
                "bear_threshold": self.bear_threshold,
                "singleton_threshold": self.singleton_threshold,
            },
        )


BEAR_ZONES_CAPABILITIES = ModeCapabilities(
    mode_id="bear_zones",
    parameters=(
        ModeParameterCapability("bear_threshold", "choice", DEFAULT_THRESHOLD, THRESHOLD_CHOICES),
        ModeParameterCapability(
            "singleton_threshold",
            "choice",
            SINGLETON_THRESHOLD,
            (SINGLETON_THRESHOLD,),
            fixed=True,
        ),
    ),
    semantic_dimensions=("geography", "economics"),
    result_kind="zones",
    comparison_parameters=(
        ("bear_threshold", DEFAULT_THRESHOLD),
        ("singleton_threshold", SINGLETON_THRESHOLD),
    ),
)


class BearZonesProductMode:
    capabilities = BEAR_ZONES_CAPABILITIES

    def __init__(self, clusterer: Clusterer) -> None:
        self._clusterer = clusterer

    def select(self, parameters: Mapping[str, ModeParameterValue]) -> ModeSelection:
        return BearZonesParameters.from_raw(parameters).selection()

    def evaluate(
        self, selection: ModeSelection, dataset: ModeDataset, operation: ModeOperation
    ) -> ModePreview | ModeOutcome:
        points = tuple(
            point
            for point in dataset.points
            if point.trip_count > 0 and point.weighted_rub_per_km is not None
        )
        unavailable_ids = frozenset(
            point.id
            for point in dataset.points
            if not (
                point.trip_count > 0
                and point.weighted_price is not None
                and point.weighted_rub_per_km is not None
            )
        )
        if operation == "preview":
            return ModePreview(
                selection,
                tuple(point.id for point in points),
                self._clusterer.algorithm,
                preview_point_states(dataset.points, unavailable_ids=unavailable_ids),
                product_warnings(dataset.quality, mixed_economic_segments=True),
            )
        if not points:
            raise ProductClusteringError(
                "INSUFFICIENT_ECONOMICS", "Нет валидной экономики для Bear Zones.", 422
            )
        full_graph = dataset.spatial_graph
        if full_graph is None:
            raise ValueError("Bear zones run requires a full spatial graph")
        graph = full_graph.induced_subgraph({point.id for point in points})
        parameters = BearZonesParameters.from_selection(selection)
        algorithm_parameters = {
            "spatial_graph": graph,
            "bear_threshold": parameters.bear_threshold,
            "singleton_threshold": parameters.singleton_threshold,
        }
        try:
            result = self._clusterer.fit(list(points), algorithm_parameters)
        except AssertionError as error:
            raise ProductClusteringError("CONNECTIVITY_VIOLATION", str(error), 422) from error
        except ValueError as error:
            raise ProductClusteringError("INSUFFICIENT_ECONOMICS", str(error), 422) from error
        status = "no_bears" if not result.clusters else "success"
        regional_rate = result.regional_weighted_rub_per_km
        candidate_ids = frozenset(
            point.id
            for point in dataset.points
            if regional_rate is not None
            and relative_rate_delta(point.weighted_rub_per_km, regional_rate) is not None
            and relative_rate_delta(point.weighted_rub_per_km, regional_rate)
            >= parameters.bear_threshold
        )
        return ModeOutcome(
            selection,
            status,
            result,
            outcome_point_states(
                dataset.points,
                result,
                unavailable_ids=unavailable_ids,
                candidate_ids=candidate_ids,
                candidate_status="bear_candidate",
            ),
            product_warnings(dataset.quality, mixed_economic_segments=True),
        )
