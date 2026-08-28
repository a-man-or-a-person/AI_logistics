"""Generate reproducible quality reports for logistics source data."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ml.data.loader import PULSE_COLUMNS, default_csv_path, iter_records
from ml.data.schema import LogisticsRecord
from ml.data.validation import CLUSTERING_FIELD_POLICY

AUDITED_FIELDS = (
    "origin_fias",
    "origin_name",
    "origin_town_source",
    "origin_region",
    "origin_point_type",
    "origin_address",
    "destination_fias",
    "destination_name",
    "destination_region",
    "destination_region_source",
    "destination_address",
    "destination_point_type",
    "latitude",
    "longitude",
    "period_id",
    "period_type",
    "price",
    "route_length",
    "trip_count",
    "nanos",
    "route_type",
    "vehicle_type",
    "tonnage_id",
    "price_type",
    "currency",
    "confidence",
    "tech_ts",
)

CARDINALITY_FIELDS = (
    "origin_fias",
    "destination_fias",
    "origin_region",
    "destination_region",
    "period_id",
    "period_type",
    "route_type",
    "vehicle_type",
    "tonnage_id",
    "price_type",
    "currency",
)


def _percent(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 4) if denominator else 0.0


def _quantile(sorted_values: list[float], fraction: float) -> float | None:
    if not sorted_values:
        return None
    position = (len(sorted_values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _distribution(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "p01": None,
            "p05": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p95": None,
            "p99": None,
            "max": None,
            "mean": None,
        }
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "min": round(ordered[0], 4),
        "p01": round(_quantile(ordered, 0.01) or 0, 4),
        "p05": round(_quantile(ordered, 0.05) or 0, 4),
        "p25": round(_quantile(ordered, 0.25) or 0, 4),
        "median": round(_quantile(ordered, 0.5) or 0, 4),
        "p75": round(_quantile(ordered, 0.75) or 0, 4),
        "p95": round(_quantile(ordered, 0.95) or 0, 4),
        "p99": round(_quantile(ordered, 0.99) or 0, 4),
        "max": round(ordered[-1], 4),
        "mean": round(sum(ordered) / len(ordered), 4),
    }


class AuditAccumulator:
    def __init__(self) -> None:
        self.total_rows = 0
        self.nulls: Counter[str] = Counter()
        self.invalids: Counter[str] = Counter()
        self.period_types: Counter[str] = Counter()
        self.price_types: Counter[str] = Counter()
        self.currencies: Counter[str] = Counter()
        self.route_types: Counter[str] = Counter()
        self.vehicle_types: Counter[str] = Counter()
        self.tonnage_ids: Counter[str] = Counter()
        self.rows_by_destination_region: Counter[str] = Counter()
        self.destinations_by_region: dict[str, set[str]] = defaultdict(set)
        self.destination_fias: set[str] = set()
        self.origin_fias: set[str] = set()
        self.period_ids: set[str] = set()
        self.unique_values: dict[str, set[object]] = {
            field: set() for field in CARDINALITY_FIELDS
        }
        self.trip_count_by_destination: Counter[str] = Counter()
        self.row_count_by_destination: Counter[str] = Counter()
        self.row_count_by_route: Counter[str] = Counter()
        self.periods_by_route: dict[str, set[str]] = defaultdict(set)
        self.prices: list[float] = []
        self.rub_per_km: list[float] = []
        self.trip_counts: list[float] = []
        self.route_length: list[float] = []
        self.tech_timestamps: list[str] = []
        self.validation_errors: Counter[str] = Counter()
        self.seen_fingerprints: set[bytes] = set()
        self.seen_business_keys: set[tuple[object, ...]] = set()
        self.duplicate_rows = 0
        self.duplicate_business_keys = 0

    def add(self, record: LogisticsRecord) -> None:
        self.total_rows += 1
        fingerprint = record.fingerprint()
        if fingerprint in self.seen_fingerprints:
            self.duplicate_rows += 1
        else:
            self.seen_fingerprints.add(fingerprint)

        business_key = (
            record.origin_fias,
            record.destination_fias,
            record.period_id,
            record.period_type,
            record.price_type,
            record.route_type,
            record.tonnage_id,
            record.vehicle_type,
            record.currency,
        )
        if business_key in self.seen_business_keys:
            self.duplicate_business_keys += 1
        else:
            self.seen_business_keys.add(business_key)

        for field in AUDITED_FIELDS:
            if getattr(record, field) is None:
                self.nulls[field] += 1

        self.validation_errors.update(record.validation_errors)

        if record.price is not None:
            self.prices.append(record.price)
            if record.price < 0:
                self.invalids["price_negative"] += 1
        if record.rub_per_km is not None:
            self.rub_per_km.append(record.rub_per_km)
        if record.route_length is not None:
            self.route_length.append(record.route_length)
            if record.route_length == 0:
                self.invalids["route_length_zero"] += 1
            elif record.route_length < 0:
                self.invalids["route_length_negative"] += 1
        if record.trip_count is not None:
            self.trip_counts.append(float(record.trip_count))
            if record.trip_count < 0:
                self.invalids["trip_count_lt_zero"] += 1

        if record.origin_fias:
            self.origin_fias.add(record.origin_fias)
        if record.destination_fias:
            self.destination_fias.add(record.destination_fias)
        if record.period_id:
            self.period_ids.add(record.period_id)
        if record.period_type:
            self.period_types[record.period_type] += 1
        if record.price_type:
            self.price_types[record.price_type] += 1
        if record.currency:
            self.currencies[record.currency] += 1
        if record.route_type:
            self.route_types[record.route_type] += 1
        if record.vehicle_type:
            self.vehicle_types[record.vehicle_type] += 1
        if record.tonnage_id:
            self.tonnage_ids[record.tonnage_id] += 1
        if record.tech_ts is not None:
            self.tech_timestamps.append(record.tech_ts.isoformat())
        for field in CARDINALITY_FIELDS:
            value = getattr(record, field)
            if value is not None:
                self.unique_values[field].add(value)

        region = record.destination_region or "<missing>"
        self.rows_by_destination_region[region] += 1
        destination_key = record.destination_fias or (
            f"name:{record.destination_name or '<missing>'}|region:{region}"
        )
        self.destinations_by_region[region].add(destination_key)
        self.row_count_by_destination[destination_key] += 1
        origin_key = record.origin_fias or (
            f"name:{record.origin_name or record.origin_town_source or '<missing>'}"
        )
        route_key = f"{origin_key}->{destination_key}"
        self.row_count_by_route[route_key] += 1
        if record.period_id:
            self.periods_by_route[route_key].add(record.period_id)
        if record.trip_count is not None and record.trip_count > 0:
            self.trip_count_by_destination[destination_key] += record.trip_count

    def report(self, *, source_path: Path, source: str) -> dict[str, Any]:
        total = self.total_rows
        route_month_counts = [len(periods) for periods in self.periods_by_route.values()]
        period_range = {
            "min": min(self.period_ids) if self.period_ids else None,
            "max": max(self.period_ids) if self.period_ids else None,
        }
        return {
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "source": source,
            "source_path": str(source_path.resolve()),
            "source_size_bytes": source_path.stat().st_size,
            "rows": {
                "total": total,
                "unique": total - self.duplicate_rows,
                "duplicates": self.duplicate_rows,
                "duplicate_pct": _percent(self.duplicate_rows, total),
                "duplicate_candidate_business_keys": self.duplicate_business_keys,
                "duplicate_candidate_business_key_pct": _percent(
                    self.duplicate_business_keys, total
                ),
            },
            "schema": {
                "source_column_count": len(PULSE_COLUMNS),
                "source_columns": list(PULSE_COLUMNS),
                "canonical_field_count": len(AUDITED_FIELDS),
                "canonical_fields": list(AUDITED_FIELDS),
            },
            "entities": {
                "unique_origin_fias": len(self.origin_fias),
                "unique_destination_fias": len(self.destination_fias),
                "unique_routes": len(self.row_count_by_route),
            },
            "periods": {
                "range": period_range,
                "count": len(self.period_ids),
                "types": dict(sorted(self.period_types.items())),
                "tech_ts_range": {
                    "min": min(self.tech_timestamps) if self.tech_timestamps else None,
                    "max": max(self.tech_timestamps) if self.tech_timestamps else None,
                },
            },
            "price_types": dict(sorted(self.price_types.items())),
            "currencies": dict(sorted(self.currencies.items())),
            "route_types": dict(sorted(self.route_types.items())),
            "vehicle_types": dict(sorted(self.vehicle_types.items())),
            "tonnage_ids": dict(sorted(self.tonnage_ids.items())),
            "cardinality": {
                field: len(values) for field, values in self.unique_values.items()
            },
            "nulls": {
                field: {
                    "count": self.nulls[field],
                    "pct": _percent(self.nulls[field], total),
                }
                for field in AUDITED_FIELDS
            },
            "invalid_values": dict(sorted(self.invalids.items())),
            "parse_errors": dict(sorted(self.validation_errors.items())),
            "price": _distribution(self.prices),
            "rub_per_km": _distribution(self.rub_per_km),
            "trip_count": _distribution(self.trip_counts),
            "route_length": _distribution(self.route_length),
            "destination_regions": {
                region: {
                    "rows": count,
                    "unique_destinations": len(self.destinations_by_region[region]),
                }
                for region, count in self.rows_by_destination_region.most_common()
            },
            "trips_per_destination": _distribution(
                [float(value) for value in self.trip_count_by_destination.values()]
            ),
            "rows_per_destination": _distribution(
                [float(value) for value in self.row_count_by_destination.values()]
            ),
            "route_history": {
                "rows_per_route": _distribution(
                    [float(value) for value in self.row_count_by_route.values()]
                ),
                "months_per_route": _distribution(
                    [float(value) for value in route_month_counts]
                ),
                "routes_seen_1_month": sum(value == 1 for value in route_month_counts),
                "routes_seen_ge_3_months": sum(value >= 3 for value in route_month_counts),
                "routes_seen_ge_6_months": sum(value >= 6 for value in route_month_counts),
                "routes_seen_ge_12_months": sum(value >= 12 for value in route_month_counts),
            },
            "contract": {
                "coordinate_status": "optional; expected to be joined by FIAS when absent",
                "duplicate_definition": "identical normalized business fields",
                "candidate_business_key": (
                    "origin_fias + destination_fias + period_id + period_type + price_type + "
                    "route_type + tonnage_id + vehicle_type + currency"
                ),
                "row_grain_status": "candidate_only_pending_business_confirmation",
            },
            "clustering": {
                "status": "current_milestone",
                "feature_policy": CLUSTERING_FIELD_POLICY,
                "price_source": "Pulse.units",
                "trip_count_source": "Pulse.bid_count",
                "period_policy": "retro/current/forecast selectable",
            },
        }


def audit_file(
    path: str | Path | None = None,
    *,
    source: str = "pulse",
    limit: int | None = None,
) -> dict[str, Any]:
    source_path = Path(path) if path is not None else default_csv_path()
    accumulator = AuditAccumulator()
    for record in iter_records(source_path, source=source, limit=limit):
        accumulator.add(record)
    return accumulator.report(source_path=source_path, source=source)


def _flatten(value: Any, prefix: str = "") -> list[tuple[str, str, Any]]:
    rows: list[tuple[str, str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(_flatten(child, path))
    elif isinstance(value, list):
        rows.append((prefix.rpartition(".")[0], prefix.rpartition(".")[2], json.dumps(value)))
    else:
        section, _, metric = prefix.rpartition(".")
        rows.append((section, metric or prefix, value))
    return rows


def write_reports(report: dict[str, Any], output_dir: str | Path = "reports") -> tuple[Path, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "data_audit.json"
    csv_path = destination / "data_audit.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("section", "metric", "value"))
        writer.writerows(_flatten(report))
    return json_path, csv_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=default_csv_path())
    parser.add_argument("--source", default="pulse")
    parser.add_argument("--output-dir", type=Path, default=Path("reports"))
    parser.add_argument("--limit", type=int, default=None, help="Audit only the first N rows")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = audit_file(args.path, source=args.source, limit=args.limit)
    json_path, csv_path = write_reports(report, args.output_dir)
    print(f"Audited {report['rows']['total']} rows")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
