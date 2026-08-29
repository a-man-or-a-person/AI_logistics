"""Canonical Product MVP orchestration over the research ML pipeline."""

from __future__ import annotations

from collections import Counter, OrderedDict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.services.boundary_provider import BoundaryProvider
from ml.clustering.base import Clusterer, ClusterPoint
from ml.clustering.kmeans import KMeansClusterer
from ml.data.loader import default_csv_path, iter_records
from ml.data.locations import LocationPoint, build_location_dataset
from ml.data.schema import LogisticsRecord
from ml.spatial.projection import LocalProjection
from ml.spatial.territorialize import territorialize

ALGORITHMS = {"kmeans": KMeansClusterer}
PERIOD_TYPES = frozenset({"retro", "current", "forecast"})
PRICE_TYPES = frozenset({"spot", "tender"})
WEIGHT_MODES = frozenset({"none", "trip_count"})


class ProductClusteringError(ValueError):
    def __init__(self, code: str, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


def _string_list(payload: dict[str, Any], name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = payload.get(name, list(default))
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ProductClusteringError(
            "INVALID_REQUEST", f"{name} должен быть списком строк.", 400
        )
    return tuple(dict.fromkeys(item.strip() for item in value))


@dataclass(frozen=True, slots=True)
class ClusteringRequest:
    origin_fias: str
    destination_region: str
    period_types: tuple[str, ...]
    price_types: tuple[str, ...]
    algorithm: str
    n_clusters: int
    weight_mode: str

    @classmethod
    def from_payload(cls, payload: Any) -> ClusteringRequest:
        if not isinstance(payload, dict):
            raise ProductClusteringError("INVALID_REQUEST", "Ожидается JSON-объект.", 400)
        origin_fias = payload.get("origin_fias")
        destination_region = payload.get("destination_region")
        algorithm = payload.get("algorithm", "kmeans")
        parameters = payload.get("parameters", {})
        if not isinstance(origin_fias, str) or not origin_fias.strip():
            raise ProductClusteringError("INVALID_REQUEST", "Не указан origin_fias.", 400)
        if not isinstance(destination_region, str) or not destination_region.strip():
            raise ProductClusteringError(
                "INVALID_REQUEST", "Не указан destination_region.", 400
            )
        if algorithm not in ALGORITHMS:
            raise ProductClusteringError(
                "INVALID_REQUEST", f"Неподдерживаемый algorithm: {algorithm}.", 400
            )
        if not isinstance(parameters, dict):
            raise ProductClusteringError(
                "INVALID_REQUEST", "parameters должен быть объектом.", 400
            )
        unknown_parameters = set(parameters) - {"n_clusters", "weight_mode"}
        if unknown_parameters:
            raise ProductClusteringError(
                "INVALID_REQUEST",
                f"Неизвестные parameters: {', '.join(sorted(unknown_parameters))}.",
                400,
            )
        n_clusters = parameters.get("n_clusters")
        if isinstance(n_clusters, bool) or not isinstance(n_clusters, int) or not 2 <= n_clusters <= 10:
            raise ProductClusteringError(
                "INVALID_REQUEST", "n_clusters должен быть целым числом от 2 до 10.", 400
            )
        weight_mode = parameters.get("weight_mode", "none")
        if weight_mode not in WEIGHT_MODES:
            raise ProductClusteringError(
                "INVALID_REQUEST", "weight_mode должен быть none или trip_count.", 400
            )
        period_types = _string_list(payload, "period_types", ("current",))
        price_types = _string_list(payload, "price_types", ("spot",))
        invalid_periods = set(period_types) - PERIOD_TYPES
        invalid_prices = set(price_types) - PRICE_TYPES
        if invalid_periods:
            raise ProductClusteringError(
                "INVALID_REQUEST",
                f"Неизвестные period_types: {', '.join(sorted(invalid_periods))}.",
                400,
            )
        if invalid_prices:
            raise ProductClusteringError(
                "INVALID_REQUEST",
                f"Неизвестные price_types: {', '.join(sorted(invalid_prices))}.",
                400,
            )
        if not period_types or not price_types:
            raise ProductClusteringError(
                "INVALID_REQUEST", "Выберите хотя бы один период и тип цены.", 400
            )
        return cls(
            origin_fias=origin_fias.strip(),
            destination_region=destination_region.strip(),
            period_types=period_types,
            price_types=price_types,
            algorithm=algorithm,
            n_clusters=n_clusters,
            weight_mode=weight_mode,
        )

    def filters(self) -> dict[str, list[str]]:
        return {
            "period_types": list(self.period_types),
            "price_types": list(self.price_types),
        }

    def parameters(self) -> dict[str, Any]:
        return {"n_clusters": self.n_clusters, "weight_mode": self.weight_mode}


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
    """Build datasets, call registered Clusterers, and shape product JSON."""

    def __init__(
        self,
        source_path: str | Path | None = None,
        *,
        coordinate_cache_path: str | Path = "backend/cache/coords_cache.json",
        boundary_provider: BoundaryProvider | None = None,
        clusterers: dict[str, Clusterer] | None = None,
        records_factory: Callable[[], Iterable[LogisticsRecord]] | None = None,
        dataset_builder: Callable[..., tuple[list[LocationPoint], dict[str, Any]]] = build_location_dataset,
    ) -> None:
        self.source_path = Path(source_path) if source_path is not None else default_csv_path()
        self.coordinate_cache_path = Path(coordinate_cache_path)
        self.boundary_provider = boundary_provider or BoundaryProvider()
        self.clusterers = clusterers or {
            name: clusterer_type() for name, clusterer_type in ALGORITHMS.items()
        }
        self._records_factory = records_factory
        self._dataset_builder = dataset_builder
        self._origin_catalog: list[OriginOption] | None = None
        self._destination_regions: dict[str, set[str]] = {}
        self._location_cache: OrderedDict[
            tuple[Any, ...], tuple[list[LocationPoint], dict[str, Any]]
        ] = OrderedDict()

    def _records(self) -> Iterable[LogisticsRecord]:
        if self._records_factory is not None:
            return self._records_factory()
        return iter_records(self.source_path)

    def _load_catalog(self) -> list[OriginOption]:
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
        catalog: list[OriginOption] = []
        for fias_id, variants in labels.items():
            name, region = variants.most_common(1)[0][0]
            catalog.append(OriginOption(fias_id, name, region, trips[fias_id]))
        catalog.sort(key=lambda item: (-item.trip_count, item.name.casefold(), item.fias_id))
        self._origin_catalog = catalog
        return catalog

    def origins(self, query: str = "", limit: int = 20) -> list[dict[str, Any]]:
        normalized_query = " ".join(query.casefold().split())
        result = [
            item
            for item in self._load_catalog()
            if not normalized_query
            or normalized_query
            in f"{item.name} {item.region} {item.fias_id}".casefold()
        ]
        return [item.as_dict() for item in result[:limit]]

    def destination_regions(self, origin_fias: str) -> list[str]:
        self._load_catalog()
        return sorted(self._destination_regions.get(origin_fias, set()))

    def options(self, origin_fias: str | None = None) -> dict[str, Any]:
        return {
            "source": "pulse",
            "algorithms": ["kmeans"],
            "weight_modes": ["none", "trip_count"],
            "period_types": ["retro", "current", "forecast"],
            "price_types": ["spot", "tender"],
            "destination_regions": self.destination_regions(origin_fias) if origin_fias else [],
        }

    def _locations(self, request: ClusteringRequest) -> tuple[list[LocationPoint], dict[str, Any]]:
        source_stat = self.source_path.stat()
        cache_stat = self.coordinate_cache_path.stat()
        key = (
            str(self.source_path.resolve()),
            source_stat.st_size,
            source_stat.st_mtime_ns,
            str(self.coordinate_cache_path.resolve()),
            cache_stat.st_size,
            cache_stat.st_mtime_ns,
            request.origin_fias,
            request.destination_region,
            request.period_types,
            request.price_types,
        )
        cached = self._location_cache.get(key)
        if cached is not None:
            self._location_cache.move_to_end(key)
            return cached
        value = self._dataset_builder(
            self.source_path,
            coordinate_cache_path=self.coordinate_cache_path,
            destination_region=request.destination_region,
            origin_fias=request.origin_fias,
            period_types=set(request.period_types),
            price_types=set(request.price_types),
        )
        self._location_cache[key] = value
        self._location_cache.move_to_end(key)
        while len(self._location_cache) > 16:
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
        locations: list[LocationPoint], projection: LocalProjection
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
                )
            )
        return points

    @staticmethod
    def _quality(locations: list[LocationPoint], report: dict[str, Any]) -> dict[str, Any]:
        coordinates = report.get("coordinates", {})
        location_counts = report.get("locations", {})
        return {
            "locations_total": len(locations),
            "fias_locations": location_counts.get("fias", len(locations)),
            "fallback_locations": location_counts.get("fallback", 0),
            "coordinates_resolved": coordinates.get("resolved", 0),
            "coordinates_unresolved": coordinates.get("unresolved", 0),
            "location_coverage_pct": coordinates.get("location_coverage_pct", 0),
            "trip_coverage_pct": coordinates.get("trip_coverage_pct", 0),
            "unresolved": list(report.get("unresolved", [])),
        }

    @staticmethod
    def _point_json(
        location: LocationPoint, assignments: dict[str, int] | None = None
    ) -> dict[str, Any]:
        return {
            "id": location.id,
            "fias_id": location.fias_id,
            "name": location.name,
            "lat": location.latitude,
            "lon": location.longitude,
            "trip_count": location.trip_count,
            "cluster_id": assignments.get(location.id) if assignments else None,
            "coordinate_source": location.coordinate_source,
        }

    def preview(self, request: ClusteringRequest) -> dict[str, Any]:
        locations, report = self._locations(request)
        return {
            "analysis": self._analysis(request),
            "data_quality": self._quality(locations, report),
            "points": [self._point_json(point) for point in locations],
        }

    def _origin(self, fias_id: str) -> dict[str, Any]:
        matches = self.origins(fias_id, limit=1)
        if matches and matches[0]["fias_id"] == fias_id:
            return matches[0]
        return {"fias_id": fias_id, "name": fias_id, "region": "", "trip_count": 0}

    def _analysis(self, request: ClusteringRequest) -> dict[str, Any]:
        return {
            "source": "pulse",
            "origin": self._origin(request.origin_fias),
            "destination_region": request.destination_region,
            "filters": request.filters(),
            "algorithm": request.algorithm,
            "parameters": request.parameters(),
        }

    def run(self, request: ClusteringRequest) -> dict[str, Any]:
        locations, report = self._locations(request)
        projection = self._projection(locations)
        points = self._ml_input(locations, projection)
        if len(points) < request.n_clusters:
            raise ProductClusteringError(
                "INSUFFICIENT_POINTS",
                f"Недостаточно точек для {request.n_clusters} зон. Доступно: {len(points)}.",
                422,
            )
        clusterer = self.clusterers[request.algorithm]
        internal_parameters = {
            "n_clusters": request.n_clusters,
            "weight_mode": (
                "shipment_count" if request.weight_mode == "trip_count" else "none"
            ),
            "random_state": 42,
        }
        result = clusterer.fit(points, internal_parameters)
        boundary = self.boundary_provider.get_region_boundary(request.destination_region)
        territorial_metrics: dict[str, Any] | None = None
        if boundary is None:
            zones = {
                "available": False,
                "status": "boundary_unavailable",
                "geojson": None,
            }
        else:
            territorial = territorialize(points, result, boundary, projection)
            territorial_metrics = territorial.metrics
            zones = {
                "available": True,
                "status": "available",
                "geojson": territorial.zones_geojson,
            }
        return {
            "analysis": self._analysis(request),
            "data_quality": self._quality(locations, report),
            "metrics": dict(result.metrics),
            "territorial_metrics": territorial_metrics,
            "points": [self._point_json(point, result.point_assignments) for point in locations],
            "clusters": [self._cluster_json(cluster) for cluster in result.clusters],
            "zones": zones,
        }

    @staticmethod
    def _cluster_json(cluster: Any) -> dict[str, Any]:
        return {
            "cluster_id": cluster.cluster_id,
            "point_count": cluster.point_count,
            "trip_count": cluster.trip_count,
            "medoid_point_id": cluster.medoid_point_id,
        }
