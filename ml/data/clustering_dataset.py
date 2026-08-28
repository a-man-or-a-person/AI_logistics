"""Build the canonical one-origin, one-region clustering dataset."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ml.data.loader import default_csv_path, iter_records
from ml.data.schema import LogisticsRecord

CLUSTERING_ALLOWED_PERIOD_TYPES = frozenset({"retro", "current", "forecast"})


@dataclass(frozen=True, slots=True)
class ClusteringRoute:
    """One destination point after combining the selected Pulse segments."""

    origin_fias: str
    destination_fias: str
    destination_name: str
    destination_region: str
    record_count: int
    trip_count: int
    weighted_price: float | None
    weighted_rub_per_km: float | None
    active_period_count: int
    period_types: tuple[str, ...]
    price_types: tuple[str, ...]
    vehicle_types: tuple[str, ...]
    tonnage_ids: tuple[str, ...]
    data_quality_flags: tuple[str, ...]


@dataclass(slots=True)
class _Accumulator:
    names: Counter[str] = field(default_factory=Counter)
    record_count: int = 0
    trip_count: int = 0
    price_numerator: float = 0.0
    price_denominator: int = 0
    rubkm_numerator: float = 0.0
    rubkm_denominator: int = 0
    periods: set[str] = field(default_factory=set)
    period_types: set[str] = field(default_factory=set)
    price_types: set[str] = field(default_factory=set)
    vehicle_types: set[str] = field(default_factory=set)
    tonnage_ids: set[str] = field(default_factory=set)
    flags: set[str] = field(default_factory=set)

    def add(self, record: LogisticsRecord) -> None:
        self.record_count += 1
        if record.destination_name:
            self.names[record.destination_name] += 1
        if record.period_id:
            self.periods.add(record.period_id)
        if record.period_type:
            self.period_types.add(record.period_type)
        if record.price_type:
            self.price_types.add(record.price_type)
        if record.vehicle_type:
            self.vehicle_types.add(record.vehicle_type)
        if record.tonnage_id:
            self.tonnage_ids.add(record.tonnage_id)

        trips = record.trip_count
        if trips is None or trips <= 0:
            self.flags.add("missing_or_nonpositive_trip_count")
            return
        self.trip_count += trips
        if record.price is not None and record.price > 0:
            self.price_numerator += record.price * trips
            self.price_denominator += trips
        else:
            self.flags.add("missing_or_nonpositive_price")
        if record.rub_per_km is not None:
            self.rubkm_numerator += record.rub_per_km * trips
            self.rubkm_denominator += trips
        else:
            self.flags.add("invalid_price_or_route_length")


def _matches(value: str | None, selected: set[str]) -> bool:
    return not selected or value in selected


def _weighted(numerator: float, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator > 0 else None


def build_clustering_routes(
    path: str | Path | None = None,
    *,
    destination_region: str | None = None,
    origin_fias: str | None = None,
    period_types: set[str] | None = None,
    price_types: set[str] | None = None,
    vehicle_types: set[str] | None = None,
    tonnage_ids: set[str] | None = None,
) -> tuple[list[ClusteringRoute], dict[str, Any]]:
    """Aggregate destination economics with ``bid_count`` as the weight."""
    if not origin_fias:
        raise ValueError("A single origin_fias is required")
    if not destination_region:
        raise ValueError("A single destination_region is required")

    source_path = Path(path) if path is not None else default_csv_path()
    selected_periods = (
        set(period_types) if period_types is not None else set(CLUSTERING_ALLOWED_PERIOD_TYPES)
    )
    unsupported_periods = selected_periods - set(CLUSTERING_ALLOWED_PERIOD_TYPES)
    if unsupported_periods:
        raise ValueError(f"Unsupported period_types: {sorted(unsupported_periods)}")
    selected_prices = set(price_types or ())
    selected_vehicles = set(vehicle_types or ())
    selected_tonnages = set(tonnage_ids or ())

    raw_rows = filtered_rows = unusable_rows = 0
    accumulators: dict[str, _Accumulator] = {}
    for record in iter_records(source_path):
        raw_rows += 1
        if record.origin_fias != origin_fias or record.destination_region != destination_region:
            continue
        if not _matches(record.period_type, selected_periods):
            continue
        if not _matches(record.price_type, selected_prices):
            continue
        if not _matches(record.vehicle_type, selected_vehicles):
            continue
        if not _matches(record.tonnage_id, selected_tonnages):
            continue
        filtered_rows += 1
        if not record.destination_fias:
            unusable_rows += 1
            continue
        accumulators.setdefault(record.destination_fias, _Accumulator()).add(record)

    routes: list[ClusteringRoute] = []
    for destination_fias, accumulator in accumulators.items():
        name = accumulator.names.most_common(1)[0][0] if accumulator.names else "<missing>"
        routes.append(
            ClusteringRoute(
                origin_fias=origin_fias,
                destination_fias=destination_fias,
                destination_name=name,
                destination_region=destination_region,
                record_count=accumulator.record_count,
                trip_count=accumulator.trip_count,
                weighted_price=_weighted(
                    accumulator.price_numerator, accumulator.price_denominator
                ),
                weighted_rub_per_km=_weighted(
                    accumulator.rubkm_numerator, accumulator.rubkm_denominator
                ),
                active_period_count=len(accumulator.periods),
                period_types=tuple(sorted(accumulator.period_types)),
                price_types=tuple(sorted(accumulator.price_types)),
                vehicle_types=tuple(sorted(accumulator.vehicle_types)),
                tonnage_ids=tuple(sorted(accumulator.tonnage_ids)),
                data_quality_flags=tuple(sorted(accumulator.flags)),
            )
        )
    routes.sort(key=lambda row: row.destination_fias)

    observed_periods = sorted({value for route in routes for value in route.period_types})
    observed_prices = sorted({value for route in routes for value in route.price_types})
    observed_vehicles = sorted({value for route in routes for value in route.vehicle_types})
    observed_tonnages = sorted({value for route in routes for value in route.tonnage_ids})
    report = {
        "source_path": str(source_path.resolve()),
        "raw_rows": raw_rows,
        "filtered_source_rows": filtered_rows,
        "unusable_rows_excluded": unusable_rows,
        "excluded_missing_fias_rows": unusable_rows,
        "canonical_destination_rows": len(routes),
        "trip_count_total": sum(route.trip_count for route in routes),
        "filters": {
            "origin_fias": origin_fias,
            "destination_region": destination_region,
            "period_types": sorted(selected_periods),
            "price_types": sorted(selected_prices),
            "vehicle_types": sorted(selected_vehicles),
            "tonnage_ids": sorted(selected_tonnages),
        },
        "metadata": {
            "contains_forecast": "forecast" in observed_periods,
            "mixed_price_types": len(observed_prices) > 1,
            "mixed_vehicle_types": len(observed_vehicles) > 1,
            "mixed_tonnages": len(observed_tonnages) > 1,
            "observed_period_types": observed_periods,
            "observed_price_types": observed_prices,
            "observed_vehicle_types": observed_vehicles,
            "observed_tonnage_ids": observed_tonnages,
        },
        "contract": {
            "version": "clustering-contract-v1",
            "grain": "one origin_fias x one destination_region x destination_fias",
            "price_source": "Pulse.units",
            "trip_count_source": "Pulse.bid_count",
            "rub_per_km": "price / route_length for positive values",
            "economic_weight": "trip_count",
        },
    }
    return routes, report


def write_clustering_routes(
    routes: list[ClusteringRoute], report: dict[str, Any], output_dir: str | Path
) -> tuple[Path, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    routes_path = destination / "routes.csv"
    audit_path = destination / "audit.json"
    fields = list(asdict(routes[0])) if routes else ["origin_fias", "destination_fias"]
    with routes_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(asdict(route) for route in routes)
    audit_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return routes_path, audit_path


def _csv_set(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=default_csv_path())
    parser.add_argument("--output-dir", type=Path, default=Path("reports/clustering_data"))
    parser.add_argument("--destination-region", required=True)
    parser.add_argument("--origin-fias", required=True)
    parser.add_argument("--period-types", type=_csv_set)
    parser.add_argument("--price-types", type=_csv_set)
    parser.add_argument("--vehicle-types", type=_csv_set)
    parser.add_argument("--tonnage-ids", type=_csv_set)
    parser.add_argument(
        "--coordinate-cache", type=Path, default=Path("backend/cache/coords_cache.json")
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    filters = {
        "destination_region": args.destination_region,
        "origin_fias": args.origin_fias,
        "period_types": args.period_types,
        "price_types": args.price_types,
        "vehicle_types": args.vehicle_types,
        "tonnage_ids": args.tonnage_ids,
    }
    routes, report = build_clustering_routes(args.path, **filters)
    routes_path, audit_path = write_clustering_routes(routes, report, args.output_dir)
    from ml.data.locations import build_location_dataset, write_location_dataset

    locations, location_report = build_location_dataset(
        args.path, coordinate_cache_path=args.coordinate_cache, **filters
    )
    _, locations_path, _ = write_location_dataset(locations, location_report, args.output_dir)
    report["coordinates"] = location_report["coordinates"]
    _, audit_path = write_clustering_routes(routes, report, args.output_dir)
    print(f"Routes: {routes_path}")
    print(f"Locations: {locations_path}")
    print(f"Audit: {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
