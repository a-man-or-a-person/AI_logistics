"""Streaming loader for the current Pulse CSV export."""

from __future__ import annotations

import csv
import os
from collections.abc import Iterator
from pathlib import Path

from ml.data.schema import (
    LogisticsRecord,
    clean_text,
    parse_datetime,
    parse_float,
    parse_int,
)
from ml.data.validation import pulse_row_validation_errors

PULSE_COLUMNS = (
    "shipment_point_locality_fias_id",
    "shipment_point_region",
    "shipment_point_town_source",
    "shipment_point_name_town",
    "shipment_point_point_type",
    "shipment_point_address",
    "delivery_point_locality_fias_id",
    "delivery_point_region_source",
    "delivery_point_region_unified",
    "delivery_point_town",
    "delivery_point_address",
    "delivery_point_point_type",
    "period_id",
    "period_type",
    "bid_count",
    "confidence",
    "nanos",
    "units",
    "price_type",
    "route_length",
    "route_type",
    "tonnage_id",
    "vehicle_body_type",
    "currency",
    "tech_load_ts",
)

REQUIRED_PULSE_COLUMNS = frozenset(
    {
        "shipment_point_locality_fias_id",
        "shipment_point_region",
        "delivery_point_locality_fias_id",
        "delivery_point_region_unified",
        "delivery_point_town",
        "period_id",
        "period_type",
        "bid_count",
        "units",
        "price_type",
        "route_length",
    }
)


def default_csv_path() -> Path:
    configured = os.environ.get("LOGISTICS_CSV_FILE")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "v_pulse_prices.csv"


def _pulse_record(row: dict[str, str], source: str) -> LogisticsRecord:
    origin_name = clean_text(row.get("shipment_point_name_town"))
    if origin_name is None:
        origin_name = clean_text(row.get("shipment_point_town_source"))

    return LogisticsRecord(
        source=source,
        origin_fias=clean_text(row.get("shipment_point_locality_fias_id")),
        origin_name=origin_name,
        origin_region=clean_text(row.get("shipment_point_region")),
        destination_fias=clean_text(row.get("delivery_point_locality_fias_id")),
        destination_name=clean_text(row.get("delivery_point_town")),
        destination_region=clean_text(row.get("delivery_point_region_unified")),
        latitude=parse_float(row.get("latitude")),
        longitude=parse_float(row.get("longitude")),
        period_id=clean_text(row.get("period_id")),
        period_type=clean_text(row.get("period_type")),
        units=parse_float(row.get("units")),
        shipment_count=parse_float(row.get("units")),
        route_length=parse_float(row.get("route_length")),
        pulse_bid_count=parse_int(row.get("bid_count")),
        vehicle_type=clean_text(row.get("vehicle_body_type")),
        tonnage_id=clean_text(row.get("tonnage_id")),
        price_type=clean_text(row.get("price_type")),
        currency=clean_text(row.get("currency")),
        pulse_confidence=clean_text(row.get("confidence")),
        origin_town_source=clean_text(row.get("shipment_point_town_source")),
        origin_point_type=clean_text(row.get("shipment_point_point_type")),
        origin_address=clean_text(row.get("shipment_point_address")),
        destination_region_source=clean_text(row.get("delivery_point_region_source")),
        destination_address=clean_text(row.get("delivery_point_address")),
        destination_point_type=clean_text(row.get("delivery_point_point_type")),
        nanos=parse_int(row.get("nanos")),
        route_type=clean_text(row.get("route_type")),
        tech_ts=parse_datetime(row.get("tech_load_ts")),
        validation_errors=pulse_row_validation_errors(row),
    )


def iter_records(
    path: str | Path | None = None,
    *,
    source: str = "pulse",
    limit: int | None = None,
) -> Iterator[LogisticsRecord]:
    """Yield normalized records without loading the source CSV into memory."""
    csv_path = Path(path) if path is not None else default_csv_path()
    with csv_path.open(encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or ())
        missing = sorted(REQUIRED_PULSE_COLUMNS - headers)
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Pulse CSV is missing required columns: {joined}")

        for index, row in enumerate(reader):
            if limit is not None and index >= limit:
                break
            yield _pulse_record(row, source)
