"""Product adapter for geography-plus-cost clustering."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from backend.product_modes._partition import (
    K_MAX,
    K_MIN,
    ClusterCount,
    KMode,
    normalize_k,
    number,
    validate_k,
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

WEIGHT_PRESETS = ((0.8, 0.2), (0.7, 0.3), (0.6, 0.4))


@dataclass(frozen=True, slots=True)
class GeoCostParameters:
    k_mode: KMode
    n_clusters: ClusterCount
    geography_weight: float
    economics_weight: float

    @classmethod
    def from_raw(cls, parameters: Mapping[str, ModeParameterValue]) -> GeoCostParameters:
        allowed = {"k_mode", "n_clusters", "geography_weight", "economics_weight"}
        unknown = set(parameters) - allowed
        if unknown:
            raise ProductClusteringError(
                "INVALID_MODE_PARAMETERS",
                f"Неизвестные parameters: {', '.join(sorted(unknown))}.",
                400,
            )
        k_mode, n_clusters = normalize_k(parameters)
        geography_weight = number(
            parameters.get("geography_weight", 0.7), "geography_weight должен быть числом."
        )
        economics_weight = number(
            parameters.get("economics_weight", 0.3), "economics_weight должен быть числом."
        )
        if not any(
            abs(geography_weight - geography) < 1e-9 and abs(economics_weight - economics) < 1e-9
            for geography, economics in WEIGHT_PRESETS
        ):
            raise ProductClusteringError(
                "INVALID_MODE_PARAMETERS",
                "Допустимы веса Geography/Cost: 80/20, 70/30 или 60/40.",
                400,
            )
        return cls(
            k_mode,
            n_clusters,
            geography_weight,
            economics_weight,
        )

    @classmethod
    def from_selection(cls, selection: ModeSelection) -> GeoCostParameters:
        values = selection.as_parameters()
        return cls(
            cast(KMode, values["k_mode"]),
            cast(ClusterCount, values["n_clusters"]),
            cast(float, values["geography_weight"]),
            cast(float, values["economics_weight"]),
        )

    def selection(self) -> ModeSelection:
        return ModeSelection.from_mapping(
            "geo_cost",
            {
                "k_mode": self.k_mode,
                "n_clusters": self.n_clusters,
                "geography_weight": self.geography_weight,
                "economics_weight": self.economics_weight,
            },
        )


GEO_COST_CAPABILITIES = ModeCapabilities(
    mode_id="geo_cost",
    parameters=(
        ModeParameterCapability("k_mode", "choice", "auto", ("auto", "manual")),
        ModeParameterCapability("n_clusters", "cluster_count", "auto", minimum=2, maximum=20),
        ModeParameterCapability("geography_weight", "choice", 0.7, (0.8, 0.7, 0.6)),
        ModeParameterCapability("economics_weight", "choice", 0.3, (0.2, 0.3, 0.4)),
    ),
    semantic_dimensions=("geography", "economics"),
    result_kind="partition",
    presets=tuple(
        (("geography_weight", geography), ("economics_weight", economics))
        for geography, economics in WEIGHT_PRESETS
    ),
    comparison_parameters=(
        ("k_mode", "auto"),
        ("n_clusters", "auto"),
        ("geography_weight", 0.7),
        ("economics_weight", 0.3),
    ),
)


class GeoCostProductMode:
    capabilities = GEO_COST_CAPABILITIES

    def __init__(self, clusterer: Clusterer) -> None:
        self._clusterer = clusterer

    def select(self, parameters: Mapping[str, ModeParameterValue]) -> ModeSelection:
        return GeoCostParameters.from_raw(parameters).selection()

    def evaluate(
        self, selection: ModeSelection, dataset: ModeDataset, operation: ModeOperation
    ) -> ModePreview | ModeOutcome:
        points = tuple(
            point
            for point in dataset.points
            if point.trip_count > 0
            and point.weighted_price is not None
            and point.weighted_rub_per_km is not None
        )
        eligible_ids = frozenset(point.id for point in points)
        unavailable_ids = frozenset(
            point.id for point in dataset.points if point.id not in eligible_ids
        )
        if operation == "preview":
            return ModePreview(
                selection,
                tuple(point.id for point in points),
                self._clusterer.algorithm,
                preview_point_states(dataset.points, unavailable_ids=unavailable_ids),
                product_warnings(
                    dataset.quality,
                    mixed_economic_segments=True,
                    economic_unavailable=True,
                ),
            )
        if len(dataset.points) < 2:
            raise ProductClusteringError(
                "INSUFFICIENT_POINTS",
                "Недостаточно точек с координатами для разбиения.",
                422,
            )
        if len(points) < 2:
            raise ProductClusteringError(
                "INSUFFICIENT_ECONOMICS",
                "Недостаточно точек с валидными price, route_length и ₽/км.",
                422,
            )
        full_graph = dataset.spatial_graph
        if full_graph is None:
            raise ValueError("Geo-cost run requires a full spatial graph")
        graph = full_graph.induced_subgraph({point.id for point in points})
        parameters = GeoCostParameters.from_selection(selection)
        if isinstance(parameters.n_clusters, int):
            validate_k(parameters.n_clusters, len(points), graph)
        algorithm_parameters = {
            "spatial_graph": graph,
            "n_clusters": parameters.n_clusters,
            "k_min": K_MIN,
            "k_max": K_MAX,
            "geography_weight": parameters.geography_weight,
            "economics_weight": parameters.economics_weight,
        }
        try:
            result = self._clusterer.fit(list(points), algorithm_parameters)
        except AssertionError as error:
            raise ProductClusteringError("CONNECTIVITY_VIOLATION", str(error), 422) from error
        except ValueError as error:
            code = (
                "INVALID_CLUSTER_COUNT"
                if isinstance(parameters.n_clusters, int)
                else "INSUFFICIENT_ECONOMICS"
            )
            raise ProductClusteringError(code, str(error), 422) from error
        return ModeOutcome(
            selection,
            "success",
            result,
            outcome_point_states(dataset.points, result, unavailable_ids=unavailable_ids),
            product_warnings(
                dataset.quality,
                mixed_economic_segments=True,
                economic_unavailable=True,
            ),
        )
