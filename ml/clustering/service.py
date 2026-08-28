"""Framework-independent Clustering Product v1 service."""

from __future__ import annotations

import copy
import json
import math
import statistics
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ml.clustering.base import ClusterPoint, ClusterResult
from ml.clustering.bear_zones import BearZoneDetector
from ml.clustering.economics import relative_rate_delta, weighted_mean
from ml.clustering.geo_cost import GeoCostClusterer
from ml.clustering.geographic import GeographicClusterer
from ml.data.clustering_dataset import CLUSTERING_ALLOWED_PERIOD_TYPES, ClusteringRoute
from ml.data.clustering_repository import ClusteringRepository, FileFingerprint
from ml.data.locations import _resolve_coordinates
from ml.spatial.graph import SpatialEdge, SpatialGraph, SpatialGraphBuilder
from ml.spatial.projection import LocalProjection

COORDINATE_POLICY = "accepted_existing_cache_v1"
PRODUCT_MODES = frozenset({"geography", "geo_cost", "bear_zones"})
TESTED_GEO_COST_WEIGHTS = ((0.8, 0.2), (0.7, 0.3), (0.6, 0.4))
TESTED_BEAR_THRESHOLDS = frozenset({20.0, 25.0, 30.0, 35.0, 40.0, 50.0})


class ProductClusteringError(ValueError):
    def __init__(self, code: str, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass(frozen=True, slots=True)
class ClusteringRequest:
    origin_fias: str
    destination_region: str
    mode: str
    period_types: tuple[str, ...] = ("current",)
    price_types: tuple[str, ...] = ()
    vehicle_types: tuple[str, ...] = ()
    tonnage_ids: tuple[str, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Any) -> ClusteringRequest:
        if not isinstance(payload, dict):
            raise ProductClusteringError("INVALID_REQUEST", "Ожидается JSON-объект.", 400)
        origin = payload.get("origin_fias")
        region = payload.get("destination_region")
        mode = payload.get("mode")
        if not isinstance(origin, str) or not origin.strip():
            raise ProductClusteringError("INVALID_REQUEST", "Не указан origin_fias.", 400)
        if not isinstance(region, str) or not region.strip():
            raise ProductClusteringError(
                "INVALID_REQUEST", "Не указан destination_region.", 400
            )
        if mode not in PRODUCT_MODES:
            raise ProductClusteringError("INVALID_REQUEST", "Неизвестный режим анализа.", 400)
        filters = payload.get("filters") or {}
        parameters = payload.get("parameters") or {}
        if not isinstance(filters, dict) or not isinstance(parameters, dict):
            raise ProductClusteringError(
                "INVALID_REQUEST", "filters и parameters должны быть объектами.", 400
            )

        def values(name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
            raw = filters.get(name, list(default))
            if not isinstance(raw, list) or any(
                not isinstance(value, str) or not value.strip() for value in raw
            ):
                raise ProductClusteringError(
                    "INVALID_REQUEST", f"filters.{name} должен быть списком строк.", 400
                )
            return tuple(sorted(set(value.strip() for value in raw)))

        periods = values("period_types", ("current",))
        if not periods:
            raise ProductClusteringError(
                "INVALID_REQUEST", "Нужно выбрать хотя бы один период.", 400
            )
        invalid_periods = set(periods) - set(CLUSTERING_ALLOWED_PERIOD_TYPES)
        if invalid_periods:
            raise ProductClusteringError(
                "INVALID_REQUEST",
                f"Неизвестные period_types: {', '.join(sorted(invalid_periods))}.",
                400,
            )
        return cls(
            origin_fias=origin.strip(),
            destination_region=region.strip(),
            mode=mode,
            period_types=periods,
            price_types=values("price_types"),
            vehicle_types=values("vehicle_types"),
            tonnage_ids=values("tonnage_ids"),
            parameters=dict(parameters),
        )

    def normalized_parameters(self) -> dict[str, Any]:
        parameters = dict(self.parameters)
        if self.mode in {"geography", "geo_cost"}:
            allowed = {"k_mode", "n_clusters"}
            if self.mode == "geo_cost":
                allowed |= {"geography_weight", "economics_weight"}
            unknown = set(parameters) - allowed
            if unknown:
                raise ProductClusteringError(
                    "INVALID_REQUEST",
                    f"Недопустимые parameters для {self.mode}: {', '.join(sorted(unknown))}.",
                    400,
                )
            k_mode = parameters.get("k_mode", "auto")
            if k_mode not in {"auto", "manual"}:
                raise ProductClusteringError(
                    "INVALID_REQUEST", "k_mode должен быть auto или manual.", 400
                )
            normalized: dict[str, Any] = {"k_mode": k_mode}
            if k_mode == "manual":
                value = parameters.get("n_clusters")
                if isinstance(value, bool) or not isinstance(value, int) or not 2 <= value <= 20:
                    raise ProductClusteringError(
                        "INVALID_REQUEST", "n_clusters должен быть целым числом от 2 до 20.", 400
                    )
                normalized["n_clusters"] = value
            elif "n_clusters" in parameters:
                raise ProductClusteringError(
                    "INVALID_REQUEST", "n_clusters допустим только при k_mode=manual.", 400
                )
            if self.mode == "geo_cost":
                geography = float(parameters.get("geography_weight", 0.7))
                economics = float(parameters.get("economics_weight", 0.3))
                total = geography + economics
                if total <= 0:
                    raise ProductClusteringError(
                        "INVALID_REQUEST", "Веса Geo+Cost должны быть положительными.", 400
                    )
                pair = (round(geography / total, 6), round(economics / total, 6))
                if not any(
                    math.isclose(pair[0], tested[0]) and math.isclose(pair[1], tested[1])
                    for tested in TESTED_GEO_COST_WEIGHTS
                ):
                    raise ProductClusteringError(
                        "INVALID_REQUEST", "Поддерживаются веса 80/20, 70/30 и 60/40.", 400
                    )
                normalized.update(
                    {"geography_weight": pair[0], "economics_weight": pair[1]}
                )
            return normalized

        allowed = {"bear_threshold_pct", "singleton_threshold_pct"}
        unknown = set(parameters) - allowed
        if unknown:
            raise ProductClusteringError(
                "INVALID_REQUEST",
                f"Bear Zones не поддерживает параметры: {', '.join(sorted(unknown))}.",
                400,
            )
        bear = float(parameters.get("bear_threshold_pct", 35.0))
        singleton = float(parameters.get("singleton_threshold_pct", 70.0))
        if bear not in TESTED_BEAR_THRESHOLDS or singleton != 70.0:
            raise ProductClusteringError(
                "INVALID_REQUEST",
                "Bear threshold должен быть одним из 20, 25, 30, 35, 40, 50; singleton — 70.",
                400,
            )
        return {"bear_threshold_pct": bear, "singleton_threshold_pct": singleton}

    def cache_key(self, parameters: dict[str, Any]) -> tuple[Any, ...]:
        return (
            self.origin_fias,
            self.destination_region,
            self.period_types,
            self.price_types,
            self.vehicle_types,
            self.tonnage_ids,
            self.mode,
            json.dumps(parameters, sort_keys=True, ensure_ascii=True),
        )


@dataclass(slots=True)
class ProductClusteringContext:
    routes: list[ClusteringRoute]
    report: dict[str, Any]
    point_rows: list[dict[str, Any]]
    resolved_points: list[ClusterPoint]
    projection: LocalProjection
    graph: SpatialGraph
    data_quality: dict[str, Any]
    dataset_fingerprint: FileFingerprint
    coordinate_fingerprint: FileFingerprint
    graph_cache_hit: bool


def _components(node_ids: tuple[str, ...], adjacency: dict[str, frozenset[str]]) -> tuple[tuple[str, ...], ...]:
    remaining = set(node_ids)
    result: list[tuple[str, ...]] = []
    while remaining:
        start = min(remaining)
        stack = [start]
        seen = {start}
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in remaining and neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        remaining -= seen
        result.append(tuple(sorted(seen)))
    return tuple(sorted(result, key=lambda item: item[0]))


def induced_spatial_graph(graph: SpatialGraph, point_ids: set[str]) -> SpatialGraph:
    """Return a true induced subgraph; never invent an edge after filtering."""
    node_ids = tuple(point_id for point_id in graph.node_ids if point_id in point_ids)
    edges = tuple(
        edge
        for edge in graph.edges
        if edge.first_id in point_ids and edge.second_id in point_ids
    )
    adjacency = {
        point_id: frozenset(neighbor for neighbor in graph.adjacency[point_id] if neighbor in point_ids)
        for point_id in node_ids
    }
    components = _components(node_ids, adjacency)
    isolated = tuple(point_id for point_id in node_ids if not adjacency[point_id])
    lengths = [edge.distance_m for edge in edges]
    degrees = [len(adjacency[point_id]) for point_id in node_ids]
    audit = {
        **graph.audit,
        "node_count": len(node_ids),
        "edge_count": len(edges),
        "graph_component_count": len(components),
        "isolated_point_count": len(isolated),
        "mean_degree": statistics.fmean(degrees) if degrees else 0.0,
        "mean_edge_m": statistics.fmean(lengths) if lengths else None,
        "p95_edge_m": float(sorted(lengths)[round((len(lengths) - 1) * 0.95)]) if lengths else None,
        "max_edge_m": max(lengths) if lengths else None,
    }
    return SpatialGraph(
        node_ids=node_ids,
        edges=tuple(SpatialEdge(edge.first_id, edge.second_id, edge.distance_m) for edge in edges),
        adjacency=adjacency,
        connected_components=components,
        isolated_point_ids=isolated,
        method=graph.method,
        parameters=dict(graph.parameters),
        audit=audit,
    )


class ProductClusteringService:
    def __init__(
        self,
        repository: ClusteringRepository | None = None,
        *,
        coordinate_cache_path: str | Path = "backend/cache/coords_cache.json",
        result_cache_size: int = 64,
        graph_cache_size: int = 32,
    ) -> None:
        self.repository = repository or ClusteringRepository()
        self.coordinate_cache_path = Path(coordinate_cache_path)
        self.result_cache_size = result_cache_size
        self.graph_cache_size = graph_cache_size
        self._lock = threading.RLock()
        self._coordinate_fingerprint: FileFingerprint | None = None
        self._coordinate_cache: dict[str, Any] = {}
        self._result_cache: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()
        self._graph_cache: OrderedDict[tuple[Any, ...], SpatialGraph] = OrderedDict()

    def options(self, origin_fias: str | None = None, destination_region: str | None = None) -> dict[str, Any]:
        if origin_fias and not self.repository.has_origin(origin_fias):
            raise ProductClusteringError("UNKNOWN_ORIGIN", "Неизвестная точка отправления.")
        if destination_region and (
            not origin_fias
            or not self.repository.has_destination_region(origin_fias, destination_region)
        ):
            raise ProductClusteringError(
                "UNKNOWN_DESTINATION_REGION", "Регион назначения недоступен для origin."
            )
        return {
            "modes": {
                "geography": {"display_name": "По географии", "uses_k": True},
                "geo_cost": {"display_name": "География + стоимость", "uses_k": True},
                "bear_zones": {"display_name": "Медвежьи зоны", "uses_k": False},
            },
            "defaults": {
                "period_types": ["current"],
                "geography": {"k_mode": "auto"},
                "geo_cost": {
                    "k_mode": "auto",
                    "geography_weight": 0.7,
                    "economics_weight": 0.3,
                },
                "bear_zones": {"bear_threshold_pct": 35, "singleton_threshold_pct": 70},
                "coordinate_policy": COORDINATE_POLICY,
            },
            **self.repository.options(origin_fias, destination_region),
        }

    def _coordinates(self) -> tuple[dict[str, Any], FileFingerprint]:
        fingerprint = FileFingerprint.from_path(self.coordinate_cache_path)
        with self._lock:
            if fingerprint != self._coordinate_fingerprint:
                self._coordinate_cache = json.loads(
                    self.coordinate_cache_path.read_text(encoding="utf-8")
                )
                self._coordinate_fingerprint = fingerprint
            return self._coordinate_cache, fingerprint

    def _graph(self, points: list[ClusterPoint]) -> tuple[SpatialGraph, bool]:
        key = tuple((point.id, point.x, point.y) for point in sorted(points, key=lambda item: item.id))
        with self._lock:
            if key in self._graph_cache:
                graph = self._graph_cache.pop(key)
                self._graph_cache[key] = graph
                return graph, True
        graph = SpatialGraphBuilder(method="delaunay", edge_mad_multiplier=3.0).build(points)
        with self._lock:
            self._graph_cache[key] = graph
            while len(self._graph_cache) > self.graph_cache_size:
                self._graph_cache.popitem(last=False)
        return graph, False

    def _context(self, request: ClusteringRequest) -> ProductClusteringContext:
        if not self.repository.has_origin(request.origin_fias):
            raise ProductClusteringError("UNKNOWN_ORIGIN", "Неизвестная точка отправления.")
        if not self.repository.has_destination_region(
            request.origin_fias, request.destination_region
        ):
            raise ProductClusteringError(
                "UNKNOWN_DESTINATION_REGION", "Регион назначения недоступен для origin."
            )
        routes, report = self.repository.aggregate(
            origin_fias=request.origin_fias,
            destination_region=request.destination_region,
            period_types=set(request.period_types),
            price_types=set(request.price_types),
            vehicle_types=set(request.vehicle_types),
            tonnage_ids=set(request.tonnage_ids),
        )
        if not routes:
            raise ProductClusteringError("NO_DATA", "По выбранным фильтрам данных нет.")
        cache, coordinate_fingerprint = self._coordinates()
        resolved_coordinates: list[tuple[float, float]] = []
        point_rows: list[dict[str, Any]] = []
        for route in routes:
            latitude, longitude, _source, coordinate_match = _resolve_coordinates(
                cache, route.destination_name, route.destination_region
            )
            if latitude is not None and longitude is not None:
                resolved_coordinates.append((latitude, longitude))
            point_rows.append(
                {
                    "route": route,
                    "latitude": latitude,
                    "longitude": longitude,
                    "coordinate_source": "cache" if latitude is not None else "unresolved",
                    "coordinate_match": coordinate_match,
                }
            )
        if len(resolved_coordinates) < 2:
            raise ProductClusteringError(
                "INSUFFICIENT_SPATIAL_POINTS",
                "Недостаточно точек с координатами для анализа.",
            )
        projection = LocalProjection.from_coordinates(resolved_coordinates)
        resolved_points: list[ClusterPoint] = []
        for row in point_rows:
            if row["latitude"] is None or row["longitude"] is None:
                continue
            route = row["route"]
            x, y = projection.project(row["latitude"], row["longitude"])
            resolved_points.append(
                ClusterPoint(
                    id=route.destination_fias,
                    name=route.destination_name,
                    region=route.destination_region,
                    x=x,
                    y=y,
                    trip_count=route.trip_count,
                    weighted_price=route.weighted_price,
                    weighted_rub_per_km=route.weighted_rub_per_km,
                    data_quality_flags=route.data_quality_flags,
                )
            )
        graph, graph_cache_hit = self._graph(resolved_points)
        total_trips = sum(route.trip_count for route in routes)
        resolved_ids = {point.id for point in resolved_points}
        resolved_trips = sum(
            route.trip_count for route in routes if route.destination_fias in resolved_ids
        )
        data_quality = {
            "source_rows": report["filtered_source_rows"],
            "destination_points_total": len(routes),
            "resolved_points": len(resolved_points),
            "unresolved_points": len(routes) - len(resolved_points),
            "point_coverage_pct": round(100 * len(resolved_points) / len(routes), 4),
            "trip_weight_coverage_pct": round(100 * resolved_trips / total_trips, 4)
            if total_trips
            else 0.0,
            "excluded_missing_fias": report["excluded_missing_fias_rows"],
            "missing_economics_points": sum(
                route.weighted_rub_per_km is None for route in routes
            ),
            "coordinate_policy": COORDINATE_POLICY,
            "coordinate_source": "cache",
        }
        return ProductClusteringContext(
            routes=routes,
            report=report,
            point_rows=point_rows,
            resolved_points=resolved_points,
            projection=projection,
            graph=graph,
            data_quality=data_quality,
            dataset_fingerprint=self.repository.fingerprint(),
            coordinate_fingerprint=coordinate_fingerprint,
            graph_cache_hit=graph_cache_hit,
        )

    def run(self, request: ClusteringRequest) -> dict[str, Any]:
        parameters = request.normalized_parameters()
        dataset_fingerprint = self.repository.fingerprint()
        _coordinate_cache, coordinate_fingerprint = self._coordinates()
        key = (
            dataset_fingerprint.cache_token(),
            coordinate_fingerprint.cache_token(),
            *request.cache_key(parameters),
        )
        with self._lock:
            if key in self._result_cache:
                cached = copy.deepcopy(self._result_cache.pop(key))
                self._result_cache[key] = copy.deepcopy(cached)
                cached["cache"]["result_hit"] = True
                return cached
        context = self._context(request)
        result = self._execute(request, parameters, context)
        result["cache"] = {"result_hit": False, "graph_hit": context.graph_cache_hit}
        with self._lock:
            self._result_cache[key] = copy.deepcopy(result)
            while len(self._result_cache) > self.result_cache_size:
                self._result_cache.popitem(last=False)
        return result

    def compare(self, request: ClusteringRequest) -> dict[str, Any]:
        context = self._context(request)
        results = {}
        for mode, parameters in (
            ("geography", {"k_mode": "auto"}),
            (
                "geo_cost",
                {"k_mode": "auto", "geography_weight": 0.7, "economics_weight": 0.3},
            ),
            ("bear_zones", {"bear_threshold_pct": 35.0, "singleton_threshold_pct": 70.0}),
        ):
            mode_request = ClusteringRequest(
                origin_fias=request.origin_fias,
                destination_region=request.destination_region,
                mode=mode,
                period_types=request.period_types,
                price_types=request.price_types,
                vehicle_types=request.vehicle_types,
                tonnage_ids=request.tonnage_ids,
                parameters=parameters,
            )
            results[mode] = self._execute(mode_request, parameters, context)
        comparison = []
        for mode, result in results.items():
            comparison.append(
                {
                    "mode": mode,
                    "cluster_count": result["summary"]["cluster_count"],
                    "outlier_count": result["summary"]["outlier_count"],
                    "p95_radius_km": result["summary"]["p95_radius_km"],
                    "weighted_rub_per_km_spread": result["summary"][
                        "weighted_rub_per_km_spread"
                    ],
                    "trip_coverage_pct": result["summary"]["trip_coverage_pct"],
                }
            )
        return {
            "filters": results["geography"]["filters"],
            "comparison": comparison,
            "results": results,
            "winner": None,
        }

    def _execute(
        self,
        request: ClusteringRequest,
        parameters: dict[str, Any],
        context: ProductClusteringContext,
    ) -> dict[str, Any]:
        points = context.resolved_points
        graph = context.graph
        algorithm_parameters: dict[str, Any] = {"spatial_graph": graph, "k_max": 20}
        excluded_economics: set[str] = set()
        try:
            if request.mode == "geography":
                algorithm_parameters["n_clusters"] = (
                    parameters.get("n_clusters")
                    if parameters["k_mode"] == "manual"
                    else "auto"
                )
                research_result = GeographicClusterer().fit(points, algorithm_parameters)
            elif request.mode == "geo_cost":
                economic_points = [
                    point for point in points if point.weighted_rub_per_km is not None
                ]
                excluded_economics = {point.id for point in points} - {
                    point.id for point in economic_points
                }
                if len(economic_points) < 2:
                    raise ProductClusteringError(
                        "ECONOMICS_UNAVAILABLE",
                        "Недостаточно направлений с корректной ценой и километражом.",
                    )
                economic_graph = induced_spatial_graph(
                    graph, {point.id for point in economic_points}
                )
                if not any(len(component) > 1 for component in economic_graph.connected_components):
                    raise ProductClusteringError(
                        "ECONOMICS_UNAVAILABLE",
                        "Экономические точки не образуют связный spatial context.",
                    )
                algorithm_parameters.update(
                    {
                        "spatial_graph": economic_graph,
                        "n_clusters": parameters.get("n_clusters")
                        if parameters["k_mode"] == "manual"
                        else "auto",
                        "geography_weight": parameters["geography_weight"],
                        "economics_weight": parameters["economics_weight"],
                    }
                )
                research_result = GeoCostClusterer().fit(
                    economic_points, algorithm_parameters
                )
            else:
                if weighted_mean(
                    (point.weighted_rub_per_km, point.trip_count) for point in points
                ) is None:
                    raise ProductClusteringError(
                        "ECONOMICS_UNAVAILABLE", "Для Bear Zones недоступна экономика."
                    )
                algorithm_parameters = {
                    "spatial_graph": graph,
                    "bear_threshold": parameters["bear_threshold_pct"] / 100,
                    "singleton_threshold": parameters["singleton_threshold_pct"] / 100,
                }
                research_result = BearZoneDetector().fit(points, algorithm_parameters)
        except ProductClusteringError:
            raise
        except ValueError as error:
            if "n_clusters" in str(error) or "clusterable" in str(error):
                raise ProductClusteringError(
                    "INVALID_CLUSTER_COUNT", "Выбранное K невозможно для spatial graph."
                ) from error
            raise
        return self._product_result(
            request, parameters, context, research_result, excluded_economics
        )

    def _product_result(
        self,
        request: ClusteringRequest,
        parameters: dict[str, Any],
        context: ProductClusteringContext,
        result: ClusterResult,
        excluded_economics: set[str],
    ) -> dict[str, Any]:
        regional_rate = weighted_mean(
            (route.weighted_rub_per_km, route.trip_count) for route in context.routes
        )
        regional_price = weighted_mean(
            (route.weighted_price, route.trip_count) for route in context.routes
        )
        routes = {route.destination_fias: route for route in context.routes}
        outlier_ids = {item["point_id"] for item in result.outliers}
        cluster_types = {
            cluster.cluster_id: cluster.cluster_type for cluster in result.clusters
        }
        bear_threshold = parameters.get("bear_threshold_pct", 35.0) / 100
        point_dtos = []
        for row in context.point_rows:
            route = row["route"]
            assignment = result.point_assignments.get(route.destination_fias)
            delta = relative_rate_delta(route.weighted_rub_per_km, regional_rate)
            if row["latitude"] is None:
                status = "unresolved"
                cluster_type = None
                assignment = None
            elif route.destination_fias in excluded_economics:
                status = "economic_unavailable"
                cluster_type = None
                assignment = None
            elif request.mode == "bear_zones" and assignment == -1 and delta is not None and delta >= bear_threshold:
                status = "bear_candidate"
                cluster_type = "bear_candidate"
                assignment = None
            elif assignment == -1 or route.destination_fias in outlier_ids:
                status = "spatial_outlier"
                cluster_type = "spatial_outlier"
                assignment = None
            elif assignment is not None and assignment >= 0:
                status = "clustered"
                cluster_type = cluster_types.get(assignment, "normal")
            else:
                status = "available"
                cluster_type = None
                assignment = None
            point_dtos.append(
                {
                    "id": route.destination_fias,
                    "fias_id": route.destination_fias,
                    "name": route.destination_name,
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "cluster_id": assignment,
                    "cluster_type": cluster_type,
                    "status": status,
                    "trip_count": route.trip_count,
                    "weighted_price": route.weighted_price,
                    "weighted_rub_per_km": route.weighted_rub_per_km,
                    "relative_rate_delta": delta,
                }
            )
        cluster_dtos = []
        for cluster in result.clusters:
            centroid_lat, centroid_lon = context.projection.unproject(*cluster.centroid)
            medoid_route = routes[cluster.medoid_point_id]
            medoid_row = next(
                row for row in context.point_rows if row["route"].destination_fias == cluster.medoid_point_id
            )
            cluster_dtos.append(
                {
                    "cluster_id": cluster.cluster_id,
                    "cluster_type": cluster.cluster_type,
                    "point_count": cluster.point_count,
                    "trip_count": cluster.trip_count,
                    "weighted_price": cluster.weighted_price,
                    "weighted_rub_per_km": cluster.weighted_rub_per_km,
                    "regional_weighted_rub_per_km": regional_rate,
                    "relative_rate_delta": relative_rate_delta(
                        cluster.weighted_rub_per_km, regional_rate
                    ),
                    "centroid": {"latitude": centroid_lat, "longitude": centroid_lon},
                    "medoid": {
                        "point_id": medoid_route.destination_fias,
                        "name": medoid_route.destination_name,
                        "latitude": medoid_row["latitude"],
                        "longitude": medoid_row["longitude"],
                    },
                    "mean_radius_km": cluster.mean_radius_km,
                    "p95_radius_km": cluster.p95_radius_km,
                    "max_radius_km": cluster.max_radius_km,
                    "connected": cluster.connected,
                    "point_ids": list(cluster.point_ids),
                }
            )
        warnings = []
        metadata = context.report["metadata"]
        mixed = any(
            metadata[name]
            for name in ("mixed_price_types", "mixed_vehicle_types", "mixed_tonnages")
        )
        if metadata["contains_forecast"]:
            warnings.append("contains_forecast")
        if mixed:
            warnings.append("mixed_tariff_segments")
        if context.data_quality["unresolved_points"]:
            warnings.append("incomplete_coordinate_coverage")
        if excluded_economics:
            warnings.append("economic_points_excluded")
        rates = [
            cluster["weighted_rub_per_km"]
            for cluster in cluster_dtos
            if cluster["weighted_rub_per_km"] is not None
        ]
        p95_values = [
            cluster["p95_radius_km"]
            for cluster in cluster_dtos
            if cluster["p95_radius_km"] is not None
        ]
        assigned_trips = sum(
            route.trip_count
            for route in context.routes
            if result.point_assignments.get(route.destination_fias, -1) >= 0
        )
        total_trips = sum(route.trip_count for route in context.routes)
        return {
            "mode": request.mode,
            "parameters": {
                **parameters,
                "selected_k": result.parameters.get("n_clusters"),
                "graph_method": context.graph.method,
                "graph_threshold_m": context.graph.audit["adaptive_edge_threshold_m"],
            },
            "filters": {
                "origin_fias": request.origin_fias,
                "destination_region": request.destination_region,
                "period_types": list(request.period_types),
                "price_types": list(request.price_types),
                "vehicle_types": list(request.vehicle_types),
                "tonnage_ids": list(request.tonnage_ids),
            },
            "regional_stats": {
                "weighted_price": regional_price,
                "weighted_rub_per_km": regional_rate,
                "trip_count": total_trips,
                "destination_count": len(context.routes),
            },
            "summary": {
                "cluster_count": len(cluster_dtos),
                "outlier_count": sum(point["status"] == "spatial_outlier" for point in point_dtos),
                "bear_candidate_count": sum(point["status"] == "bear_candidate" for point in point_dtos),
                "p95_radius_km": max(p95_values) if p95_values else None,
                "weighted_rub_per_km_spread": max(rates) - min(rates) if rates else None,
                "trip_coverage_pct": 100 * assigned_trips / total_trips if total_trips else 0.0,
            },
            "clusters": cluster_dtos,
            "points": point_dtos,
            "outliers": [point for point in point_dtos if point["status"] in {"spatial_outlier", "unresolved", "economic_unavailable"}],
            "metrics": result.metrics,
            "data_quality": context.data_quality,
            "warnings": warnings,
            "flags": {
                "contains_forecast": metadata["contains_forecast"],
                "mixed_tariff_segments": mixed,
            },
            "diagnostics": {
                "dataset_fingerprint": context.dataset_fingerprint.as_dict(),
                "coordinate_fingerprint": context.coordinate_fingerprint.as_dict(),
                "projection": {
                    "name": "local_azimuthal_equidistant",
                    "center_latitude": context.projection.center_latitude,
                    "center_longitude": context.projection.center_longitude,
                },
                "graph_method": context.graph.method,
                "graph_threshold_m": context.graph.audit["adaptive_edge_threshold_m"],
            },
        }
