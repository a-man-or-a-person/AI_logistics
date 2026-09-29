"""Product adapter for the geography clustering mode."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from backend.product_modes._partition import DEFAULT_MANUAL_K
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

K_MIN, K_MAX = 2, 20

GEOGRAPHY_CAPABILITIES = ModeCapabilities(
    mode_id="geography",
    parameters=(
        ModeParameterCapability("k_mode", "choice", "auto", ("auto", "manual")),
        ModeParameterCapability(
            "n_clusters",
            "cluster_count",
            "auto",
            minimum=K_MIN,
            maximum=K_MAX,
            manual_default=DEFAULT_MANUAL_K,
        ),
    ),
    semantic_dimensions=("geography",),
    result_kind="partition",
    comparison_parameters=(("k_mode", "auto"), ("n_clusters", "auto")),
)


class GeographyProductMode:
    """Own geography Product semantics while reusing the frozen ML algorithm."""

    capabilities = GEOGRAPHY_CAPABILITIES

    def __init__(self, clusterer: Clusterer) -> None:
        self._clusterer = clusterer

    def select(self, parameters: Mapping[str, ModeParameterValue]) -> ModeSelection:
        unknown = set(parameters) - set(self.capabilities.parameter_names)
        if unknown:
            raise ProductClusteringError(
                "INVALID_MODE_PARAMETERS",
                f"Неизвестные parameters: {', '.join(sorted(unknown))}.",
                400,
            )

        k_mode = parameters.get("k_mode")
        raw_k = parameters.get("n_clusters")
        if k_mode is None:
            k_mode = "auto" if raw_k in (None, "auto") else "manual"
        if k_mode not in {"auto", "manual"}:
            raise ProductClusteringError(
                "INVALID_MODE_PARAMETERS", "k_mode должен быть auto или manual.", 400
            )
        if k_mode == "auto":
            n_clusters: int | str = "auto"
        elif isinstance(raw_k, bool) or not isinstance(raw_k, int) or not K_MIN <= raw_k <= K_MAX:
            raise ProductClusteringError(
                "INVALID_CLUSTER_COUNT",
                f"n_clusters должен быть целым числом от {K_MIN} до {K_MAX}.",
                400,
            )
        else:
            n_clusters = raw_k
        return ModeSelection.from_mapping("geography", {"k_mode": k_mode, "n_clusters": n_clusters})

    def evaluate(
        self,
        selection: ModeSelection,
        dataset: ModeDataset,
        operation: ModeOperation,
    ) -> ModePreview | ModeOutcome:
        points = tuple(
            replace(point, weighted_price=None, weighted_rub_per_km=None)
            for point in dataset.points
        )
        if operation == "preview":
            return ModePreview(
                selection,
                tuple(point.id for point in points),
                self._clusterer.algorithm,
                preview_point_states(dataset.points),
                product_warnings(dataset.quality),
            )
        if operation != "run":
            raise ValueError(f"Unknown Product mode operation: {operation}")
        if len(points) < 2:
            raise ProductClusteringError(
                "INSUFFICIENT_POINTS",
                "Недостаточно точек с координатами для разбиения.",
                422,
            )
        graph = dataset.spatial_graph
        if graph is None:
            raise ValueError("Geography run requires a full spatial graph")

        parameters = selection.as_parameters()
        n_clusters = parameters["n_clusters"]
        if isinstance(n_clusters, int):
            clusterable = len(points) - len(graph.isolated_point_ids)
            components = sum(len(component) > 1 for component in graph.connected_components)
            if n_clusters > clusterable or n_clusters < components:
                raise ProductClusteringError(
                    "INVALID_CLUSTER_COUNT",
                    (
                        f"K={n_clusters} невозможно для {clusterable} связанных точек "
                        f"в {components} компонентах."
                    ),
                    422,
                )

        algorithm_parameters = {
            "spatial_graph": graph,
            "n_clusters": n_clusters,
            "k_min": K_MIN,
            "k_max": K_MAX,
        }
        try:
            result = self._clusterer.fit(list(points), algorithm_parameters)
        except AssertionError as error:
            raise ProductClusteringError("CONNECTIVITY_VIOLATION", str(error), 422) from error
        except ValueError as error:
            code = "INVALID_CLUSTER_COUNT" if isinstance(n_clusters, int) else "INSUFFICIENT_POINTS"
            raise ProductClusteringError(code, str(error), 422) from error
        return ModeOutcome(
            selection,
            "success",
            result,
            outcome_point_states(dataset.points, result),
            product_warnings(dataset.quality),
        )
