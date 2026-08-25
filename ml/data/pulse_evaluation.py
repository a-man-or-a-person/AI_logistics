"""Temporal Pulse records retained for actual-price evaluation."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ml.data.loader import REQUIRED_PULSE_COLUMNS, default_csv_path
from ml.data.schema import clean_text, parse_float, parse_int


@dataclass(frozen=True, slots=True)
class PulseEvaluationRecord:
    origin_fias: str | None
    destination_fias: str | None
    destination_region: str | None
    period_id: str | None
    period_type: str | None
    price: float | None
    route_length: float | None
    bid_count: int | None
    price_type: str | None
    source_snapshot_time: str | None


def iter_pulse_evaluation_records(
    path: str | Path | None = None,
) -> list[PulseEvaluationRecord]:
    source_path = Path(path) if path is not None else default_csv_path()
    records: list[PulseEvaluationRecord] = []
    with source_path.open(encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or ())
        missing = sorted(REQUIRED_PULSE_COLUMNS - headers)
        if missing:
            raise ValueError(f"Pulse CSV is missing required columns: {', '.join(missing)}")
        for row in reader:
            records.append(
                PulseEvaluationRecord(
                    origin_fias=clean_text(row.get("shipment_point_locality_fias_id")),
                    destination_fias=clean_text(row.get("delivery_point_locality_fias_id")),
                    destination_region=clean_text(row.get("delivery_point_region_unified")),
                    period_id=clean_text(row.get("period_id")),
                    period_type=clean_text(row.get("period_type")),
                    price=parse_float(row.get("units")),
                    route_length=parse_float(row.get("route_length")),
                    bid_count=parse_int(row.get("bid_count")),
                    price_type=clean_text(row.get("price_type")),
                    source_snapshot_time=clean_text(row.get("tech_load_ts")),
                )
            )
    return records
