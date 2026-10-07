"""Resolve canonical destination economics to spatial points."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ml.data.clustering_dataset import (
    CLUSTERING_ALLOWED_PERIOD_TYPES,
    ClusteringRoute,
    _csv_set,
    build_clustering_routes,
)
from ml.data.loader import default_csv_path
from ml.spatial.projection import LocalProjection

_LOCATION_PREFIXES = (
    "городской поселок ", "рабочий поселок ", "деревня ", "посёлок ",
    "поселок ", "станица ", "слобода ", "город ", "село ", "г. ",
    "г ", "с. ", "с ", "д. ", "д ", "п. ", "п ",
)


def normalize_location_name(name: str | None) -> str:
    value = (name or "").strip()
    lowered = value.casefold()
    for prefix in _LOCATION_PREFIXES:
        if lowered.startswith(prefix):
            return value[len(prefix) :].strip()
    return value


@dataclass(frozen=True, slots=True)
class LocationPoint:
    id: str
    id_source: str
    fias_id: str
    name: str
    region: str
    latitude: float | None
    longitude: float | None
    x: float | None
    y: float | None
    record_count: int
    trip_count: int
    weighted_route_length: float | None
    weighted_price: float | None
    weighted_rub_per_km: float | None
    valid_route_length_trip_count: int
    valid_price_trip_count: int
    valid_rub_per_km_trip_count: int
    economic_status: str
    active_period_count: int
    coordinate_source: str
    coordinate_status: str
    coordinate_match: str
    data_quality_flags: tuple[str, ...]


def _valid_coordinates(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, list | tuple) or len(value) != 2:
        return None
    try:
        latitude, longitude = float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return latitude, longitude


def _resolve_coordinates(
    cache: dict[str, Any], name: str, region: str
) -> tuple[float | None, float | None, str, str]:
    keys = (
        (f"{name}::{region}", "cache_exact"),
        (f"{normalize_location_name(name)}::{region}", "cache_normalized"),
    )
    present = False
    for key, source in keys:
        if key not in cache:
            continue
        present = True
        coordinates = _valid_coordinates(cache[key])
        if coordinates is not None:
            return coordinates[0], coordinates[1], "unverified_cache", source
    return (
        None,
        None,
        "unresolved",
        "cache_null" if present else "not_in_cache",
    )


def build_location_dataset(
    path: str | Path | None = None,
    *,
    coordinate_cache_path: str | Path = "backend/cache/coords_cache.json",
    destination_region: str | None = None,
    origin_fias: str | None = None,
    period_types: set[str] | None = None,
    price_types: set[str] | None = None,
    vehicle_types: set[str] | None = None,
    tonnage_ids: set[str] | None = None,
    allow_name_fallback: bool = False,
) -> tuple[list[LocationPoint], dict[str, Any]]:
    if allow_name_fallback:
        raise ValueError("Clustering Contract v1 requires destination FIAS identity")
    source_path = Path(path) if path is not None else default_csv_path()
    cache_path = Path(coordinate_cache_path)
    routes, route_report = build_clustering_routes(
        source_path,
        destination_region=destination_region,
        origin_fias=origin_fias,
        period_types=period_types,
        price_types=price_types,
        vehicle_types=vehicle_types,
        tonnage_ids=tonnage_ids,
    )

    return resolve_location_routes(
        routes,
        route_report,
        coordinate_cache_path=cache_path,
    )


def resolve_location_routes(
    routes: list[ClusteringRoute],
    route_report: dict[str, Any],
    *,
    coordinate_cache_path: str | Path = "backend/cache/coords_cache.json",
) -> tuple[list[LocationPoint], dict[str, Any]]:
    """Resolve repository-produced canonical routes without rescanning Pulse."""
    cache_path = Path(coordinate_cache_path)
    cache = json.loads(cache_path.read_text(encoding="utf-8"))

    resolved_rows: list[
        tuple[Any, float | None, float | None, str, str]
    ] = []
    for route in routes:
        latitude, longitude, source, coordinate_match = _resolve_coordinates(
            cache, route.destination_name, route.destination_region
        )
        resolved_rows.append(
            (route, latitude, longitude, source, coordinate_match)
        )
    projection_coordinates = [
        (latitude, longitude)
        for _, latitude, longitude, _, _ in resolved_rows
        if latitude is not None and longitude is not None
    ]
    projection = (
        LocalProjection.from_coordinates(projection_coordinates)
        if projection_coordinates
        else None
    )

    points: list[LocationPoint] = []
    for (
        route,
        latitude,
        longitude,
        coordinate_source,
        coordinate_match,
    ) in resolved_rows:
        x = y = None
        flags = set(route.data_quality_flags)
        if latitude is not None and longitude is not None and projection is not None:
            x, y = projection.project(latitude, longitude)
        else:
            flags.add("unresolved_coordinates")
        points.append(
            LocationPoint(
                id=route.destination_fias,
                id_source="fias",
                fias_id=route.destination_fias,
                name=route.destination_name,
                region=route.destination_region,
                latitude=latitude,
                longitude=longitude,
                x=x,
                y=y,
                record_count=route.record_count,
                trip_count=route.trip_count,
                weighted_route_length=route.weighted_route_length,
                weighted_price=route.weighted_price,
                weighted_rub_per_km=route.weighted_rub_per_km,
                valid_route_length_trip_count=route.valid_route_length_trip_count,
                valid_price_trip_count=route.valid_price_trip_count,
                valid_rub_per_km_trip_count=route.valid_rub_per_km_trip_count,
                economic_status=(
                    "available"
                    if route.weighted_rub_per_km is not None
                    else "insufficient_weight"
                ),
                active_period_count=route.active_period_count,
                coordinate_source=coordinate_source,
                coordinate_status=(
                    "resolved" if latitude is not None else "unresolved"
                ),
                coordinate_match=coordinate_match,
                data_quality_flags=tuple(sorted(flags)),
            )
        )
    points.sort(key=lambda point: (-point.trip_count, point.id))

    resolved = [point for point in points if point.x is not None]
    total_trips = sum(point.trip_count for point in points)
    resolved_trips = sum(point.trip_count for point in resolved)
    report = {
        **route_report,
        "coordinate_cache_path": str(cache_path.resolve()),
        "locations": {"total": len(points), "fias": len(points), "fallback": 0},
        "coordinates": {
            "resolved": len(resolved),
            "unresolved": len(points) - len(resolved),
            "trip_count_resolved": resolved_trips,
            "trip_count_total": total_trips,
            "location_coverage_pct": round(100 * len(resolved) / len(points), 4)
            if points
            else 0,
            "trip_coverage_pct": round(100 * resolved_trips / total_trips, 4)
            if total_trips
            else 0,
            "sources": dict(Counter(point.coordinate_source for point in points)),
            "projection": (
                {
                    "name": "local_azimuthal_equidistant",
                    "center_latitude": projection.center_latitude,
                    "center_longitude": projection.center_longitude,
                }
                if projection
                else None
            ),
        },
        "unresolved": [
            {"id": point.id, "name": point.name, "trip_count": point.trip_count}
            for point in points
            if point.x is None
        ],
        "data_quality": {
            "excluded_missing_fias": route_report[
                "excluded_missing_fias_rows"
            ],
            "destination_points_total": len(points),
            "resolved_points": len(resolved),
            "unresolved_points": len(points) - len(resolved),
            "point_coverage_pct": (
                round(100 * len(resolved) / len(points), 4) if points else 0
            ),
            "trip_weight_coverage_pct": (
                round(100 * resolved_trips / total_trips, 4)
                if total_trips
                else 0
            ),
            "coordinate_source_distribution": dict(
                Counter(point.coordinate_source for point in points)
            ),
        },
    }
    return points, report


def write_location_dataset(
    points: list[LocationPoint],
    report: dict[str, Any],
    output_dir: str | Path = "reports/locations",
) -> tuple[Path, Path, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "locations.json"
    csv_path = destination / "locations.csv"
    audit_path = destination / "location_audit.json"
    json_path.write_text(
        json.dumps([asdict(point) for point in points], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(asdict(points[0])) if points else ["id"])
        writer.writeheader()
        writer.writerows(asdict(point) for point in points)
    audit_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return json_path, csv_path, audit_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=default_csv_path())
    parser.add_argument(
        "--coordinate-cache", type=Path, default=Path("backend/cache/coords_cache.json")
    )
    parser.add_argument("--destination-region", required=True)
    parser.add_argument("--origin-fias", required=True)
    parser.add_argument("--period-types", type=_csv_set, default=set(CLUSTERING_ALLOWED_PERIOD_TYPES))
    parser.add_argument("--price-types", type=_csv_set)
    parser.add_argument("--vehicle-types", type=_csv_set)
    parser.add_argument("--tonnage-ids", type=_csv_set)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/locations"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    points, report = build_location_dataset(
        args.path,
        coordinate_cache_path=args.coordinate_cache,
        destination_region=args.destination_region,
        origin_fias=args.origin_fias,
        period_types=args.period_types,
        price_types=args.price_types,
        vehicle_types=args.vehicle_types,
        tonnage_ids=args.tonnage_ids,
    )
    json_path, csv_path, audit_path = write_location_dataset(points, report, args.output_dir)
    print(f"Built {len(points)} locations")
    print(f"JSON: {json_path}\nCSV: {csv_path}\nAudit: {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
