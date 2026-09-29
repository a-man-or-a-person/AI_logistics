"""Product adapter for high-volume Bear zones."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
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


@dataclass(frozen=True, slots=True)
class BearVolumeZonesParameters:
    volume_threshold: float
    singleton_threshold: float

    @classmethod
    def from_raw(cls, parameters: Mapping[str, ModeParameterValue]) -> BearVolumeZonesParameters:
        unknown = set(parameters) - {"volume_threshold", "singleton_threshold"}
        if unknown:
            raise ProductClusteringError(
                "INVALID_MODE_PARAMETERS",
                f"Неизвестные parameters: {', '.join(sorted(unknown))}.",
                400,
            )
        volume_threshold = number(
            parameters.get("volume_threshold", DEFAULT_THRESHOLD),
            "Порог объёмной зоны должен быть числом.",
        )
        singleton_threshold = fixed_singleton(
            parameters.get("singleton_threshold", SINGLETON_THRESHOLD)
        )
        if not any(abs(volume_threshold - option) < 1e-9 for option in THRESHOLD_CHOICES):
            raise ProductClusteringError(
                "INVALID_MODE_PARAMETERS",
                "Допустимые пороги объёмных зон: +20%, +25%, +30%, +35%, +40% или +50%.",
                400,
            )
        return cls(volume_threshold, singleton_threshold)

    @classmethod
    def from_selection(cls, selection: ModeSelection) -> BearVolumeZonesParameters:
        values = selection.as_parameters()
        return cls(
            cast(float, values["volume_threshold"]),
            cast(float, values["singleton_threshold"]),
        )

    def selection(self) -> ModeSelection:
        return ModeSelection.from_mapping(
            "bear_volume_zones",
            {
                "volume_threshold": self.volume_threshold,
                "singleton_threshold": self.singleton_threshold,
            },
        )


BEAR_VOLUME_ZONES_CAPABILITIES = ModeCapabilities(
    mode_id="bear_volume_zones",
    parameters=(
        ModeParameterCapability("volume_threshold", "choice", DEFAULT_THRESHOLD, THRESHOLD_CHOICES),
        ModeParameterCapability(
            "singleton_threshold",
            "choice",
            SINGLETON_THRESHOLD,
            (SINGLETON_THRESHOLD,),
            fixed=True,
        ),
    ),
    semantic_dimensions=("geography", "volume"),
    result_kind="zones",
    comparison_parameters=(
        ("volume_threshold", DEFAULT_THRESHOLD),
        ("singleton_threshold", SINGLETON_THRESHOLD),
    ),
)


class BearVolumeZonesProductMode:
    capabilities = BEAR_VOLUME_ZONES_CAPABILITIES

    def __init__(self, clusterer: Clusterer) -> None:
        self._clusterer = clusterer

    def select(self, parameters: Mapping[str, ModeParameterValue]) -> ModeSelection:
        return BearVolumeZonesParameters.from_raw(parameters).selection()

    def evaluate(
        self, selection: ModeSelection, dataset: ModeDataset, operation: ModeOperation
    ) -> ModePreview | ModeOutcome:
        points = tuple(
            replace(point, weighted_price=None, weighted_rub_per_km=None)
            for point in dataset.points
            if point.trip_count > 0
        )
        if operation == "preview":
            return ModePreview(
                selection,
                tuple(point.id for point in points),
                self._clusterer.algorithm,
                preview_point_states(dataset.points),
                product_warnings(dataset.quality),
            )
        if not points:
            raise ProductClusteringError(
                "INSUFFICIENT_POINTS",
                "Нет точек с положительным объёмом перевозок для объёмных зон.",
                422,
            )
        full_graph = dataset.spatial_graph
        if full_graph is None:
            raise ValueError("Bear volume zones run requires a full spatial graph")
        graph = full_graph.induced_subgraph({point.id for point in points})
        parameters = BearVolumeZonesParameters.from_selection(selection)
        algorithm_parameters = {
            "spatial_graph": graph,
            "volume_threshold": parameters.volume_threshold,
            "singleton_threshold": parameters.singleton_threshold,
        }
        try:
            result = self._clusterer.fit(list(points), algorithm_parameters)
        except AssertionError as error:
            raise ProductClusteringError("CONNECTIVITY_VIOLATION", str(error), 422) from error
        except ValueError as error:
            raise ProductClusteringError("INSUFFICIENT_POINTS", str(error), 422) from error
        status = "no_bears" if not result.clusters else "success"
        regional_mean = result.metrics.get("regional_mean_trip_count")
        candidate_ids = frozenset(
            point.id
            for point in dataset.points
            if regional_mean is not None
            and regional_mean > 0
            and point.trip_count / regional_mean - 1 >= parameters.volume_threshold
        )
        return ModeOutcome(
            selection,
            status,
            result,
            outcome_point_states(
                dataset.points,
                result,
                candidate_ids=candidate_ids,
                candidate_status="bear_volume_candidate",
            ),
            product_warnings(dataset.quality),
        )
