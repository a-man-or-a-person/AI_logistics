"""Trusted distance contract used by E1 and E3."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path

from ml.data.normalization import normalize_region
from ml.data.schema import clean_text, parse_float

DISTANCE_COLUMNS = (
    "origin_fias",
    "destination_region",
    "destination_fias",
    "shipment_month",
    "distance_km",
    "source",
    "confidence",
)
APPROVED_DISTANCE_SOURCES = frozenset(
    {"internal_actual", "approved_route_system", "manual_verified"}
)


@dataclass(frozen=True, slots=True)
class DistanceRecord:
    origin_fias: str
    destination_region: str
    destination_fias: str | None
    shipment_month: str | None
    distance_km: float
    source: str
    confidence: float | None


def default_distance_path() -> Path | None:
    configured = os.environ.get("LOGISTICS_DISTANCE_FILE")
    return Path(configured) if configured else None


def load_distances(path: str | Path) -> list[DistanceRecord]:
    records: list[DistanceRecord] = []
    with Path(path).open(encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or ())
        missing = sorted(set(DISTANCE_COLUMNS) - headers)
        if missing:
            raise ValueError(f"Distance CSV is missing columns: {', '.join(missing)}")
        for row_number, row in enumerate(reader, start=2):
            origin_fias = clean_text(row.get("origin_fias"))
            region = normalize_region(clean_text(row.get("destination_region")))
            distance = parse_float(row.get("distance_km"))
            source = clean_text(row.get("source")) or ""
            if origin_fias is None or region is None or distance is None or distance <= 0:
                raise ValueError(f"distance row {row_number}: valid origin, region and distance required")
            if source not in APPROVED_DISTANCE_SOURCES:
                raise ValueError(f"distance row {row_number}: unapproved source {source!r}")
            records.append(
                DistanceRecord(
                    origin_fias=origin_fias,
                    destination_region=region,
                    destination_fias=clean_text(row.get("destination_fias")),
                    shipment_month=clean_text(row.get("shipment_month")),
                    distance_km=distance,
                    source=source,
                    confidence=parse_float(row.get("confidence")),
                )
            )
    return records
