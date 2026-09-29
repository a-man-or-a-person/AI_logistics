"""Explicit Product-mode registration for incremental runtime migration."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Literal, Protocol

from ml.clustering.base import Clusterer, ClusterPoint, ClusterResult
from ml.spatial.graph import SpatialGraph

ModeParameterValue = str | int | float | bool | None
ModeParameterKind = Literal["choice", "cluster_count", "number"]
ModeResultKind = Literal["partition", "zones"]
ModeParameterValues = tuple[tuple[str, ModeParameterValue], ...]
ModeOperation = Literal["preview", "run"]
ModeStatus = Literal["success", "no_bears"]
ModeSemanticDimension = Literal["geography", "economics", "volume"]
ProductModeId = Literal[
    "geography",
    "geo_cost",
    "geo_volume",
    "bear_zones",
    "bear_volume_zones",
]

CANONICAL_PRODUCT_MODE_IDS: Final[tuple[ProductModeId, ...]] = (
    "geography",
    "geo_cost",
    "geo_volume",
    "bear_zones",
    "bear_volume_zones",
)


@dataclass(frozen=True, slots=True)
class ModeParameterCapability:
    """Machine-readable facts about one Product-mode parameter."""

    name: str
    kind: ModeParameterKind
    default: ModeParameterValue
    choices: tuple[ModeParameterValue, ...] = ()
    minimum: int | float | None = None
    maximum: int | float | None = None
    fixed: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Parameter name cannot be empty")
        if self.kind not in {"choice", "cluster_count", "number"}:
            raise ValueError(f"Unknown parameter kind: {self.kind}")
        if len(set(self.choices)) != len(self.choices):
            raise ValueError(f"Duplicate choices for parameter: {self.name}")
        if self.choices and self.default not in self.choices:
            raise ValueError("Default must be one of the declared choices")
        if self.kind == "choice" and not self.choices:
            raise ValueError("Choice parameter must declare choices")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError(f"Invalid limits for parameter: {self.name}")
        if not self._kind_accepts(self.default):
            raise ValueError(f"Default is incompatible with parameter kind: {self.kind}")
        if not self.accepts(self.default):
            raise ValueError("Default is outside declared limits")
        if self.fixed and self.choices != (self.default,):
            raise ValueError("Fixed parameter must declare only its default choice")

    def accepts(self, value: ModeParameterValue) -> bool:
        if not self._kind_accepts(value):
            return False
        if self.choices and value not in self.choices:
            return False
        if not isinstance(value, int | float) or isinstance(value, bool):
            return True
        if self.minimum is not None and value < self.minimum:
            return False
        return self.maximum is None or value <= self.maximum

    def _kind_accepts(self, value: ModeParameterValue) -> bool:
        if self.kind == "choice":
            return value in self.choices
        if self.kind == "cluster_count":
            return value == "auto" or (isinstance(value, int) and not isinstance(value, bool))
        return isinstance(value, int | float) and not isinstance(value, bool)


@dataclass(frozen=True, slots=True)
class ModeCapabilities:
    """Product facts that will become authoritative after mode migration."""

    mode_id: ProductModeId
    parameters: tuple[ModeParameterCapability, ...]
    semantic_dimensions: tuple[ModeSemanticDimension, ...]
    result_kind: ModeResultKind
    presets: tuple[ModeParameterValues, ...] = ()
    comparison_supported: bool = True
    comparison_parameters: ModeParameterValues = ()

    def __post_init__(self) -> None:
        if not self.mode_id:
            raise ValueError("Product mode ID cannot be empty")
        parameter_names = self.parameter_names
        duplicates = tuple(name for name, count in Counter(parameter_names).items() if count > 1)
        if duplicates:
            raise ValueError(f"Duplicate parameter names: {', '.join(duplicates)}")
        if not self.semantic_dimensions or len(set(self.semantic_dimensions)) != len(
            self.semantic_dimensions
        ):
            raise ValueError("Semantic dimensions must be non-empty and unique")
        unknown_dimensions = tuple(
            dimension
            for dimension in self.semantic_dimensions
            if dimension not in {"geography", "economics", "volume"}
        )
        if unknown_dimensions:
            raise ValueError(f"Unknown semantic dimensions: {', '.join(unknown_dimensions)}")
        if self.result_kind not in {"partition", "zones"}:
            raise ValueError(f"Unknown result kind: {self.result_kind}")
        parameter_by_name = {parameter.name: parameter for parameter in self.parameters}
        for values in (*self.presets, self.comparison_parameters):
            value_names = tuple(name for name, _ in values)
            if len(set(value_names)) != len(value_names):
                raise ValueError("Capability parameter values must use unique names")
            unknown = tuple(name for name in value_names if name not in parameter_names)
            if unknown:
                raise ValueError(f"Unknown preset parameters: {', '.join(unknown)}")
            for name, value in values:
                if not parameter_by_name[name].accepts(value):
                    raise ValueError(f"Unsupported preset value for {name}: {value}")
        if not self.comparison_supported and self.comparison_parameters:
            raise ValueError("Unsupported comparison cannot declare parameters")

    @property
    def parameter_names(self) -> tuple[str, ...]:
        return tuple(parameter.name for parameter in self.parameters)

    @property
    def default_parameters(self) -> ModeParameterValues:
        return tuple((parameter.name, parameter.default) for parameter in self.parameters)


@dataclass(frozen=True, slots=True)
class ModeSelection:
    """One mode and its adapter-normalized Product parameters."""

    mode_id: ProductModeId
    parameters: ModeParameterValues

    def __post_init__(self) -> None:
        if not self.mode_id:
            raise ValueError("Product mode ID cannot be empty")
        parameter_names = tuple(name for name, _ in self.parameters)
        if len(set(parameter_names)) != len(parameter_names):
            raise ValueError("Mode selection parameter names must be unique")
        if parameter_names != tuple(sorted(parameter_names)):
            raise ValueError("Mode selection parameters must use canonical order")

    @classmethod
    def from_mapping(
        cls, mode_id: ProductModeId, parameters: Mapping[str, ModeParameterValue]
    ) -> ModeSelection:
        return cls(mode_id, tuple(sorted(parameters.items())))

    def as_parameters(self) -> dict[str, ModeParameterValue]:
        return dict(self.parameters)


@dataclass(frozen=True, slots=True)
class ModeDataset:
    """Shared Product data prepared before mode-specific eligibility filtering."""

    points: tuple[ClusterPoint, ...]
    spatial_graph: SpatialGraph | None

    def __post_init__(self) -> None:
        point_ids = tuple(point.id for point in self.points)
        if len(set(point_ids)) != len(point_ids):
            raise ValueError("Mode dataset point IDs must be unique")
        if self.spatial_graph is not None and set(point_ids) != set(self.spatial_graph.node_ids):
            raise ValueError("Mode dataset points must match full spatial graph nodes")


@dataclass(frozen=True, slots=True)
class ModePreview:
    """Mode-normalized parameters and the points eligible for evaluation."""

    selection: ModeSelection
    eligible_point_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModeOutcome:
    """Algorithm result plus Product status and point-state semantics."""

    selection: ModeSelection
    status: ModeStatus
    result: ClusterResult


class ProductModeNotMigratedError(RuntimeError):
    """Guard against using a registration before its dedicated migration ticket."""


class ProductMode(Protocol):
    """Deep seam hiding one mode's future Product-specific behavior."""

    capabilities: ModeCapabilities

    def select(self, parameters: Mapping[str, ModeParameterValue]) -> ModeSelection: ...

    def evaluate(
        self,
        selection: ModeSelection,
        dataset: ModeDataset,
        operation: ModeOperation,
    ) -> ModePreview | ModeOutcome: ...


@dataclass(frozen=True, slots=True)
class PendingProductMode:
    """Temporary registration replaced mode-by-mode during migration."""

    capabilities: ModeCapabilities


class ProductModeCatalog:
    """Ordered collection of the explicitly supported Product modes."""

    def __init__(self, modes: tuple[ProductMode | PendingProductMode, ...]) -> None:
        capabilities: list[ModeCapabilities] = []
        for index, mode in enumerate(modes):
            capability = getattr(mode, "capabilities", None)
            if capability is None:
                raise ValueError(
                    f"Product mode registration is missing capabilities at index {index}"
                )
            if not isinstance(capability, ModeCapabilities):
                raise ValueError(
                    f"Product mode registration has invalid capabilities at index {index}"
                )
            capabilities.append(capability)
        mode_ids = tuple(capability.mode_id for capability in capabilities)
        duplicates = tuple(mode_id for mode_id, count in Counter(mode_ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"Duplicate Product mode IDs: {', '.join(duplicates)}")
        unknown = tuple(
            mode_id for mode_id in mode_ids if mode_id not in CANONICAL_PRODUCT_MODE_IDS
        )
        if unknown:
            raise ValueError(f"Unknown Product mode IDs: {', '.join(unknown)}")
        missing = tuple(
            mode_id for mode_id in CANONICAL_PRODUCT_MODE_IDS if mode_id not in mode_ids
        )
        if missing:
            raise ValueError(f"Missing Product mode IDs: {', '.join(missing)}")
        if mode_ids != CANONICAL_PRODUCT_MODE_IDS:
            raise ValueError("Product modes must use canonical order")
        incomplete = tuple(
            mode.capabilities.mode_id
            for mode in modes
            if not isinstance(mode, PendingProductMode)
            and (
                not callable(getattr(mode, "select", None))
                or not callable(getattr(mode, "evaluate", None))
            )
        )
        if incomplete:
            raise ValueError(
                "Product mode registration does not implement select/evaluate: "
                f"{', '.join(incomplete)}"
            )
        self._modes = modes
        self._mode_by_id = {mode.capabilities.mode_id: mode for mode in self._modes}

    @property
    def mode_ids(self) -> tuple[str, ...]:
        return tuple(mode.capabilities.mode_id for mode in self._modes)

    def manifest(self) -> tuple[ModeCapabilities, ...]:
        return tuple(mode.capabilities for mode in self._modes)

    def select(
        self,
        mode_id: str,
        parameters: Mapping[str, ModeParameterValue],
    ) -> ModeSelection:
        try:
            mode = self._mode_by_id[mode_id]
        except KeyError as error:
            raise ValueError(f"Unknown Product mode ID: {mode_id}") from error
        if isinstance(mode, PendingProductMode):
            raise ProductModeNotMigratedError(
                f"Product mode has not migrated to the catalog: {mode_id}"
            )
        return mode.select(parameters)

    def evaluate(
        self,
        selection: ModeSelection,
        dataset: ModeDataset,
        operation: ModeOperation,
    ) -> ModePreview | ModeOutcome:
        if operation not in {"preview", "run"}:
            raise ValueError(f"Unknown Product mode operation: {operation}")
        try:
            mode = self._mode_by_id[selection.mode_id]
        except KeyError as error:
            raise ValueError(f"Unknown Product mode ID: {selection.mode_id}") from error
        if isinstance(mode, PendingProductMode):
            raise ProductModeNotMigratedError(
                f"Product mode has not migrated to the catalog: {selection.mode_id}"
            )
        result = mode.evaluate(selection, dataset, operation)
        if operation == "preview" and not isinstance(result, ModePreview):
            raise TypeError("Product mode preview must return ModePreview")
        if operation == "run" and not isinstance(result, ModeOutcome):
            raise TypeError("Product mode run must return ModeOutcome")
        return result


_K_PARAMETERS = (
    ModeParameterCapability("k_mode", "choice", "auto", ("auto", "manual")),
    ModeParameterCapability("n_clusters", "cluster_count", "auto", minimum=2, maximum=20),
)
_GEOGRAPHY_WEIGHT = ModeParameterCapability("geography_weight", "choice", 0.7, (0.8, 0.7, 0.6))
_SINGLETON_THRESHOLD = ModeParameterCapability(
    "singleton_threshold", "choice", 0.7, (0.7,), fixed=True
)
_ZONE_THRESHOLD_CHOICES = (0.2, 0.25, 0.3, 0.35, 0.4, 0.5)


def _weight_presets(business_parameter: str) -> tuple[ModeParameterValues, ...]:
    return tuple(
        (
            ("geography_weight", geography_weight),
            (business_parameter, business_weight),
        )
        for geography_weight, business_weight in ((0.8, 0.2), (0.7, 0.3), (0.6, 0.4))
    )


def default_product_mode_catalog(
    geography_clusterer: Clusterer | None = None,
) -> ProductModeCatalog:
    """Compose the frozen Product v1 mode set explicitly."""

    from backend.product_modes.geography import GeographyProductMode
    from ml.clustering.geographic import GeographicClusterer

    return ProductModeCatalog(
        (
            GeographyProductMode(geography_clusterer or GeographicClusterer()),
            PendingProductMode(
                ModeCapabilities(
                    mode_id="geo_cost",
                    parameters=(
                        *_K_PARAMETERS,
                        _GEOGRAPHY_WEIGHT,
                        ModeParameterCapability(
                            "economics_weight",
                            "choice",
                            0.3,
                            (0.2, 0.3, 0.4),
                        ),
                    ),
                    semantic_dimensions=("geography", "economics"),
                    result_kind="partition",
                    presets=_weight_presets("economics_weight"),
                    comparison_parameters=(
                        ("k_mode", "auto"),
                        ("n_clusters", "auto"),
                        ("geography_weight", 0.7),
                        ("economics_weight", 0.3),
                    ),
                )
            ),
            PendingProductMode(
                ModeCapabilities(
                    mode_id="geo_volume",
                    parameters=(
                        *_K_PARAMETERS,
                        _GEOGRAPHY_WEIGHT,
                        ModeParameterCapability("volume_weight", "choice", 0.3, (0.2, 0.3, 0.4)),
                    ),
                    semantic_dimensions=("geography", "volume"),
                    result_kind="partition",
                    presets=_weight_presets("volume_weight"),
                    comparison_parameters=(
                        ("k_mode", "auto"),
                        ("n_clusters", "auto"),
                        ("geography_weight", 0.7),
                        ("volume_weight", 0.3),
                    ),
                )
            ),
            PendingProductMode(
                ModeCapabilities(
                    mode_id="bear_zones",
                    parameters=(
                        ModeParameterCapability(
                            "bear_threshold",
                            "choice",
                            0.35,
                            _ZONE_THRESHOLD_CHOICES,
                        ),
                        _SINGLETON_THRESHOLD,
                    ),
                    semantic_dimensions=("geography", "economics"),
                    result_kind="zones",
                    comparison_parameters=(
                        ("bear_threshold", 0.35),
                        ("singleton_threshold", 0.7),
                    ),
                )
            ),
            PendingProductMode(
                ModeCapabilities(
                    mode_id="bear_volume_zones",
                    parameters=(
                        ModeParameterCapability(
                            "volume_threshold",
                            "choice",
                            0.35,
                            _ZONE_THRESHOLD_CHOICES,
                        ),
                        _SINGLETON_THRESHOLD,
                    ),
                    semantic_dimensions=("geography", "volume"),
                    result_kind="zones",
                    comparison_parameters=(
                        ("volume_threshold", 0.35),
                        ("singleton_threshold", 0.7),
                    ),
                )
            ),
        )
    )
