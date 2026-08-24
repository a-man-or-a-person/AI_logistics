"""Test Pulse rates against internal route distances (decision gate 1)."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ml.data.internal import iter_internal_trips
from ml.data.loader import default_csv_path, iter_records
from ml.data.schema import LogisticsRecord


@dataclass(slots=True)
class PulseCell:
    price_sum: float = 0
    distance_sum: float = 0
    weighted_price_sum: float = 0
    weighted_distance_sum: float = 0
    trip_count: int = 0

    def add(self, record: LogisticsRecord) -> None:
        if record.price is None or record.route_length is None:
            return
        if record.price <= 0 or record.route_length <= 0:
            return
        trips = max(record.trip_count or 0, 0)
        self.price_sum += record.price
        self.distance_sum += record.route_length
        self.weighted_price_sum += record.price * trips
        self.weighted_distance_sum += record.route_length * trips
        self.trip_count += trips

    def rate(self, method: str) -> float | None:
        if method == "backend_compatible":
            return self.price_sum / self.distance_sum if self.distance_sum else None
        return (
            self.weighted_price_sum / self.weighted_distance_sum
            if self.weighted_distance_sum
            else None
        )

    def mean_price(self) -> float | None:
        return self.weighted_price_sum / self.trip_count if self.trip_count else None


def _metrics(predictions: list[dict[str, Any]], field: str) -> dict[str, float | int | None]:
    comparable = [
        row
        for row in predictions
        if row.get(field) is not None
        and row.get("reference_price") is not None
        and row["reference_price"] > 0
    ]
    if not comparable:
        return {"rows": 0, "wape_pct": None, "median_absolute_pct_difference": None}
    weighted_absolute_error = sum(
        abs(row[field] - row["reference_price"]) * row["weight"] for row in comparable
    )
    weighted_reference = sum(row["reference_price"] * row["weight"] for row in comparable)
    absolute_percentages = [
        100 * abs(row[field] - row["reference_price"]) / row["reference_price"]
        for row in comparable
    ]
    return {
        "rows": len(comparable),
        "wape_pct": round(100 * weighted_absolute_error / weighted_reference, 4),
        "median_absolute_pct_difference": round(statistics.median(absolute_percentages), 4),
    }


def evaluate_distance_hypothesis(
    pulse_path: str | Path,
    internal_path: str | Path,
    *,
    destination_region: str | None = None,
    origin_fias: str | None = None,
    rate_method: str = "trip_weighted",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if rate_method not in {"backend_compatible", "trip_weighted"}:
        raise ValueError("rate_method must be backend_compatible or trip_weighted")

    cells: dict[tuple[str, str], PulseCell] = defaultdict(PulseCell)
    overall = PulseCell()
    for record in iter_records(pulse_path):
        if destination_region and record.destination_region != destination_region:
            continue
        if origin_fias and record.origin_fias != origin_fias:
            continue
        if not record.destination_region or not record.period_id:
            continue
        cells[(record.destination_region, record.period_id)].add(record)
        overall.add(record)

    internal_rows = [
        trip
        for trip in iter_internal_trips(internal_path)
        if (not destination_region or trip.destination_region == destination_region)
        and (not origin_fias or trip.origin_fias == origin_fias)
    ]
    global_rate = overall.rate(rate_method)
    current_pulse_price = overall.mean_price()
    valid_distances = [
        trip for trip in internal_rows if trip.route_length is not None and trip.route_length > 0
    ]
    distance_weight = sum(max(trip.trip_count or 0, 1) for trip in valid_distances)
    weighted_distance = (
        sum(trip.route_length * max(trip.trip_count or 0, 1) for trip in valid_distances)
        / distance_weight
        if distance_weight
        else None
    )
    variant_b_price = (
        global_rate * weighted_distance
        if global_rate is not None and weighted_distance is not None
        else None
    )

    predictions: list[dict[str, Any]] = []
    matched = 0
    for trip in internal_rows:
        cell = cells.get((trip.destination_region or "", trip.period_id or ""))
        cell_rate = cell.rate(rate_method) if cell else None
        adjusted_c = (
            cell_rate * trip.route_length
            if cell_rate is not None and trip.route_length is not None and trip.route_length > 0
            else None
        )
        if adjusted_c is not None:
            matched += 1
        predictions.append(
            {
                "origin_fias": trip.origin_fias,
                "destination_fias": trip.destination_fias,
                "destination_region": trip.destination_region,
                "period_id": trip.period_id,
                "route_length": trip.route_length,
                "weight": max(trip.trip_count or 0, 1),
                "reference_price": trip.reference_price,
                "current_pulse_price": current_pulse_price,
                "adjusted_b_price": variant_b_price,
                "adjusted_c_price": adjusted_c,
                "pulse_rub_per_km": cell_rate,
            }
        )

    total = len(internal_rows)
    report = {
        "inputs": {
            "pulse_path": str(Path(pulse_path).resolve()),
            "internal_path": str(Path(internal_path).resolve()),
            "destination_region": destination_region,
            "origin_fias": origin_fias,
            "rate_method": rate_method,
        },
        "coverage": {
            "internal_rows": total,
            "matched_rows": matched,
            "matched_pct": round(100 * matched / total, 4) if total else 0,
        },
        "variants": {
            "current_pulse": {
                "description": "Pulse trip-weighted mean price",
                "aggregate_price": round(current_pulse_price, 4) if current_pulse_price else None,
                "metrics": _metrics(predictions, "current_pulse_price"),
            },
            "adjusted_b": {
                "description": "Pulse regional ₽/km × internal weighted mean distance",
                "aggregate_price": round(variant_b_price, 4) if variant_b_price else None,
                "metrics": _metrics(predictions, "adjusted_b_price"),
            },
            "adjusted_c": {
                "description": "Pulse period/region ₽/km × each internal route distance",
                "metrics": _metrics(predictions, "adjusted_c_price"),
            },
        },
        "decision_gate": {
            "ready": total > 0 and matched == total and any(
                row["reference_price"] is not None for row in predictions
            ),
            "rule": "Review WAPE across multiple periods before spatial clustering",
        },
    }
    return report, predictions


def write_results(
    report: dict[str, Any],
    predictions: list[dict[str, Any]],
    output_dir: str | Path = "reports/hypothesis_1",
) -> tuple[Path, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "metrics.json"
    csv_path = destination / "predictions.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fieldnames = list(predictions[0]) if predictions else ["no_predictions"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(predictions)
    return json_path, csv_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pulse", type=Path, default=default_csv_path())
    parser.add_argument("--internal", type=Path, required=True)
    parser.add_argument("--destination-region")
    parser.add_argument("--origin-fias")
    parser.add_argument(
        "--rate-method",
        choices=("backend_compatible", "trip_weighted"),
        default="trip_weighted",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("reports/hypothesis_1"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report, predictions = evaluate_distance_hypothesis(
        args.pulse,
        args.internal,
        destination_region=args.destination_region,
        origin_fias=args.origin_fias,
        rate_method=args.rate_method,
    )
    json_path, csv_path = write_results(report, predictions, args.output_dir)
    print(f"Matched {report['coverage']['matched_rows']} of {report['coverage']['internal_rows']} rows")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
