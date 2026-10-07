"""Canonical Product v1 orchestration over the frozen clustering research layer."""

from __future__ import annotations

import copy
import hashlib
import logging
import statistics
import time
from collections import Counter, OrderedDict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
from ml.clustering.base import ClusterPoint, ClusterResult
from ml.clustering.economics import relative_rate_delta, weighted_mean
from ml.data.clustering_repository import ClusteringRepository
from ml.data.loader import default_csv_path, iter_records
from ml.data.locations import LocationPoint, build_location_dataset, resolve_location_routes
from ml.data.schema import LogisticsRecord
from ml.spatial.graph import SpatialGraph, SpatialGraphBuilder
from ml.spatial.projection import LocalProjection

logger = logging.getLogger(__name__)

PERIOD_TYPES = frozenset({"retro", "current", "forecast"})
PRICE_TYPES = frozenset({"spot", "tender"})
RESULT_CACHE_SIZE, GRAPH_CACHE_SIZE, LOCATION_CACHE_SIZE = 64, 32, 32


def _string_list(payload: dict[str, Any], name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = payload.get(name, list(default))
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ProductClusteringError("INVALID_REQUEST", f"{name} должен быть списком строк.", 400)
    return tuple(sorted({item.strip() for item in value}))


@dataclass(frozen=True, slots=True)
class ClusteringRequest:
    origin_fias: str
    destination_region: str
    period_types: tuple[str, ...]
    price_types: tuple[str, ...]
    vehicle_types: tuple[str, ...]
    tonnage_ids: tuple[str, ...]
    selection: ModeSelection

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

        catalog = product_mode_catalog or default_product_mode_catalog()
        mode = payload.get("mode", catalog.mode_ids[0])
        if mode not in catalog.mode_ids:
            raise ProductClusteringError("INVALID_REQUEST", f"Неподдерживаемый mode: {mode}.", 400)
        parameters = payload.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ProductClusteringError("INVALID_REQUEST", "parameters должен быть объектом.", 400)
        selection = catalog.select(mode, parameters)

        periods = _string_list(payload, "period_types", ("current",))
        prices = _string_list(payload, "price_types", ("spot",))
        vehicles = _string_list(payload, "vehicle_types", ())
        tonnages = _string_list(payload, "tonnage_ids", ())
        invalid = (set(periods) - PERIOD_TYPES) | (set(prices) - PRICE_TYPES)
        if invalid:
            raise ProductClusteringError(
                "INVALID_REQUEST",
                f"Неизвестные значения фильтров: {', '.join(sorted(invalid))}.",
                400,
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
            selection=selection,
        )

    @property
    def mode(self) -> str:
        return self.selection.mode_id

    def filters(self) -> dict[str, list[str]]:
        return {
            "period_types": list(self.period_types),
            "price_types": list(self.price_types),
            "vehicle_types": list(self.vehicle_types),
            "tonnage_ids": list(self.tonnage_ids),
        }

    def parameters(self) -> dict[str, Any]:
        return self.selection.as_parameters()


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
        records_factory: Callable[[], Iterable[LogisticsRecord]] | None = None,
        dataset_builder: Callable[
            ..., tuple[list[LocationPoint], dict[str, Any]]
        ] = build_location_dataset,
        repository: ClusteringRepository | None = None,
        graph_builder: SpatialGraphBuilder | None = None,
        product_mode_catalog: ProductModeCatalog | None = None,
    ) -> None:
        self.source_path = Path(source_path) if source_path is not None else default_csv_path()
        self.coordinate_cache_path = Path(coordinate_cache_path)
        self.boundary_provider = boundary_provider or BoundaryProvider()
        self._records_factory = records_factory
        self._dataset_builder = dataset_builder
        self.repository = repository or (
            None if records_factory is not None else ClusteringRepository(self.source_path)
        )
        self.graph_builder = graph_builder or SpatialGraphBuilder()
        self.product_mode_catalog = product_mode_catalog or default_product_mode_catalog()
        self._origin_catalog: list[OriginOption] | None = None
        self._destination_regions: dict[str, set[str]] = {}
        self._location_cache: OrderedDict[
            tuple[Any, ...], tuple[list[LocationPoint], dict[str, Any]]
        ] = OrderedDict()
        self._graph_cache: OrderedDict[tuple[Any, ...], SpatialGraph] = OrderedDict()
        self._result_cache: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()
        self._cache_generation: tuple[Any, ...] | None = None

    def _records(self) -> Iterable[LogisticsRecord]:
        return (
            self._records_factory()
            if self._records_factory is not None
            else iter_records(self.source_path)
        )

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
                "destination_regions": sorted(
                    self._destination_regions.get(origin_fias or "", set())
                ),
            }
        facets = repository_options.get("facets", {})
        mode_capabilities = self.product_mode_catalog.manifest()
        capability_by_id = {capability.mode_id: capability for capability in mode_capabilities}

        def mode_parameter(mode_id: str, name: str):
            return next(
                parameter
                for parameter in capability_by_id[mode_id].parameters
                if parameter.name == name
            )

        cluster_count = mode_parameter("geography", "n_clusters")
        k_mode = mode_parameter("geography", "k_mode")
        cost_defaults = dict(capability_by_id["geo_cost"].default_parameters)
        volume_defaults = dict(capability_by_id["geo_volume"].default_parameters)
        bear_threshold = mode_parameter("bear_zones", "bear_threshold")
        bear_singleton = mode_parameter("bear_zones", "singleton_threshold")
        volume_threshold = mode_parameter("bear_volume_zones", "volume_threshold")
        volume_singleton = mode_parameter("bear_volume_zones", "singleton_threshold")
        return {
            "source": "pulse",
            "modes": [capability.mode_id for capability in mode_capabilities],
            "mode_capabilities": [capability.as_dict() for capability in mode_capabilities],
            "origins": repository_options.get("origins", []),
            "period_types": facets.get("period_types", ["retro", "current", "forecast"]),
            "price_types": facets.get("price_types", ["spot", "tender"]),
            "vehicle_types": facets.get("vehicle_types", []),
            "tonnage_ids": facets.get("tonnage_ids", []),
            "facets": facets,
            "destination_regions": repository_options.get("destination_regions", []),
            "dataset_fingerprint": repository_options.get("dataset_fingerprint"),
            "k": {
                "min": cluster_count.minimum,
                "max": cluster_count.maximum,
                "default": cluster_count.manual_default,
                "modes": list(k_mode.choices),
            },
            "geo_cost_weights": {
                "default": {
                    "geography": cost_defaults["geography_weight"],
                    "economics": cost_defaults["economics_weight"],
                },
                "presets": [
                    {
                        "geography": dict(preset)["geography_weight"],
                        "economics": dict(preset)["economics_weight"],
                    }
                    for preset in capability_by_id["geo_cost"].presets
                ],
            },
            "geo_volume_weights": {
                "default": {
                    "geography": volume_defaults["geography_weight"],
                    "volume": volume_defaults["volume_weight"],
                },
                "presets": [
                    {
                        "geography": dict(preset)["geography_weight"],
                        "volume": dict(preset)["volume_weight"],
                    }
                    for preset in capability_by_id["geo_volume"].presets
                ],
            },
            "bear_thresholds": {
                "zone_default": bear_threshold.default,
                "zone_options": list(bear_threshold.choices),
                "singleton_default": bear_singleton.default,
                "singleton_fixed": bear_singleton.fixed,
            },
            "bear_volume_thresholds": {
                "zone_default": volume_threshold.default,
                "zone_options": list(volume_threshold.choices),
                "singleton_default": volume_singleton.default,
                "singleton_fixed": volume_singleton.fixed,
            },
            "defaults": {
                "period_types": ["current"],
                "price_types": ["spot"],
                "mode": mode_capabilities[0].mode_id,
                "k_mode": k_mode.default,
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
    def _location_cache_key(token: tuple[Any, ...], request: ClusteringRequest) -> tuple[Any, ...]:
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
    def _point_json(
        location: LocationPoint,
        *,
        status: str | None = None,
        cluster_id: int | None = None,
        regional_rate: float | None = None,
        regional_mean_trip_count: float | None = None,
        include_table_analytics: bool = False,
    ) -> dict[str, Any]:
        if location.latitude is None or location.longitude is None:
            status = "unresolved"
        elif status is None:
            status = "ordinary"
        point = {
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
            "relative_rate_delta": relative_rate_delta(location.weighted_rub_per_km, regional_rate),
            "regional_mean_trip_count": regional_mean_trip_count,
            "relative_volume_delta": (
                location.trip_count / regional_mean_trip_count - 1
                if regional_mean_trip_count is not None and regional_mean_trip_count > 0
                else None
            ),
            "cluster_id": cluster_id,
            "status": status,
            "economic_status": location.economic_status,
            "coordinate_status": location.coordinate_status,
            "coordinate_source": location.coordinate_source,
            "data_quality_flags": list(location.data_quality_flags),
        }
        if include_table_analytics:
            point.update(
                {
                    "weighted_route_length": location.weighted_route_length,
                    "valid_route_length_trip_count": location.valid_route_length_trip_count,
                    "valid_price_trip_count": location.valid_price_trip_count,
                    "valid_rub_per_km_trip_count": location.valid_rub_per_km_trip_count,
                    "active_period_count": location.active_period_count,
                    "period_types": list(location.period_types),
                }
            )
        return point

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
        if result is not None:
            algorithm = result.internal_algorithm or result.algorithm
            parameters = result.parameters
        elif preview is not None:
            algorithm = preview.algorithm
            parameters = preview.selection.as_parameters()
        else:
            raise ValueError("Product analysis requires a mode result or preview")
        return {
            "source": "pulse",
            "origin": self._origin(request.origin_fias),
            "destination_region": request.destination_region,
            "filters": request.filters(),
            "mode": request.mode,
            "algorithm": algorithm,
            "parameters": parameters,
        }

    def preview(self, request: ClusteringRequest, *, request_id: str = "-") -> dict[str, Any]:
        started = time.perf_counter()
        self._validate_scope(request)
        locations, report = self._locations(request)
        quality = self._quality(locations, report)
        dataset = self._prepare_mode_dataset(locations, quality, None)
        evaluated = self.product_mode_catalog.evaluate(request.selection, dataset, "preview")
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
                self._point_json(point, status=point_states.get(point.id)) for point in locations
            ],
        }

    def run(self, request: ClusteringRequest, *, request_id: str = "-") -> dict[str, Any]:
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
        dataset = self._prepare_mode_dataset(locations, quality, full_graph, projection)
        evaluated = self.product_mode_catalog.evaluate(request.selection, dataset, "run")
        if not isinstance(evaluated, ModeOutcome):
            raise TypeError("Product mode adapter did not return an outcome")
        return (
            self._result_json(request, locations, report, evaluated),
            graph_cache_hit,
        )

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
        table_supported = next(
            capability.result_kind == "partition"
            for capability in self.product_mode_catalog.manifest()
            if capability.mode_id == request.mode
        )
        return {
            "status": outcome.status,
            "data_snapshot": hashlib.sha256(repr(self._cache_generation).encode()).hexdigest(),
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
                    include_table_analytics=True,
                )
                for point in locations
            ],
            "clusters": [
                self._cluster_json(cluster, location_by_id) for cluster in result.clusters
            ],
            "cluster_table": self._cluster_table(
                result.clusters,
                location_by_id,
                request.period_types,
                supported=table_supported,
            ),
            "outliers": list(result.outliers),
        }

    @staticmethod
    def _cluster_table(
        clusters: tuple[Any, ...],
        locations: dict[str, LocationPoint],
        period_types: tuple[str, ...],
        *,
        supported: bool,
    ) -> dict[str, Any]:
        if not supported:
            return {"supported": False}

        def coverage(
            members: list[LocationPoint],
            value_name: str,
            weight_name: str,
            total_trip_count: int,
        ) -> dict[str, int]:
            return {
                "valid_points": sum(getattr(point, value_name) is not None for point in members),
                "total_points": len(members),
                "valid_trip_count": sum(getattr(point, weight_name) for point in members),
                "total_trip_count": total_trip_count,
            }

        rows = []
        all_cluster_trips = sum(cluster.trip_count for cluster in clusters)
        for cluster in clusters:
            members = [locations[point_id] for point_id in cluster.point_ids]
            prices = [point.weighted_price for point in members if point.weighted_price is not None]
            rates = [
                point.weighted_rub_per_km
                for point in members
                if point.weighted_rub_per_km is not None
            ]
            total_trips = sum(point.trip_count for point in members)
            price_coverage = coverage(
                members, "weighted_price", "valid_price_trip_count", total_trips
            )
            rubkm_coverage = coverage(
                members,
                "weighted_rub_per_km",
                "valid_rub_per_km_trip_count",
                total_trips,
            )
            rows.append(
                {
                    "cluster_id": cluster.cluster_id,
                    "point_count": len(members),
                    "trip_count": total_trips,
                    "trip_share": total_trips / all_cluster_trips if all_cluster_trips else None,
                    "weighted_route_length": weighted_mean(
                        (
                            point.weighted_route_length,
                            point.valid_route_length_trip_count,
                        )
                        for point in members
                    ),
                    "price": {
                        "min": min(prices) if prices else None,
                        "median": statistics.median(prices) if prices else None,
                        "weighted": weighted_mean(
                            (point.weighted_price, point.valid_price_trip_count)
                            for point in members
                        ),
                        "max": max(prices) if prices else None,
                    },
                    "rub_per_km": {
                        "min": min(rates) if rates else None,
                        "median": statistics.median(rates) if rates else None,
                        "weighted": weighted_mean(
                            (
                                point.weighted_rub_per_km,
                                point.valid_rub_per_km_trip_count,
                            )
                            for point in members
                        ),
                        "max": max(rates) if rates else None,
                    },
                    "coverage": {
                        "route_length": coverage(
                            members,
                            "weighted_route_length",
                            "valid_route_length_trip_count",
                            total_trips,
                        ),
                        "price": price_coverage,
                        "rub_per_km": rubkm_coverage,
                    },
                    "economic_coverage": {
                        **rubkm_coverage,
                        "valid_points": sum(
                            point.weighted_price is not None
                            and point.weighted_rub_per_km is not None
                            for point in members
                        ),
                    },
                    "point_ids": list(cluster.point_ids),
                }
            )
        rows.sort(key=lambda row: (-row["trip_count"], row["cluster_id"]))
        return {
            "supported": True,
            "period_types": list(period_types),
            "methodology": {
                "version": "product_cluster_table_v1",
                "distributions": "unweighted_destination_points",
                "weighted_values": "metric_valid_trip_count",
            },
            "rows": rows,
        }

    @staticmethod
    def _cluster_json(cluster: Any, locations: dict[str, LocationPoint]) -> dict[str, Any]:
        medoid = locations.get(cluster.medoid_point_id)
        members = [locations[point_id] for point_id in cluster.point_ids if point_id in locations]
        weighted_price = weighted_mean(
            (point.weighted_price, point.trip_count) for point in members
        )
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
