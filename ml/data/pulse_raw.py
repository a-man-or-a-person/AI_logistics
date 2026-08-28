"""Literal, interpretation-free contract for the 25-column Pulse export."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ml.data.loader import PULSE_COLUMNS, REQUIRED_PULSE_COLUMNS, default_csv_path
from ml.data.schema import clean_text


@dataclass(frozen=True, slots=True)
class PulseRawRecord:
    shipment_point_locality_fias_id: str | None
    shipment_point_region: str | None
    shipment_point_town_source: str | None
    shipment_point_name_town: str | None
    shipment_point_point_type: str | None
    shipment_point_address: str | None
    delivery_point_locality_fias_id: str | None
    delivery_point_region_source: str | None
    delivery_point_region_unified: str | None
    delivery_point_town: str | None
    delivery_point_address: str | None
    delivery_point_point_type: str | None
    period_id: str | None
    period_type: str | None
    bid_count: str | None
    confidence: str | None
    nanos: str | None
    units: str | None
    price_type: str | None
    route_length: str | None
    route_type: str | None
    tonnage_id: str | None
    vehicle_body_type: str | None
    currency: str | None
    tech_load_ts: str | None


def iter_raw_records(path: str | Path | None = None):
    """Yield source values without assigning unconfirmed business meaning."""
    source_path = Path(path) if path is not None else default_csv_path()
    with source_path.open(encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or ())
        missing = sorted(REQUIRED_PULSE_COLUMNS - headers)
        if missing:
            raise ValueError(f"Pulse CSV is missing required columns: {', '.join(missing)}")
        for row in reader:
            yield PulseRawRecord(**{column: clean_text(row.get(column)) for column in PULSE_COLUMNS})
