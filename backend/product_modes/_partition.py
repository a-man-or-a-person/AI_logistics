"""Small shared mechanics for the three partition-mode adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, TypeAlias, cast

from backend.product_modes.catalog import ModeParameterValue
from backend.product_modes.errors import ProductClusteringError
from ml.spatial.graph import SpatialGraph

K_MIN, K_MAX = 2, 20
KMode: TypeAlias = Literal["auto", "manual"]
ClusterCount: TypeAlias = int | Literal["auto"]


def normalize_k(
    parameters: Mapping[str, ModeParameterValue],
) -> tuple[KMode, ClusterCount]:
    k_mode = parameters.get("k_mode")
    raw_k = parameters.get("n_clusters")
    if k_mode is None:
        k_mode = "auto" if raw_k in (None, "auto") else "manual"
    if k_mode not in {"auto", "manual"}:
        raise ProductClusteringError(
            "INVALID_MODE_PARAMETERS", "k_mode должен быть auto или manual.", 400
        )
    if k_mode == "auto":
        return cast(KMode, k_mode), "auto"
    if isinstance(raw_k, bool) or not isinstance(raw_k, int) or not K_MIN <= raw_k <= K_MAX:
        raise ProductClusteringError(
            "INVALID_CLUSTER_COUNT",
            f"n_clusters должен быть целым числом от {K_MIN} до {K_MAX}.",
            400,
        )
    return cast(KMode, k_mode), raw_k


def number(value: ModeParameterValue, message: str) -> float:
    if isinstance(value, bool):
        raise ProductClusteringError("INVALID_MODE_PARAMETERS", message, 400)
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ProductClusteringError("INVALID_MODE_PARAMETERS", message, 400) from error


def validate_k(n_clusters: int, point_count: int, graph: SpatialGraph) -> None:
    clusterable = point_count - len(graph.isolated_point_ids)
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
