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

from ml.data.loader import default_csv_path, iter_records
from ml.data.schema import LogisticsRecord


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
        return {"count": 0, "min": None, "p25": None, "median": None, "p75": None, "p95": None, "max": None, "mean": None}
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "min": round(ordered[0], 4),
        "p25": round(_quantile(ordered, 0.25) or 0, 4),
        "median": round(_quantile(ordered, 0.5) or 0, 4),
        "p75": round(_quantile(ordered, 0.75) or 0, 4),
        "p95": round(_quantile(ordered, 0.95) or 0, 4),
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
        self.rows_by_destination_region: Counter[str] = Counter()
        self.destinations_by_region: dict[str, set[str]] = defaultdict(set)
        self.destination_fias: set[str] = set()
        self.origin_fias: set[str] = set()
        self.period_ids: set[str] = set()
        self.trip_count_by_destination: Counter[str] = Counter()
        self.row_count_by_destination: Counter[str] = Counter()
        self.rub_per_km: list[float] = []
        self.seen_fingerprints: set[bytes] = set()
        self.duplicate_rows = 0

    def add(self, record: LogisticsRecord) -> None:
        self.total_rows += 1
        fingerprint = record.fingerprint()
        if fingerprint in self.seen_fingerprints:
            self.duplicate_rows += 1
        else:
            self.seen_fingerprints.add(fingerprint)

        for field in (
            "origin_fias",
            "origin_name",
            "origin_region",
            "destination_fias",
            "destination_name",
            "destination_region",
            "latitude",
            "longitude",
            "period_id",
            "period_type",
            "price",
            "route_length",
            "trip_count",
        ):
            if getattr(record, field) is None:
                self.nulls[field] += 1

        if record.price is not None and record.price <= 0:
            self.invalids["price_le_zero"] += 1
        if record.route_length is not None and record.route_length <= 0:
            self.invalids["route_length_le_zero"] += 1
        if record.trip_count is not None and record.trip_count < 0:
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

        region = record.destination_region or "<missing>"
        self.rows_by_destination_region[region] += 1
        destination_key = record.destination_fias or (
            f"name:{record.destination_name or '<missing>'}|region:{region}"
        )
        self.destinations_by_region[region].add(destination_key)
        self.row_count_by_destination[destination_key] += 1
        if record.trip_count is not None and record.trip_count > 0:
            self.trip_count_by_destination[destination_key] += record.trip_count

        rub_per_km = record.rub_per_km
        if rub_per_km is not None:
            self.rub_per_km.append(rub_per_km)

    def report(self, *, source_path: Path, source: str) -> dict[str, Any]:
        total = self.total_rows
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
            },
            "entities": {
                "unique_origin_fias": len(self.origin_fias),
                "unique_destination_fias": len(self.destination_fias),
            },
            "periods": {
                "range": period_range,
                "types": dict(sorted(self.period_types.items())),
            },
            "price_types": dict(sorted(self.price_types.items())),
            "nulls": {
                key: {"count": count, "pct": _percent(count, total)}
                for key, count in sorted(self.nulls.items())
            },
            "invalid_values": dict(sorted(self.invalids.items())),
            "rub_per_km": _distribution(self.rub_per_km),
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
            "contract": {
                "rub_per_km_formula": "price / route_length for price > 0 and route_length > 0",
                "coordinate_status": "optional; expected to be joined by FIAS when absent",
                "duplicate_definition": "identical normalized business fields",
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
