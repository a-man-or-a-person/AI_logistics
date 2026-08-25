"""Contract and validated streaming loader for confidential actual snapshots."""

from __future__ import annotations

import csv
import hashlib
import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ml.data.schema import clean_text, parse_float

ACTUAL_COLUMNS = (
    "current_month",
    "shipment_date_month",
    "month_label",
    "shipment_point_name",
    "shipment_point_name_town",
    "delivery_point_name",
    "qty_total",
    "net_weight_total",
    "qty_auction",
    "auction_percent",
    "fact_rub_total",
    "market_rub_total",
    "fact_rub_per_item",
    "market_rub_per_item",
    "market_spread",
    "tech_load_ts",
    "filename",
    "tech_load_ts_core",
)
REQUIRED_ACTUAL_COLUMNS = frozenset(ACTUAL_COLUMNS)


@dataclass(frozen=True, slots=True)
class ActualSnapshotRecord:
    snapshot_month: str
    shipment_month: str
    horizon_months: int
    month_label: str
    origin_external_name: str
    origin_town: str | None
    destination_region: str
    qty_total: float | None
    net_weight_total: float | None
    qty_auction: float | None
    auction_percent: float | None
    fact_rub_total: float | None
    fact_rub_per_item: float | None
    market_rub_total: float | None
    market_rub_per_item: float | None
    market_spread: float | None
    tech_load_ts: str | None
    source_filename: str | None
    source_loaded_at: str | None
    source: str = "actual_sibur"
    market_source: str = "ati_embedded"

    @property
    def actual_origin_id(self) -> str:
        return stable_origin_id(self.origin_external_name)


def default_actual_path() -> Path:
    configured = os.environ.get("LOGISTICS_ACTUAL_FILE")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "v_fact_sibur_actual.csv"


def stable_origin_id(origin_external_name: str) -> str:
    digest = hashlib.blake2b(
        f"actual-origin\x1f{origin_external_name.strip()}".encode(), digest_size=12
    ).hexdigest()
    return f"actual_{digest}"


def parse_month(value: object) -> str:
    normalized = clean_text(value)
    if normalized is None:
        raise ValueError("month is missing")
    for pattern in ("%Y-%m", "%Y%m", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, pattern).strftime("%Y-%m")
        except ValueError:
            pass
    raise ValueError(f"invalid month format: {normalized!r}")


def month_difference(shipment_month: str, snapshot_month: str) -> int:
    shipment_year, shipment_value = (int(part) for part in shipment_month.split("-"))
    snapshot_year, snapshot_value = (int(part) for part in snapshot_month.split("-"))
    return (shipment_year - snapshot_year) * 12 + shipment_value - snapshot_value


def format_month_label(horizon_months: int) -> str:
    return f"M{horizon_months}"


def _non_negative(name: str, value: float | None, row_number: int) -> None:
    if value is not None and value < 0:
        raise ValueError(f"actual row {row_number}: {name} must be non-negative")


def _validate_price_consistency(record: ActualSnapshotRecord, row_number: int, tolerance: float) -> None:
    if (
        record.qty_total is None
        or record.qty_total <= 0
        or record.fact_rub_total is None
        or record.fact_rub_per_item is None
        or record.fact_rub_per_item <= 0
    ):
        return
    calculated = record.fact_rub_total / record.qty_total
    relative_error = abs(calculated - record.fact_rub_per_item) / record.fact_rub_per_item
    if relative_error > tolerance:
        raise ValueError(
            f"actual row {row_number}: fact total/per-item mismatch exceeds {tolerance:.1%}"
        )


def _record(row: dict[str, str], row_number: int, fact_tolerance: float) -> ActualSnapshotRecord:
    snapshot_month = parse_month(row.get("current_month"))
    shipment_month = parse_month(row.get("shipment_date_month"))
    horizon = month_difference(shipment_month, snapshot_month)
    month_label = clean_text(row.get("month_label")) or ""
    expected_label = format_month_label(horizon)
    if month_label != expected_label:
        raise ValueError(
            f"actual row {row_number}: month_label {month_label!r} does not match {expected_label!r}"
        )

    origin = clean_text(row.get("shipment_point_name"))
    destination = clean_text(row.get("delivery_point_name"))
    if origin is None or destination is None:
        raise ValueError(f"actual row {row_number}: origin and destination region are required")

    record = ActualSnapshotRecord(
        snapshot_month=snapshot_month,
        shipment_month=shipment_month,
        horizon_months=horizon,
        month_label=month_label,
        origin_external_name=origin,
        origin_town=clean_text(row.get("shipment_point_name_town")),
        destination_region=destination,
        qty_total=parse_float(row.get("qty_total")),
        net_weight_total=parse_float(row.get("net_weight_total")),
        qty_auction=parse_float(row.get("qty_auction")),
        auction_percent=parse_float(row.get("auction_percent")),
        fact_rub_total=parse_float(row.get("fact_rub_total")),
        fact_rub_per_item=parse_float(row.get("fact_rub_per_item")),
        market_rub_total=parse_float(row.get("market_rub_total")),
        market_rub_per_item=parse_float(row.get("market_rub_per_item")),
        market_spread=parse_float(row.get("market_spread")),
        tech_load_ts=clean_text(row.get("tech_load_ts")),
        source_filename=clean_text(row.get("filename")),
        source_loaded_at=clean_text(row.get("tech_load_ts_core")),
    )
    for field_name in (
        "qty_total",
        "net_weight_total",
        "qty_auction",
        "fact_rub_total",
        "fact_rub_per_item",
        "market_rub_total",
        "market_rub_per_item",
    ):
        _non_negative(field_name, getattr(record, field_name), row_number)
    if record.auction_percent is not None and not 0 <= record.auction_percent <= 1:
        raise ValueError(f"actual row {row_number}: auction_percent must use the 0..1 scale")
    _validate_price_consistency(record, row_number, fact_tolerance)
    return record


def iter_actual_snapshots(
    path: str | Path | None = None,
    *,
    limit: int | None = None,
    validate_unique: bool = True,
    fact_tolerance: float = 0.05,
) -> Iterator[ActualSnapshotRecord]:
    """Yield validated snapshots without exposing facility names in errors."""
    source_path = Path(path) if path is not None else default_actual_path()
    seen: set[tuple[str, str, str, str]] = set()
    with source_path.open(encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or ())
        missing = sorted(REQUIRED_ACTUAL_COLUMNS - headers)
        if missing:
            raise ValueError(f"Actual CSV is missing required columns: {', '.join(missing)}")
        for index, row in enumerate(reader, start=2):
            if limit is not None and index - 2 >= limit:
                break
            record = _record(row, index, fact_tolerance)
            key = (
                record.snapshot_month,
                record.shipment_month,
                record.origin_external_name,
                record.destination_region,
            )
            if validate_unique and key in seen:
                raise ValueError(f"actual row {index}: duplicate natural snapshot key")
            seen.add(key)
            yield record
