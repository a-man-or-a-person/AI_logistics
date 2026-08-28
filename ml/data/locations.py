"""Build one canonical analytical location per destination FIAS."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ml.data.clustering_dataset import CLUSTERING_ALLOWED_PERIOD_TYPES
from ml.data.loader import default_csv_path, iter_records
from ml.data.schema import LogisticsRecord

_LOCATION_PREFIXES = (
    "городской поселок ",
    "рабочий поселок ",
    "деревня ",
    "поселок ",
    "посёлок ",
    "станица ",
    "слобода ",
    "город ",
    "село ",
    "ст-ца ",
    "пгт. ",
    "пгт ",
    "гп. ",
    "гп ",
    "рп. ",
    "рп ",
    "пос. ",
    "пос ",
    "тер ",
    "мкр. ",
    "мкр ",
    "аул ",
    "хутор ",
    "г. ",
    "г ",
    "с. ",
    "с ",
    "д. ",
    "д ",
    "п. ",
    "п ",
    "х. ",
    "х ",
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
    fias_id: str | None
    name: str
    region: str
    latitude: float | None
    longitude: float | None
    coordinate_source: str
    record_count: int
    shipment_count: float
    active_period_count: int
    origin_count: int


@dataclass(slots=True)
class _LocationAccumulator:
    fias_id: str | None
    names: Counter[str] = field(default_factory=Counter)
    regions: Counter[str] = field(default_factory=Counter)
    record_count: int = 0
    shipment_count: float = 0
    periods: set[str] = field(default_factory=set)
    origins: set[str] = field(default_factory=set)

    def add(self, record: LogisticsRecord) -> None:
        if record.destination_name:
            self.names[record.destination_name] += 1
        if record.destination_region:
            self.regions[record.destination_region] += 1
        self.record_count += 1
        self.shipment_count += max(record.shipment_count or 0, 0)
        if record.period_id:
            self.periods.add(record.period_id)
        if record.origin_fias:
            self.origins.add(record.origin_fias)


def _location_id(record: LogisticsRecord) -> tuple[str, str]:
    if record.destination_fias:
        return record.destination_fias, "fias"
    name = normalize_location_name(record.destination_name).casefold() or "<missing>"
    region = (record.destination_region or "<missing>").casefold()
    return f"fallback:{name}::{region}", "name_region_fallback"


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
) -> tuple[float | None, float | None, str]:
    exact_key = f"{name}::{region}"
    normalized_key = f"{normalize_location_name(name)}::{region}"
    keys = ((exact_key, "cache_exact"), (normalized_key, "cache_normalized"))
    present = False
    for key, source in keys:
        if key not in cache:
            continue
        present = True
        coordinates = _valid_coordinates(cache[key])
        if coordinates is not None:
            return coordinates[0], coordinates[1], source
    return None, None, "cache_null" if present else "unresolved"


def build_location_dataset(
    path: str | Path | None = None,
    *,
    coordinate_cache_path: str | Path = "backend/cache/coords_cache.json",
    destination_region: str | None = None,
    origin_fias: str | None = None,
    period_types: set[str] | None = None,
    price_types: set[str] | None = None,
    allow_name_fallback: bool = False,
) -> tuple[list[LocationPoint], dict[str, Any]]:
    source_path = Path(path) if path is not None else default_csv_path()
    cache_path = Path(coordinate_cache_path)
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    requested_period_types = (
        set(period_types) if period_types is not None else set(CLUSTERING_ALLOWED_PERIOD_TYPES)
    )
    selected_period_types = requested_period_types & set(CLUSTERING_ALLOWED_PERIOD_TYPES)
    selected_price_types = price_types or set()
    accumulators: dict[str, _LocationAccumulator] = {}
    id_sources: dict[str, str] = {}
    excluded_missing_fias_records = 0

    for record in iter_records(source_path):
        if destination_region and record.destination_region != destination_region:
            continue
        if origin_fias and record.origin_fias != origin_fias:
            continue
        if record.period_type not in selected_period_types:
            continue
        if selected_price_types and record.price_type not in selected_price_types:
            continue
        if not record.destination_fias and not allow_name_fallback:
            excluded_missing_fias_records += 1
            continue
        location_id, id_source = _location_id(record)
        accumulator = accumulators.setdefault(
            location_id, _LocationAccumulator(fias_id=record.destination_fias)
        )
        id_sources[location_id] = id_source
        accumulator.add(record)

    points: list[LocationPoint] = []
    for location_id, accumulator in accumulators.items():
        name = accumulator.names.most_common(1)[0][0] if accumulator.names else "<missing>"
        region = accumulator.regions.most_common(1)[0][0] if accumulator.regions else "<missing>"
        latitude, longitude, coordinate_source = _resolve_coordinates(cache, name, region)
        points.append(
            LocationPoint(
                id=location_id,
                id_source=id_sources[location_id],
                fias_id=accumulator.fias_id,
                name=name,
                region=region,
                latitude=latitude,
                longitude=longitude,
                coordinate_source=coordinate_source,
                record_count=accumulator.record_count,
                shipment_count=round(accumulator.shipment_count, 4),
                active_period_count=len(accumulator.periods),
                origin_count=len(accumulator.origins),
            )
        )

    points.sort(key=lambda point: (-point.shipment_count, point.id))
    resolved = [point for point in points if point.latitude is not None]
    total_shipments = sum(point.shipment_count for point in points)
    resolved_shipments = sum(point.shipment_count for point in resolved)
    unresolved = [
        {
            "id": point.id,
            "fias_id": point.fias_id,
            "name": point.name,
            "region": point.region,
            "shipment_count": point.shipment_count,
            "coordinate_source": point.coordinate_source,
        }
        for point in points
        if point.latitude is None
    ]
    report = {
        "source_path": str(source_path.resolve()),
        "coordinate_cache_path": str(cache_path.resolve()),
        "filters": {
            "destination_region": destination_region,
            "origin_fias": origin_fias,
            "period_types": sorted(selected_period_types),
            "rejected_period_types": sorted(requested_period_types - selected_period_types),
            "price_types": sorted(selected_price_types),
        },
        "records": sum(point.record_count for point in points),
        "excluded_missing_fias_records": excluded_missing_fias_records,
        "locations": {
            "total": len(points),
            "fias": sum(point.id_source == "fias" for point in points),
            "fallback": sum(point.id_source != "fias" for point in points),
        },
        "coordinates": {
            "resolved": len(resolved),
            "unresolved": len(points) - len(resolved),
            "location_coverage_pct": round(100 * len(resolved) / len(points), 4) if points else 0,
            "shipment_coverage_pct": (
                round(100 * resolved_shipments / total_shipments, 4) if total_shipments else 0
            ),
            "sources": dict(Counter(point.coordinate_source for point in points)),
        },
        "unresolved": unresolved,
        "contract": {
            "clustering_unit": (
                "unique destination FIAS"
                if not allow_name_fallback
                else "unique destination FIAS; explicit development name+region fallback"
            ),
            "name_region_fallback_enabled": allow_name_fallback,
            "shipment_count_source": "Pulse.units",
            "diagnostic_only": ["bid_count", "confidence"],
            "forecast_excluded_by_default": True,
            "clustering_features": ["projected_x", "projected_y"],
            "region_center_fallback": False,
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


def _csv_set(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=default_csv_path())
    parser.add_argument(
        "--coordinate-cache", type=Path, default=Path("backend/cache/coords_cache.json")
    )
    parser.add_argument("--destination-region")
    parser.add_argument("--origin-fias")
    parser.add_argument("--period-types", type=_csv_set, default=set())
    parser.add_argument("--price-types", type=_csv_set, default=set())
    parser.add_argument("--allow-name-fallback", action="store_true")
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
        allow_name_fallback=args.allow_name_fallback,
    )
    json_path, csv_path, audit_path = write_location_dataset(points, report, args.output_dir)
    print(
        f"Built {len(points)} locations; "
        f"coordinate coverage={report['coordinates']['location_coverage_pct']}%"
    )
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    print(f"Audit: {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
