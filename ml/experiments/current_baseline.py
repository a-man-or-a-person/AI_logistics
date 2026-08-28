"""Reproduce the current Pulse rate calculation outside production code."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ml.data.loader import default_csv_path
from ml.data.pulse_evaluation import PulseEvaluationRecord, iter_pulse_evaluation_records


@dataclass(slots=True)
class RateAccumulator:
    record_count: int = 0
    trip_count: int = 0
    price_sum: float = 0.0
    distance_sum: float = 0.0
    weighted_price_sum: float = 0.0
    weighted_distance_sum: float = 0.0

    def add(self, record: PulseEvaluationRecord) -> None:
        if record.price is None or record.route_length is None:
            return
        if record.price <= 0 or record.route_length <= 0:
            return
        trips = max(record.bid_count or 0, 0)
        self.record_count += 1
        self.trip_count += trips
        self.price_sum += record.price
        self.distance_sum += record.route_length
        self.weighted_price_sum += record.price * trips
        self.weighted_distance_sum += record.route_length * trips

    def as_dict(self) -> dict[str, int | float | None]:
        backend_rate = self.price_sum / self.distance_sum if self.distance_sum else None
        trip_weighted_rate = (
            self.weighted_price_sum / self.weighted_distance_sum
            if self.weighted_distance_sum
            else None
        )
        return {
            "record_count": self.record_count,
            "trip_count": self.trip_count,
            "backend_compatible_rub_per_km": _round(backend_rate),
            "trip_weighted_rub_per_km": _round(trip_weighted_rate),
            "mean_price": _round(self.price_sum / self.record_count if self.record_count else None),
            "mean_route_length": _round(
                self.distance_sum / self.record_count if self.record_count else None
            ),
        }


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def _matches(
    record: PulseEvaluationRecord,
    *,
    destination_region: str | None,
    origin_fias: str | None,
    period_types: set[str],
    price_types: set[str],
) -> bool:
    return not (
        (destination_region and record.destination_region != destination_region)
        or (origin_fias and record.origin_fias != origin_fias)
        or (period_types and record.period_type not in period_types)
        or (price_types and record.price_type not in price_types)
    )


def calculate_baseline(
    path: str | Path | None = None,
    *,
    destination_region: str | None = None,
    origin_fias: str | None = None,
    period_types: set[str] | None = None,
    price_types: set[str] | None = None,
) -> dict[str, Any]:
    """Calculate both production-compatible and trip-weighted Pulse baselines."""
    source_path = Path(path) if path is not None else default_csv_path()
    selected_period_types = period_types or set()
    selected_price_types = price_types or set()
    overall = RateAccumulator()
    by_period: dict[str, RateAccumulator] = defaultdict(RateAccumulator)
    by_origin: dict[tuple[str, str], RateAccumulator] = defaultdict(RateAccumulator)
    by_destination: dict[tuple[str, str], RateAccumulator] = defaultdict(RateAccumulator)

    for record in iter_pulse_evaluation_records(source_path):
        if not _matches(
            record,
            destination_region=destination_region,
            origin_fias=origin_fias,
            period_types=selected_period_types,
            price_types=selected_price_types,
        ):
            continue
        overall.add(record)
        period_key = record.period_id or "<missing>"
        by_period[period_key].add(record)
        origin_key = (record.origin_fias or "<missing>", record.origin_name or "<missing>")
        by_origin[origin_key].add(record)
        destination_key = (
            record.destination_fias or "<missing>",
            record.destination_name or "<missing>",
        )
        by_destination[destination_key].add(record)

    return {
        "source_path": str(source_path.resolve()),
        "filters": {
            "destination_region": destination_region,
            "origin_fias": origin_fias,
            "period_types": sorted(selected_period_types),
            "price_types": sorted(selected_price_types),
        },
        "methodology": {
            "backend_compatible_rub_per_km": "sum(price) / sum(route_length)",
            "trip_weighted_rub_per_km": (
                "sum(price * trip_count) / sum(route_length * trip_count)"
            ),
            "valid_row": "price > 0 and route_length > 0",
        },
        "overall": overall.as_dict(),
        "by_period": {
            period: accumulator.as_dict()
            for period, accumulator in sorted(by_period.items())
        },
        "by_origin": [
            {"origin_fias": key[0], "origin_name": key[1], **accumulator.as_dict()}
            for key, accumulator in sorted(
                by_origin.items(), key=lambda item: item[1].record_count, reverse=True
            )
        ],
        "by_destination": [
            {
                "destination_fias": key[0],
                "destination_name": key[1],
                **accumulator.as_dict(),
            }
            for key, accumulator in sorted(
                by_destination.items(), key=lambda item: item[1].record_count, reverse=True
            )
        ],
    }


def write_baseline(report: dict[str, Any], output_dir: str | Path = "reports") -> tuple[Path, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "current_baseline.json"
    csv_path = destination / "current_baseline.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows: list[dict[str, Any]] = []
    for dimension in ("by_period", "by_origin", "by_destination"):
        values = report[dimension]
        if isinstance(values, dict):
            values = [{"period_id": key, **value} for key, value in values.items()]
        for value in values:
            rows.append({"dimension": dimension, **value})
    fieldnames = [
        "dimension",
        "period_id",
        "origin_fias",
        "origin_name",
        "destination_fias",
        "destination_name",
        "record_count",
        "trip_count",
        "backend_compatible_rub_per_km",
        "trip_weighted_rub_per_km",
        "mean_price",
        "mean_route_length",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return json_path, csv_path


def _csv_set(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=default_csv_path())
    parser.add_argument("--destination-region")
    parser.add_argument("--origin-fias")
    parser.add_argument("--period-types", type=_csv_set, default=set())
    parser.add_argument("--price-types", type=_csv_set, default=set())
    parser.add_argument("--output-dir", type=Path, default=Path("reports"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = calculate_baseline(
        args.path,
        destination_region=args.destination_region,
        origin_fias=args.origin_fias,
        period_types=args.period_types,
        price_types=args.price_types,
    )
    json_path, csv_path = write_baseline(report, args.output_dir)
    print(f"Included {report['overall']['record_count']} valid rows")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
