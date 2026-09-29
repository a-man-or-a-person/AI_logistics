"""Canonical Product v1 orchestration over the frozen clustering research layer."""

from __future__ import annotations

import copy
import logging
import time
from collections import Counter, OrderedDict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from backend.product_modes import (
    ModeDataQuality,
    ModeDataset,
    ModeOutcome,
    ModePreview,
    ModeSelection,
    ProductClusteringError,
    ProductModeCatalog,
    default_product_mode_catalog,
)
from backend.services.boundary_provider import BoundaryProvider
from ml.clustering.base import Clusterer, ClusterPoint, ClusterResult
from ml.clustering.bear_volume_zones import BearVolumeZoneDetector
from ml.clustering.bear_zones import BearZoneDetector
from ml.clustering.economics import relative_rate_delta, weighted_mean
from ml.clustering.geo_cost import GeoCostClusterer
from ml.clustering.geo_volume import GeoVolumeClusterer
from ml.clustering.geographic import GeographicClusterer
from ml.data.clustering_repository import ClusteringRepository
from ml.data.loader import default_csv_path, iter_records
from ml.data.locations import LocationPoint, build_location_dataset, resolve_location_routes
from ml.data.schema import LogisticsRecord
from ml.spatial.graph import SpatialGraph, SpatialGraphBuilder
from ml.spatial.projection import LocalProjection

logger = logging.getLogger(__name__)

MODES: dict[str, type[Clusterer]] = {
    "geography": GeographicClusterer,
    "geo_cost": GeoCostClusterer,
    "geo_volume": GeoVolumeClusterer,
    "bear_zones": BearZoneDetector,
    "bear_volume_zones": BearVolumeZoneDetector,
}
LEGACY_BEAR_MODES = frozenset({"bear_zones", "bear_volume_zones"})
CATALOG_MODE_IDS = frozenset(MODES)
PERIOD_TYPES = frozenset({"retro", "current", "forecast"})
PRICE_TYPES = frozenset({"spot", "tender"})
K_MIN, K_MAX, DEFAULT_K = 2, 20, 5
DEFAULT_BEAR_THRESHOLD, DEFAULT_SINGLETON_THRESHOLD = 0.35, 0.70
GEO_COST_PRESETS = ((0.80, 0.20), (0.70, 0.30), (0.60, 0.40))
GEO_VOLUME_PRESETS = GEO_COST_PRESETS
BEAR_THRESHOLD_OPTIONS = (0.20, 0.25, 0.30, 0.35, 0.40, 0.50)
RESULT_CACHE_SIZE, GRAPH_CACHE_SIZE, LOCATION_CACHE_SIZE = 64, 32, 32


def _string_list(payload: dict[str, Any], name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = payload.get(name, list(default))
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ProductClusteringError("INVALID_REQUEST", f"{name} должен быть списком строк.", 400)
    return tuple(dict.fromkeys(item.strip() for item in value))


def _number(
    value: Any, message: str, code: str = "INVALID_MODE_PARAMETERS"
) -> float:
    if isinstance(value, bool):
        raise ProductClusteringError(code, message, 400)
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ProductClusteringError(code, message, 400) from error


@dataclass(frozen=True, slots=True)
class ClusteringRequest:
    origin_fias: str
    destination_region: str
    period_types: tuple[str, ...]
    price_types: tuple[str, ...]
    vehicle_types: tuple[str, ...]
    tonnage_ids: tuple[str, ...]
    mode: str
    k_mode: str | None
    n_clusters: int | str | None
    geography_weight: float | None
    economics_weight: float | None
    volume_weight: float | None
    bear_threshold: float
    volume_threshold: float
    singleton_threshold: float
    mode_selection: ModeSelection | None = None

    @classmethod
    def from_payload(
        cls,
        payload: Any,
        *,
        product_mode_catalog: ProductModeCatalog | None = None,
    ) -> ClusteringRequest:
        if not isinstance(payload, dict):
            raise ProductClusteringError("INVALID_REQUEST", "Ожидается JSON-объект.", 400)
        origin_fias = payload.get("origin_fias")
        destination_region = payload.get("destination_region")
        if not isinstance(origin_fias, str) or not origin_fias.strip():
            raise ProductClusteringError("INVALID_REQUEST", "Не указан origin_fias.", 400)
        if not isinstance(destination_region, str) or not destination_region.strip():
            raise ProductClusteringError("INVALID_REQUEST", "Не указан destination_region.", 400)

        mode = payload.get("mode", "geography")
        if mode not in MODES:
            raise ProductClusteringError("INVALID_REQUEST", f"Неподдерживаемый mode: {mode}.", 400)
        parameters = payload.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ProductClusteringError("INVALID_REQUEST", "parameters должен быть объектом.", 400)
        allowed = {
            "bear_zones": {"bear_threshold", "singleton_threshold"},
            "bear_volume_zones": {"volume_threshold", "singleton_threshold"},
        }.get(mode)
        if allowed is not None and mode not in CATALOG_MODE_IDS:
            unknown = set(parameters) - allowed
            if unknown:
                raise ProductClusteringError(
                    "INVALID_MODE_PARAMETERS",
                    f"Неизвестные parameters: {', '.join(sorted(unknown))}.",
                    400,
                )

        k_mode: str | None = None
        n_clusters: int | str | None = None
        geography_weight: float | None = None
        economics_weight: float | None = None
        volume_weight: float | None = None
        bear_threshold = DEFAULT_BEAR_THRESHOLD
        volume_threshold = DEFAULT_BEAR_THRESHOLD
        singleton_threshold = DEFAULT_SINGLETON_THRESHOLD
        mode_selection: ModeSelection | None = None
        if mode in CATALOG_MODE_IDS:
            catalog = product_mode_catalog or default_product_mode_catalog()
            mode_selection = catalog.select(mode, parameters)
            normalized = mode_selection.as_parameters()
            k_mode = cast(str | None, normalized.get("k_mode"))
            n_clusters = cast(int | str | None, normalized.get("n_clusters"))
            geography_weight = cast(float | None, normalized.get("geography_weight"))
            economics_weight = cast(float | None, normalized.get("economics_weight"))
            volume_weight = cast(float | None, normalized.get("volume_weight"))
            bear_threshold = float(
                normalized.get("bear_threshold", DEFAULT_BEAR_THRESHOLD)
            )
            volume_threshold = float(
                normalized.get("volume_threshold", DEFAULT_BEAR_THRESHOLD)
            )
            singleton_threshold = float(
                normalized.get("singleton_threshold", DEFAULT_SINGLETON_THRESHOLD)
            )
        # Inactive pre-catalog parsing retained for the Ticket 05 rollback boundary.
        elif mode not in LEGACY_BEAR_MODES:
            k_mode = parameters.get("k_mode")
            raw_k = parameters.get("n_clusters")
            if k_mode is None:
                k_mode = "auto" if raw_k in (None, "auto") else "manual"
            if k_mode not in {"auto", "manual"}:
                raise ProductClusteringError(
                    "INVALID_MODE_PARAMETERS", "k_mode должен быть auto или manual.", 400
                )
            if k_mode == "auto":
                n_clusters = "auto"
            elif isinstance(raw_k, bool) or not isinstance(raw_k, int) or not K_MIN <= raw_k <= K_MAX:
                raise ProductClusteringError(
                    "INVALID_CLUSTER_COUNT",
                    f"n_clusters должен быть целым числом от {K_MIN} до {K_MAX}.",
                    400,
                )
            else:
                n_clusters = raw_k

        if mode == "geo_cost" and mode_selection is None:
            geography_weight = _number(
                parameters.get("geography_weight", 0.70), "geography_weight должен быть числом."
            )
            economics_weight = _number(
                parameters.get("economics_weight", 0.30), "economics_weight должен быть числом."
            )
            if not any(
                abs(geography_weight - geography) < 1e-9
                and abs(economics_weight - economics) < 1e-9
                for geography, economics in GEO_COST_PRESETS
            ):
                raise ProductClusteringError(
                    "INVALID_MODE_PARAMETERS",
                    "Допустимы веса Geography/Cost: 80/20, 70/30 или 60/40.",
                    400,
                )

        if mode == "geo_volume" and mode_selection is None:
            geography_weight = _number(
                parameters.get("geography_weight", 0.70),
                "geography_weight должен быть числом.",
            )
            volume_weight = _number(
                parameters.get("volume_weight", 0.30),
                "volume_weight должен быть числом.",
            )
            if not any(
                abs(geography_weight - geography) < 1e-9
                and abs(volume_weight - volume) < 1e-9
                for geography, volume in GEO_VOLUME_PRESETS
            ):
                raise ProductClusteringError(
                    "INVALID_MODE_PARAMETERS",
                    "Допустимы веса Geography/Volume: 80/20, 70/30 или 60/40.",
                    400,
                )

        if mode_selection is None:
            bear_threshold = _number(
                parameters.get("bear_threshold", DEFAULT_BEAR_THRESHOLD), "Порог Bear должен быть числом."
            )
            volume_threshold = _number(
                parameters.get("volume_threshold", DEFAULT_BEAR_THRESHOLD),
                "Порог объёмной зоны должен быть числом.",
            )
            singleton_threshold = _number(
                parameters.get("singleton_threshold", DEFAULT_SINGLETON_THRESHOLD),
                "Порог одиночной точки должен быть числом.",
            )
            if mode in LEGACY_BEAR_MODES and abs(singleton_threshold - DEFAULT_SINGLETON_THRESHOLD) > 1e-9:
                raise ProductClusteringError(
                    "INVALID_MODE_PARAMETERS",
                    "Порог одиночной точки фиксирован на уровне +70%.",
                    400,
                )
            if mode == "bear_zones" and not any(
                abs(bear_threshold - option) < 1e-9 for option in BEAR_THRESHOLD_OPTIONS
            ):
                raise ProductClusteringError(
                    "INVALID_MODE_PARAMETERS",
                    "Допустимые пороги Bear: +20%, +25%, +30%, +35%, +40% или +50%.",
                    400,
                )
            if mode == "bear_volume_zones" and not any(
                abs(volume_threshold - option) < 1e-9
                for option in BEAR_THRESHOLD_OPTIONS
            ):
                raise ProductClusteringError(
                    "INVALID_MODE_PARAMETERS",
                    "Допустимые пороги объёмных зон: +20%, +25%, +30%, +35%, +40% или +50%.",
                    400,
                )

        periods = _string_list(payload, "period_types", ("current",))
        prices = _string_list(payload, "price_types", ("spot",))
        vehicles = _string_list(payload, "vehicle_types", ())
        tonnages = _string_list(payload, "tonnage_ids", ())
        invalid = (set(periods) - PERIOD_TYPES) | (set(prices) - PRICE_TYPES)
        if invalid:
            raise ProductClusteringError(
                "INVALID_REQUEST", f"Неизвестные значения фильтров: {', '.join(sorted(invalid))}.", 400
            )
        if not periods or not prices:
            raise ProductClusteringError(
                "INVALID_REQUEST", "Выберите хотя бы один период и тип цены.", 400
            )
        return cls(
            origin_fias=origin_fias.strip(),
            destination_region=destination_region.strip(),
            period_types=periods,
            price_types=prices,
            vehicle_types=vehicles,
            tonnage_ids=tonnages,
            mode=mode,
            k_mode=k_mode,
            n_clusters=n_clusters,
            geography_weight=geography_weight,
            economics_weight=economics_weight,
            volume_weight=volume_weight,
            bear_threshold=bear_threshold,
            volume_threshold=volume_threshold,
            singleton_threshold=singleton_threshold,
            mode_selection=mode_selection,
        )

    def filters(self) -> dict[str, list[str]]:
        return {
            "period_types": list(self.period_types),
            "price_types": list(self.price_types),
            "vehicle_types": list(self.vehicle_types),
            "tonnage_ids": list(self.tonnage_ids),
        }

    def parameters(self) -> dict[str, Any]:
        if self.mode_selection is not None:
            return self.mode_selection.as_parameters()
        # Compatibility projection for the inactive legacy execution path.
        if self.mode == "bear_zones":
            return {
                "bear_threshold": self.bear_threshold,
                "singleton_threshold": self.singleton_threshold,
            }
        if self.mode == "bear_volume_zones":
            return {
                "volume_threshold": self.volume_threshold,
                "singleton_threshold": self.singleton_threshold,
            }
        result: dict[str, Any] = {"k_mode": self.k_mode, "n_clusters": self.n_clusters}
        if self.mode == "geo_cost":
            result.update(
                geography_weight=self.geography_weight,
                economics_weight=self.economics_weight,
            )
        if self.mode == "geo_volume":
            result.update(
                geography_weight=self.geography_weight,
                volume_weight=self.volume_weight,
            )
        return result


@dataclass(frozen=True, slots=True)
class OriginOption:
    fias_id: str
    name: str
    region: str
    trip_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "fias_id": self.fias_id,
            "name": self.name,
            "region": self.region,
            "trip_count": self.trip_count,
        }


class ClusteringService:
    """Build filtered point datasets and expose the Product v1 JSON contract."""

    def __init__(
        self,
        source_path: str | Path | None = None,
        *,
        coordinate_cache_path: str | Path = "backend/cache/coords_cache.json",
        boundary_provider: BoundaryProvider | None = None,
        clusterers: dict[str, Clusterer] | None = None,
        records_factory: Callable[[], Iterable[LogisticsRecord]] | None = None,
        dataset_builder: Callable[..., tuple[list[LocationPoint], dict[str, Any]]] = build_location_dataset,
        repository: ClusteringRepository | None = None,
        graph_builder: SpatialGraphBuilder | None = None,
        product_mode_catalog: ProductModeCatalog | None = None,
    ) -> None:
        self.source_path = Path(source_path) if source_path is not None else default_csv_path()
        self.coordinate_cache_path = Path(coordinate_cache_path)
        self.boundary_provider = boundary_provider or BoundaryProvider()
        self.clusterers = clusterers or {name: cls() for name, cls in MODES.items()}
        self._records_factory = records_factory
        self._dataset_builder = dataset_builder
        self.repository = repository or (
            None if records_factory is not None else ClusteringRepository(self.source_path)
        )
        self.graph_builder = graph_builder or SpatialGraphBuilder()
        self.product_mode_catalog = product_mode_catalog or default_product_mode_catalog(
            geography_clusterer=self.clusterers.get("geography"),
            geo_cost_clusterer=self.clusterers.get("geo_cost"),
            geo_volume_clusterer=self.clusterers.get("geo_volume"),
            bear_zones_clusterer=self.clusterers.get("bear_zones"),
            bear_volume_zones_clusterer=self.clusterers.get("bear_volume_zones"),
        )
        self._origin_catalog: list[OriginOption] | None = None
        self._destination_regions: dict[str, set[str]] = {}
        self._location_cache: OrderedDict[
            tuple[Any, ...], tuple[list[LocationPoint], dict[str, Any]]
        ] = OrderedDict()
        self._graph_cache: OrderedDict[tuple[Any, ...], SpatialGraph] = OrderedDict()
        self._result_cache: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()
        self._cache_generation: tuple[Any, ...] | None = None

    def _records(self) -> Iterable[LogisticsRecord]:
        return self._records_factory() if self._records_factory is not None else iter_records(self.source_path)

    def _source_token(self) -> tuple[Any, ...]:
        if self.repository is not None:
            source = self.repository.fingerprint().cache_token()
        else:
            resolved = self.source_path.resolve()
            stat = resolved.stat()
            source = (str(resolved), stat.st_size, stat.st_mtime_ns)
        cache = self.coordinate_cache_path.resolve()
        cache_stat = cache.stat()
        return (*source, str(cache), cache_stat.st_size, cache_stat.st_mtime_ns)

    def _refresh_cache_generation(self) -> tuple[Any, ...]:
        token = self._source_token()
        if token != self._cache_generation:
            self._location_cache.clear()
            self._graph_cache.clear()
            self._result_cache.clear()
            self._cache_generation = token
        return token

    def _load_catalog(self) -> list[OriginOption]:
        if self.repository is not None:
            return [OriginOption(**item) for item in self.repository.options()["origins"]]
        if self._origin_catalog is not None:
            return self._origin_catalog
        trips: Counter[str] = Counter()
        labels: dict[str, Counter[tuple[str, str]]] = {}
        for record in self._records():
            if not record.origin_fias:
                continue
            label = (record.origin_name or record.origin_fias, record.origin_region or "")
            labels.setdefault(record.origin_fias, Counter())[label] += 1
            trips[record.origin_fias] += max(record.trip_count or 0, 0)
            if record.destination_region:
                self._destination_regions.setdefault(record.origin_fias, set()).add(
                    record.destination_region
                )
        catalog = [
            OriginOption(fias_id, *variants.most_common(1)[0][0], trips[fias_id])
            for fias_id, variants in labels.items()
        ]
        catalog.sort(key=lambda item: (-item.trip_count, item.name.casefold(), item.fias_id))
        self._origin_catalog = catalog
        return catalog

    def origins(self, query: str = "", limit: int = 20) -> list[dict[str, Any]]:
        normalized = " ".join(query.casefold().split())
        matches = [
            item
            for item in self._load_catalog()
            if not normalized
            or normalized in f"{item.name} {item.region} {item.fias_id}".casefold()
        ]
        return [item.as_dict() for item in matches[:limit]]

    def options(
        self, origin_fias: str | None = None, destination_region: str | None = None
    ) -> dict[str, Any]:
        repository_options: dict[str, Any] = {}
        if self.repository is not None:
            if origin_fias and not self.repository.has_origin(origin_fias):
                raise ProductClusteringError(
                    "UNKNOWN_ORIGIN", "Указанная точка отправления отсутствует в Pulse.", 422
                )
            if (
                origin_fias
                and destination_region
                and not self.repository.has_destination_region(origin_fias, destination_region)
            ):
                raise ProductClusteringError(
                    "UNKNOWN_DESTINATION_REGION",
                    "Указанный регион назначения недоступен для точки отправления.",
                    422,
                )
            repository_options = self.repository.options(origin_fias, destination_region)
        else:
            repository_options = {
                "origins": [item.as_dict() for item in self._load_catalog()],
                "destination_regions": sorted(self._destination_regions.get(origin_fias or "", set())),
            }
        facets = repository_options.get("facets", {})
        return {
            "source": "pulse",
            "modes": [
                "geography",
                "geo_cost",
                "geo_volume",
                "bear_zones",
                "bear_volume_zones",
            ],
            "origins": repository_options.get("origins", []),
            "period_types": facets.get("period_types", ["retro", "current", "forecast"]),
            "price_types": facets.get("price_types", ["spot", "tender"]),
            "vehicle_types": facets.get("vehicle_types", []),
            "tonnage_ids": facets.get("tonnage_ids", []),
            "facets": facets,
            "destination_regions": repository_options.get("destination_regions", []),
            "dataset_fingerprint": repository_options.get("dataset_fingerprint"),
            "k": {"min": K_MIN, "max": K_MAX, "default": DEFAULT_K, "modes": ["auto", "manual"]},
            "geo_cost_weights": {
                "default": {"geography": 0.70, "economics": 0.30},
                "presets": [
                    {"geography": geography, "economics": economics}
                    for geography, economics in GEO_COST_PRESETS
                ],
            },
            "geo_volume_weights": {
                "default": {"geography": 0.70, "volume": 0.30},
                "presets": [
                    {"geography": geography, "volume": volume}
                    for geography, volume in GEO_VOLUME_PRESETS
                ],
            },
            "bear_thresholds": {
                "zone_default": DEFAULT_BEAR_THRESHOLD,
                "zone_options": list(BEAR_THRESHOLD_OPTIONS),
                "singleton_default": DEFAULT_SINGLETON_THRESHOLD,
                "singleton_fixed": True,
            },
            "bear_volume_thresholds": {
                "zone_default": DEFAULT_BEAR_THRESHOLD,
                "zone_options": list(BEAR_THRESHOLD_OPTIONS),
                "singleton_default": DEFAULT_SINGLETON_THRESHOLD,
                "singleton_fixed": True,
            },
            "defaults": {
                "period_types": ["current"],
                "price_types": ["spot"],
                "mode": "geography",
                "k_mode": "auto",
            },
        }

    def _validate_scope(self, request: ClusteringRequest) -> None:
        if self.repository is None:
            return
        if not self.repository.has_origin(request.origin_fias):
            raise ProductClusteringError(
                "UNKNOWN_ORIGIN", "Указанная точка отправления отсутствует в Pulse.", 422
            )
        if not self.repository.has_destination_region(
            request.origin_fias, request.destination_region
        ):
            raise ProductClusteringError(
                "UNKNOWN_DESTINATION_REGION",
                "Указанный регион назначения недоступен для точки отправления.",
                422,
            )

    @staticmethod
    def _location_cache_key(
        token: tuple[Any, ...], request: ClusteringRequest
    ) -> tuple[Any, ...]:
        return (
            token,
            request.origin_fias,
            request.destination_region,
            request.period_types,
            request.price_types,
            request.vehicle_types,
            request.tonnage_ids,
        )

    def _locations(self, request: ClusteringRequest) -> tuple[list[LocationPoint], dict[str, Any]]:
        token = self._refresh_cache_generation()
        key = self._location_cache_key(token, request)
        cached = self._location_cache.get(key)
        if cached is not None:
            self._location_cache.move_to_end(key)
            return cached
        if self.repository is not None:
            routes, route_report = self.repository.aggregate(
                origin_fias=request.origin_fias,
                destination_region=request.destination_region,
                period_types=set(request.period_types),
                price_types=set(request.price_types),
                vehicle_types=set(request.vehicle_types),
                tonnage_ids=set(request.tonnage_ids),
            )
            value = resolve_location_routes(
                routes,
                route_report,
                coordinate_cache_path=self.coordinate_cache_path,
            )
        else:
            value = self._dataset_builder(
                self.source_path,
                coordinate_cache_path=self.coordinate_cache_path,
                destination_region=request.destination_region,
                origin_fias=request.origin_fias,
                period_types=set(request.period_types),
                price_types=set(request.price_types),
                vehicle_types=set(request.vehicle_types),
                tonnage_ids=set(request.tonnage_ids),
            )
        self._location_cache[key] = value
        while len(self._location_cache) > LOCATION_CACHE_SIZE:
            self._location_cache.popitem(last=False)
        return value

    @staticmethod
    def _projection(locations: list[LocationPoint]) -> LocalProjection:
        coordinates = [
            (point.latitude, point.longitude)
            for point in locations
            if point.latitude is not None and point.longitude is not None
        ]
        if not coordinates:
            raise ProductClusteringError(
                "INSUFFICIENT_POINTS", "В выбранной выборке нет точек с координатами.", 422
            )
        return LocalProjection.from_coordinates(coordinates)

    @staticmethod
    def _ml_input(
        locations: list[LocationPoint],
        projection: LocalProjection,
        *,
        include_economics: bool,
    ) -> list[ClusterPoint]:
        points = []
        for location in locations:
            if location.latitude is None or location.longitude is None:
                continue
            x, y = projection.project(location.latitude, location.longitude)
            points.append(
                ClusterPoint(
                    id=location.id,
                    name=location.name,
                    region=location.region,
                    x=x,
                    y=y,
                    trip_count=location.trip_count,
                    weighted_price=location.weighted_price if include_economics else None,
                    weighted_rub_per_km=(
                        location.weighted_rub_per_km if include_economics else None
                    ),
                    data_quality_flags=location.data_quality_flags,
                )
            )
        return points

    def _spatial_graph(self, points: list[ClusterPoint]) -> tuple[SpatialGraph, bool]:
        token = self._refresh_cache_generation()
        key = (
            token,
            tuple((point.id, round(point.x, 6), round(point.y, 6)) for point in points),
        )
        cached = self._graph_cache.get(key)
        if cached is not None:
            self._graph_cache.move_to_end(key)
            return cached, True
        graph = self.graph_builder.build(points)
        self._graph_cache[key] = graph
        while len(self._graph_cache) > GRAPH_CACHE_SIZE:
            self._graph_cache.popitem(last=False)
        return graph, False

    @staticmethod
    def _quality(locations: list[LocationPoint], report: dict[str, Any]) -> dict[str, Any]:
        coordinates = report.get("coordinates", {})
        metadata = report.get("metadata", {})
        embedded = report.get("data_quality", {})
        resolved = [point for point in locations if point.latitude is not None]
        economic_valid = [
            point
            for point in resolved
            if point.trip_count > 0
            and point.weighted_price is not None
            and point.weighted_rub_per_km is not None
        ]
        total = len(locations)
        resolved_count = coordinates.get("resolved", len(resolved))
        unresolved_count = coordinates.get("unresolved", total - len(resolved))
        point_coverage = coordinates.get("location_coverage_pct", 0)
        trip_coverage = coordinates.get("trip_coverage_pct", 0)
        mixed_price = bool(metadata.get("mixed_price_types", False))
        mixed_vehicle = bool(metadata.get("mixed_vehicle_types", False))
        mixed_tonnage = bool(metadata.get("mixed_tonnages", False))
        return {
            "destination_points_total": total,
            "resolved_points": resolved_count,
            "unresolved_points": unresolved_count,
            "point_coverage_pct": point_coverage,
            "trip_weight_coverage_pct": trip_coverage,
            "trip_count_total": report.get("trip_count_total", 0),
            "trip_count_resolved": coordinates.get("trip_count_resolved", 0),
            "source_row_count": report.get("filtered_source_rows", 0),
            "excluded_missing_fias": embedded.get(
                "excluded_missing_fias", report.get("excluded_missing_fias_rows", 0)
            ),
            "economic_valid_points": len(economic_valid),
            "economic_unavailable_points": len(resolved) - len(economic_valid),
            "contains_forecast": bool(metadata.get("contains_forecast", False)),
            "mixed_price_segments": mixed_price,
            "mixed_vehicle_segments": mixed_vehicle,
            "mixed_tonnage_segments": mixed_tonnage,
            "locations_total": total,
            "coordinates_resolved": resolved_count,
            "coordinates_unresolved": unresolved_count,
            "location_coverage_pct": point_coverage,
            "trip_coverage_pct": trip_coverage,
            "mixed_segment_details": {
                "period_types": len(metadata.get("observed_period_types", [])) > 1,
                "price_types": mixed_price,
                "vehicle_types": mixed_vehicle,
                "tonnage_ids": mixed_tonnage,
            },
            "unresolved": list(report.get("unresolved", [])),
        }

    @staticmethod
    def _mode_quality(quality: dict[str, Any]) -> ModeDataQuality:
        return ModeDataQuality(
            contains_forecast=quality["contains_forecast"],
            mixed_economic_segments=any(
                quality[key]
                for key in (
                    "mixed_price_segments",
                    "mixed_vehicle_segments",
                    "mixed_tonnage_segments",
                )
            ),
            unresolved_points=quality["unresolved_points"],
            economic_unavailable_points=quality["economic_unavailable_points"],
        )

    def _prepare_mode_dataset(
        self,
        locations: list[LocationPoint],
        quality: dict[str, Any],
        spatial_graph: SpatialGraph | None,
        projection: LocalProjection | None = None,
    ) -> ModeDataset:
        resolved = [
            point
            for point in locations
            if point.latitude is not None and point.longitude is not None
        ]
        points = (
            self._ml_input(
                locations,
                projection or self._projection(locations),
                include_economics=True,
            )
            if resolved
            else []
        )
        return ModeDataset(tuple(points), spatial_graph, self._mode_quality(quality))

    @staticmethod
    def _legacy_warnings(mode: str, quality: dict[str, Any]) -> list[dict[str, str]]:
        warnings: list[dict[str, str]] = []
        if quality["contains_forecast"]:
            warnings.append(
                {"code": "CONTAINS_FORECAST", "message": "В анализ включены прогнозные данные Pulse."}
            )
        if mode in {"geo_cost", "bear_zones"} and any(
            quality[key]
            for key in (
                "mixed_price_segments",
                "mixed_vehicle_segments",
                "mixed_tonnage_segments",
            )
        ):
            warnings.append(
                {
                    "code": "MIXED_ECONOMIC_SEGMENTS",
                    "message": (
                        "Различия ₽/км могут быть связаны не только с территорией, "
                        "но и со смешением тарифных сегментов."
                    ),
                }
            )
        if quality["unresolved_points"]:
            warnings.append(
                {
                    "code": "COORDINATE_INCOMPLETE",
                    "message": "Часть точек не имеет координат и не может быть отображена на карте.",
                }
            )
        if mode == "geo_cost" and quality["economic_unavailable_points"]:
            warnings.append(
                {
                    "code": "ECONOMIC_UNAVAILABLE",
                    "message": (
                        "Часть точек не имеет достаточных данных для расчёта ₽/км. "
                        "Они не участвовали в экономической кластеризации."
                    ),
                }
            )
        return warnings

    @staticmethod
    def _point_json(
        location: LocationPoint,
        *,
        status: str | None = None,
        cluster_id: int | None = None,
        regional_rate: float | None = None,
        regional_mean_trip_count: float | None = None,
    ) -> dict[str, Any]:
        if location.latitude is None or location.longitude is None:
            status = "unresolved"
        elif status is None:
            status = "ordinary"
        return {
            "id": location.id,
            "fias_id": location.fias_id,
            "name": location.name,
            "region": location.region,
            "lat": location.latitude,
            "lon": location.longitude,
            "trip_count": location.trip_count,
            "weighted_price": location.weighted_price,
            "weighted_rub_per_km": location.weighted_rub_per_km,
            "regional_weighted_rub_per_km": regional_rate,
            "relative_rate_delta": relative_rate_delta(
                location.weighted_rub_per_km, regional_rate
            ),
            "regional_mean_trip_count": regional_mean_trip_count,
            "relative_volume_delta": (
                location.trip_count / regional_mean_trip_count - 1
                if regional_mean_trip_count is not None
                and regional_mean_trip_count > 0
                else None
            ),
            "cluster_id": cluster_id,
            "status": status,
            "economic_status": location.economic_status,
            "coordinate_status": location.coordinate_status,
            "coordinate_source": location.coordinate_source,
            "data_quality_flags": list(location.data_quality_flags),
        }

    @staticmethod
    def _legacy_point_json(
        location: LocationPoint,
        *,
        mode: str,
        assignments: dict[str, int] | None = None,
        cluster_types: dict[int, str] | None = None,
        outlier_ids: set[str] | None = None,
        candidate_ids: set[str] | None = None,
        regional_rate: float | None = None,
        regional_mean_trip_count: float | None = None,
    ) -> dict[str, Any]:
        cluster_id = assignments.get(location.id) if assignments else None
        economic_available = (
            location.trip_count > 0
            and location.weighted_price is not None
            and location.weighted_rub_per_km is not None
        )
        if location.latitude is None or location.longitude is None:
            status = "unresolved"
        elif mode in {"geo_cost", "bear_zones"} and not economic_available:
            status = "economic_unavailable"
        elif cluster_id is not None and cluster_id >= 0:
            status = (cluster_types or {}).get(cluster_id, "normal")
        elif location.id in (candidate_ids or set()):
            status = (
                "bear_volume_candidate"
                if mode == "bear_volume_zones"
                else "bear_candidate"
            )
        elif location.id in (outlier_ids or set()):
            status = "spatial_outlier"
        else:
            status = "ordinary"
        return ClusteringService._point_json(
            location,
            status=status,
            cluster_id=cluster_id,
            regional_rate=regional_rate,
            regional_mean_trip_count=regional_mean_trip_count,
        )

    def _origin(self, fias_id: str) -> dict[str, Any]:
        matches = self.origins(fias_id, limit=1)
        if matches and matches[0]["fias_id"] == fias_id:
            return matches[0]
        return {"fias_id": fias_id, "name": fias_id, "region": "", "trip_count": 0}

    def _analysis(
        self,
        request: ClusteringRequest,
        result: ClusterResult | None = None,
        preview: ModePreview | None = None,
    ) -> dict[str, Any]:
        return {
            "source": "pulse",
            "origin": self._origin(request.origin_fias),
            "destination_region": request.destination_region,
            "filters": request.filters(),
            "mode": request.mode,
            "algorithm": (
                (result.internal_algorithm or result.algorithm)
                if result
                else preview.algorithm
                if preview is not None
                else MODES[request.mode].algorithm
            ),
            "parameters": (
                result.parameters
                if result is not None
                else preview.selection.as_parameters()
                if preview is not None
                else request.parameters()
            ),
        }

    def preview(
        self, request: ClusteringRequest, *, request_id: str = "-"
    ) -> dict[str, Any]:
        started = time.perf_counter()
        self._validate_scope(request)
        locations, report = self._locations(request)
        quality = self._quality(locations, report)
        dataset = self._prepare_mode_dataset(locations, quality, None)
        selection = request.mode_selection or self.product_mode_catalog.select(
            request.mode, request.parameters()
        )
        evaluated = self.product_mode_catalog.evaluate(selection, dataset, "preview")
        if not isinstance(evaluated, ModePreview):
            raise TypeError("Product mode adapter did not return a preview")
        point_states = {state.point_id: state.status for state in evaluated.point_states}
        logger.info(
            (
                "clustering_preview request_id=%s mode=%s origin=%s destination=%s "
                "filters=%s source_rows=%s points=%s resolved=%s calculation_ms=%.2f"
            ),
            request_id,
            request.mode,
            request.origin_fias,
            request.destination_region,
            request.filters(),
            quality["source_row_count"],
            quality["destination_points_total"],
            quality["resolved_points"],
            (time.perf_counter() - started) * 1000,
        )
        return {
            "status": "preview",
            "analysis": self._analysis(request, preview=evaluated),
            "data_quality": quality,
            "warnings": [warning.as_dict() for warning in evaluated.warnings],
            "points": [
                self._point_json(point, status=point_states.get(point.id))
                for point in locations
            ],
        }

    def run(
        self, request: ClusteringRequest, *, request_id: str = "-"
    ) -> dict[str, Any]:
        started = time.perf_counter()
        repository_cache_hit = self.repository is None or self.repository.load_count > 0
        self._validate_scope(request)
        token = self._refresh_cache_generation()
        location_cache_hit = self._location_cache_key(token, request) in self._location_cache
        cache_key = (token, request)
        cached = self._result_cache.get(cache_key)
        if cached is not None:
            self._result_cache.move_to_end(cache_key)
            quality = cached["data_quality"]
            logger.info(
                (
                    "clustering request_id=%s mode=%s origin=%s destination=%s filters=%s "
                    "source_rows=%s points=%s resolved=%s repository_cache=%s "
                    "location_cache=%s graph_cache=not_used result_cache=hit calculation_ms=%.2f"
                ),
                request_id,
                request.mode,
                request.origin_fias,
                request.destination_region,
                request.filters(),
                quality["source_row_count"],
                quality["destination_points_total"],
                quality["resolved_points"],
                "hit" if repository_cache_hit else "miss",
                "hit" if location_cache_hit else "miss",
                (time.perf_counter() - started) * 1000,
            )
            return copy.deepcopy(cached)
        try:
            result, graph_cache_hit = self._calculate(request)
        except ProductClusteringError as error:
            logger.warning(
                "clustering request_id=%s mode=%s origin=%s destination=%s error_code=%s",
                request_id,
                request.mode,
                request.origin_fias,
                request.destination_region,
                error.code,
            )
            raise
        self._result_cache[cache_key] = copy.deepcopy(result)
        while len(self._result_cache) > RESULT_CACHE_SIZE:
            self._result_cache.popitem(last=False)
        quality = result["data_quality"]
        logger.info(
            (
                "clustering mode=%s origin=%s destination=%s routes=%s resolved=%s "
                "request_id=%s filters=%s source_rows=%s repository_cache=%s "
                "location_cache=%s result_cache=miss graph_cache=%s calculation_ms=%.2f"
            ),
            request.mode,
            request.origin_fias,
            request.destination_region,
            quality["destination_points_total"],
            quality["resolved_points"],
            request_id,
            request.filters(),
            quality["source_row_count"],
            "hit" if repository_cache_hit else "miss",
            "hit" if location_cache_hit else "miss",
            "hit" if graph_cache_hit else "miss",
            (time.perf_counter() - started) * 1000,
        )
        return result

    def _calculate(self, request: ClusteringRequest) -> tuple[dict[str, Any], bool]:
        locations, report = self._locations(request)
        if not locations:
            raise ProductClusteringError("NO_DATA", "По выбранным фильтрам данных нет.", 422)
        quality = self._quality(locations, report)
        projection = self._projection(locations)
        spatial_points = self._ml_input(locations, projection, include_economics=False)
        full_graph, graph_cache_hit = self._spatial_graph(spatial_points)
        dataset = self._prepare_mode_dataset(
            locations, quality, full_graph, projection
        )
        selection = request.mode_selection or self.product_mode_catalog.select(
            request.mode, request.parameters()
        )
        evaluated = self.product_mode_catalog.evaluate(selection, dataset, "run")
        if not isinstance(evaluated, ModeOutcome):
            raise TypeError("Product mode adapter did not return an outcome")
        return (
            self._result_json(request, locations, report, evaluated),
            graph_cache_hit,
        )

    def _calculate_legacy(self, request: ClusteringRequest) -> tuple[dict[str, Any], bool]:
        """Inactive pre-Ticket-05 path retained as the rollback boundary."""
        locations, report = self._locations(request)
        if not locations:
            raise ProductClusteringError("NO_DATA", "По выбранным фильтрам данных нет.", 422)
        projection = self._projection(locations)
        geography_points = self._ml_input(locations, projection, include_economics=False)
        full_graph, graph_cache_hit = self._spatial_graph(geography_points)

        if request.mode == "geo_volume":
            points = geography_points
            graph = full_graph
        elif request.mode == "bear_volume_zones":
            points = [point for point in geography_points if point.trip_count > 0]
            if not points:
                raise ProductClusteringError(
                    "INSUFFICIENT_POINTS",
                    "Нет точек с положительным объёмом перевозок для объёмных зон.",
                    422,
                )
            graph = full_graph.induced_subgraph({point.id for point in points})
        else:
            economic_points = self._ml_input(locations, projection, include_economics=True)
            if request.mode == "geo_cost":
                points = [
                    point
                    for point in economic_points
                    if point.trip_count > 0
                    and point.weighted_price is not None
                    and point.weighted_rub_per_km is not None
                ]
                if len(points) < 2:
                    raise ProductClusteringError(
                        "INSUFFICIENT_ECONOMICS",
                        "Недостаточно точек с валидными price, route_length и ₽/км.",
                        422,
                    )
            else:
                points = [
                    point
                    for point in economic_points
                    if point.trip_count > 0 and point.weighted_rub_per_km is not None
                ]
                if not points:
                    raise ProductClusteringError(
                        "INSUFFICIENT_ECONOMICS", "Нет валидной экономики для Bear Zones.", 422
                    )
            graph = full_graph.induced_subgraph({point.id for point in points})

        if request.mode not in LEGACY_BEAR_MODES and isinstance(request.n_clusters, int):
            clusterable = len(points) - len(graph.isolated_point_ids)
            components = sum(len(component) > 1 for component in graph.connected_components)
            if request.n_clusters > clusterable or request.n_clusters < components:
                raise ProductClusteringError(
                    "INVALID_CLUSTER_COUNT",
                    (
                        f"K={request.n_clusters} невозможно для {clusterable} связанных точек "
                        f"в {components} компонентах."
                    ),
                    422,
                )

        parameters: dict[str, Any] = {"spatial_graph": graph}
        if request.mode == "bear_zones":
            parameters.update(
                bear_threshold=request.bear_threshold,
                singleton_threshold=request.singleton_threshold,
            )
        elif request.mode == "bear_volume_zones":
            parameters.update(
                volume_threshold=request.volume_threshold,
                singleton_threshold=request.singleton_threshold,
            )
        else:
            parameters.update(n_clusters=request.n_clusters, k_min=K_MIN, k_max=K_MAX)
            if request.mode == "geo_cost":
                parameters.update(
                    geography_weight=request.geography_weight,
                    economics_weight=request.economics_weight,
                )
            elif request.mode == "geo_volume":
                parameters.update(
                    geography_weight=request.geography_weight,
                    volume_weight=request.volume_weight,
                )
        try:
            result = self.clusterers[request.mode].fit(points, parameters)
        except AssertionError as error:
            raise ProductClusteringError("CONNECTIVITY_VIOLATION", str(error), 422) from error
        except ValueError as error:
            if isinstance(request.n_clusters, int):
                code = "INVALID_CLUSTER_COUNT"
            elif request.mode in {"geo_cost", "bear_zones"}:
                code = "INSUFFICIENT_ECONOMICS"
            else:
                code = "INSUFFICIENT_POINTS"
            raise ProductClusteringError(code, str(error), 422) from error
        status = (
            "no_bears"
            if request.mode in LEGACY_BEAR_MODES and not result.clusters
            else "success"
        )
        return self._legacy_result_json(
            request, locations, report, result, status
        ), graph_cache_hit

    def compare(self, payload: Any, *, request_id: str = "-") -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ProductClusteringError("INVALID_REQUEST", "Ожидается JSON-объект.", 400)
        dataset = {
            key: payload.get(key)
            for key in (
                "origin_fias",
                "destination_region",
                "period_types",
                "price_types",
                "vehicle_types",
                "tonnage_ids",
            )
            if key in payload
        }
        requests = {
            capability.mode_id: dict(capability.comparison_parameters)
            for capability in self.product_mode_catalog.manifest()
            if capability.comparison_supported
        }
        results = {
            mode: self.run(
                ClusteringRequest.from_payload(
                    {**dataset, "mode": mode, "parameters": parameters},
                    product_mode_catalog=self.product_mode_catalog,
                ),
                request_id=request_id,
            )
            for mode, parameters in requests.items()
        }
        return {
            "status": "success",
            "winner": None,
            "dataset": dataset,
            "results": results,
        }

    def _result_json(
        self,
        request: ClusteringRequest,
        locations: list[LocationPoint],
        report: dict[str, Any],
        outcome: ModeOutcome,
    ) -> dict[str, Any]:
        quality = self._quality(locations, report)
        result = outcome.result
        location_by_id = {point.id: point for point in locations}
        regional_rate = result.regional_weighted_rub_per_km
        regional_mean_trip_count = result.metrics.get("regional_mean_trip_count")
        point_states = {state.point_id: state.status for state in outcome.point_states}
        metrics = dict(result.metrics)
        graph_metric_names = {
            "node_count",
            "edge_count",
            "candidate_edge_count",
            "pruned_edge_count",
            "graph_component_count",
            "isolated_point_count",
            "connectivity_violations",
            "adaptive_edge_threshold_m",
        }
        regional_price = weighted_mean(
            (point.weighted_price, point.trip_count) for point in locations
        )
        return {
            "status": outcome.status,
            "analysis": self._analysis(request, result),
            "contains_forecast": quality["contains_forecast"],
            "data_quality": quality,
            "warnings": [warning.as_dict() for warning in outcome.warnings],
            "metrics": metrics,
            "graph_metrics": {
                key: value for key, value in metrics.items() if key in graph_metric_names
            },
            "regional_stats": {
                "destination_points": quality["destination_points_total"],
                "trip_count": quality["trip_count_total"],
            },
            "regional_economics": {
                "weighted_price": regional_price,
                "weighted_rub_per_km": regional_rate,
            },
            "regional_volume": {
                "trip_count": quality["trip_count_total"],
                "mean_trip_count_per_point": regional_mean_trip_count,
            },
            "regional_weighted_rub_per_km": regional_rate,
            "points": [
                self._point_json(
                    point,
                    status=point_states.get(point.id),
                    cluster_id=result.point_assignments.get(point.id),
                    regional_rate=regional_rate,
                    regional_mean_trip_count=regional_mean_trip_count,
                )
                for point in locations
            ],
            "clusters": [
                self._cluster_json(cluster, location_by_id) for cluster in result.clusters
            ],
            "outliers": list(result.outliers),
        }

    def _legacy_result_json(
        self,
        request: ClusteringRequest,
        locations: list[LocationPoint],
        report: dict[str, Any],
        result: ClusterResult,
        status: str,
    ) -> dict[str, Any]:
        quality = self._quality(locations, report)
        cluster_types = {cluster.cluster_id: cluster.cluster_type for cluster in result.clusters}
        outlier_ids = {item["point_id"] for item in result.outliers}
        location_by_id = {point.id: point for point in locations}
        regional_rate = result.regional_weighted_rub_per_km
        regional_mean_trip_count = result.metrics.get("regional_mean_trip_count")
        candidate_ids: set[str] = set()
        if request.mode == "bear_zones" and regional_rate is not None:
            candidate_ids = {
                point.id
                for point in locations
                if point.latitude is not None
                and relative_rate_delta(point.weighted_rub_per_km, regional_rate) is not None
                and relative_rate_delta(point.weighted_rub_per_km, regional_rate)
                >= request.bear_threshold
            }
        elif (
            request.mode == "bear_volume_zones"
            and regional_mean_trip_count is not None
            and regional_mean_trip_count > 0
        ):
            candidate_ids = {
                point.id
                for point in locations
                if point.latitude is not None
                and point.trip_count / regional_mean_trip_count - 1
                >= request.volume_threshold
            }
        metrics = dict(result.metrics)
        graph_metric_names = {
            "node_count",
            "edge_count",
            "candidate_edge_count",
            "pruned_edge_count",
            "graph_component_count",
            "isolated_point_count",
            "connectivity_violations",
            "adaptive_edge_threshold_m",
        }
        regional_price = weighted_mean(
            (point.weighted_price, point.trip_count) for point in locations
        )
        return {
            "status": status,
            "analysis": self._analysis(request, result),
            "contains_forecast": quality["contains_forecast"],
            "data_quality": quality,
            "warnings": self._legacy_warnings(request.mode, quality),
            "metrics": metrics,
            "graph_metrics": {
                key: value for key, value in metrics.items() if key in graph_metric_names
            },
            "regional_stats": {
                "destination_points": quality["destination_points_total"],
                "trip_count": quality["trip_count_total"],
            },
            "regional_economics": {
                "weighted_price": regional_price,
                "weighted_rub_per_km": regional_rate,
            },
            "regional_volume": {
                "trip_count": quality["trip_count_total"],
                "mean_trip_count_per_point": regional_mean_trip_count,
            },
            "regional_weighted_rub_per_km": regional_rate,
            "points": [
                self._legacy_point_json(
                    point,
                    mode=request.mode,
                    assignments=result.point_assignments,
                    cluster_types=cluster_types,
                    outlier_ids=outlier_ids,
                    candidate_ids=candidate_ids,
                    regional_rate=regional_rate,
                    regional_mean_trip_count=regional_mean_trip_count,
                )
                for point in locations
            ],
            "clusters": [
                self._cluster_json(cluster, location_by_id) for cluster in result.clusters
            ],
            "outliers": list(result.outliers),
        }

    @staticmethod
    def _cluster_json(cluster: Any, locations: dict[str, LocationPoint]) -> dict[str, Any]:
        medoid = locations.get(cluster.medoid_point_id)
        members = [locations[point_id] for point_id in cluster.point_ids if point_id in locations]
        weighted_price = weighted_mean((point.weighted_price, point.trip_count) for point in members)
        weighted_rub_per_km = weighted_mean(
            (point.weighted_rub_per_km, point.trip_count) for point in members
        )
        representative = {
            "type": "medoid",
            "point_id": cluster.medoid_point_id,
            "name": medoid.name if medoid else cluster.medoid_point_id,
            "lat": medoid.latitude if medoid else None,
            "lon": medoid.longitude if medoid else None,
        }
        return {
            "cluster_id": cluster.cluster_id,
            "cluster_type": cluster.cluster_type,
            "point_count": cluster.point_count,
            "trip_count": cluster.trip_count,
            "trip_share": cluster.trip_share,
            "point_ids": list(cluster.point_ids),
            "weighted_price": weighted_price,
            "weighted_rub_per_km": weighted_rub_per_km,
            "regional_weighted_rub_per_km": cluster.regional_weighted_rub_per_km,
            "relative_rate_delta": cluster.relative_rate_delta,
            "mean_trip_count": cluster.mean_trip_count,
            "regional_mean_trip_count": cluster.regional_mean_trip_count,
            "relative_volume_delta": cluster.relative_volume_delta,
            "centroid": {"x": cluster.centroid[0], "y": cluster.centroid[1]},
            "medoid": {
                **representative,
                "x": cluster.medoid[0],
                "y": cluster.medoid[1],
            },
            "medoid_point_id": cluster.medoid_point_id,
            "representative": representative,
            "mean_radius_km": cluster.mean_radius_km,
            "p95_radius_km": cluster.p95_radius_km,
            "max_radius_km": cluster.max_radius_km,
            "connected": cluster.connected,
        }
