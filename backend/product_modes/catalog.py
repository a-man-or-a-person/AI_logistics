"""Explicit Product-mode registration for incremental runtime migration."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
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
class ModeDataQuality:
    """Common data-quality facts available to every Product adapter."""

    contains_forecast: bool = False
    mixed_economic_segments: bool = False
    unresolved_points: int = 0
    economic_unavailable_points: int = 0


@dataclass(frozen=True, slots=True)
class ModeDataset:
    """Shared Product data prepared before mode-specific eligibility filtering."""

    points: tuple[ClusterPoint, ...]
    spatial_graph: SpatialGraph | None
    quality: ModeDataQuality = field(default_factory=ModeDataQuality)

    def __post_init__(self) -> None:
        point_ids = tuple(point.id for point in self.points)
        if len(set(point_ids)) != len(point_ids):
            raise ValueError("Mode dataset point IDs must be unique")
        if self.spatial_graph is not None and set(point_ids) != set(self.spatial_graph.node_ids):
            raise ValueError("Mode dataset points must match full spatial graph nodes")


@dataclass(frozen=True, slots=True)
class ProductWarning:
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True, slots=True)
class ModePointState:
    point_id: str
    status: str


@dataclass(frozen=True, slots=True)
class ModePreview:
    """Mode-normalized parameters and the points eligible for evaluation."""

    selection: ModeSelection
    eligible_point_ids: tuple[str, ...]
    algorithm: str = ""
    point_states: tuple[ModePointState, ...] = ()
    warnings: tuple[ProductWarning, ...] = ()


@dataclass(frozen=True, slots=True)
class ModeOutcome:
    """Algorithm result plus Product status and point-state semantics."""

    selection: ModeSelection
    status: ModeStatus
    result: ClusterResult
    point_states: tuple[ModePointState, ...] = ()
    warnings: tuple[ProductWarning, ...] = ()


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


def default_product_mode_catalog(
    geography_clusterer: Clusterer | None = None,
    geo_cost_clusterer: Clusterer | None = None,
    geo_volume_clusterer: Clusterer | None = None,
    bear_zones_clusterer: Clusterer | None = None,
    bear_volume_zones_clusterer: Clusterer | None = None,
) -> ProductModeCatalog:
    """Compose the frozen Product v1 mode set explicitly."""

    from backend.product_modes.bear_volume_zones import BearVolumeZonesProductMode
    from backend.product_modes.bear_zones import BearZonesProductMode
    from backend.product_modes.geo_cost import GeoCostProductMode
    from backend.product_modes.geo_volume import GeoVolumeProductMode
    from backend.product_modes.geography import GeographyProductMode
    from ml.clustering.bear_volume_zones import BearVolumeZoneDetector
    from ml.clustering.bear_zones import BearZoneDetector
    from ml.clustering.geo_cost import GeoCostClusterer
    from ml.clustering.geo_volume import GeoVolumeClusterer
    from ml.clustering.geographic import GeographicClusterer

    return ProductModeCatalog(
        (
            GeographyProductMode(geography_clusterer or GeographicClusterer()),
            GeoCostProductMode(geo_cost_clusterer or GeoCostClusterer()),
            GeoVolumeProductMode(geo_volume_clusterer or GeoVolumeClusterer()),
            BearZonesProductMode(bear_zones_clusterer or BearZoneDetector()),
            BearVolumeZonesProductMode(bear_volume_zones_clusterer or BearVolumeZoneDetector()),
        )
    )
