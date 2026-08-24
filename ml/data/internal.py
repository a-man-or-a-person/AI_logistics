"""Contract and loader for internal/ATI trip distances used by hypothesis 1."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from ml.data.schema import clean_text, parse_float, parse_int

INTERNAL_COLUMNS = (
    "origin_fias",
    "origin_name",
    "destination_fias",
    "destination_name",
    "destination_region",
    "period_id",
    "route_length",
    "trip_count",
    "reference_price",
)
REQUIRED_INTERNAL_COLUMNS = frozenset(
    {"origin_fias", "destination_region", "period_id", "route_length", "trip_count"}
)


@dataclass(frozen=True, slots=True)
class InternalTrip:
    origin_fias: str | None
    origin_name: str | None
    destination_fias: str | None
    destination_name: str | None
    destination_region: str | None
    period_id: str | None
    route_length: float | None
    trip_count: int | None
    reference_price: float | None


def iter_internal_trips(path: str | Path) -> Iterator[InternalTrip]:
    source_path = Path(path)
    with source_path.open(encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or ())
        missing = sorted(REQUIRED_INTERNAL_COLUMNS - headers)
        if missing:
            raise ValueError(f"Internal CSV is missing required columns: {', '.join(missing)}")
        for row in reader:
            yield InternalTrip(
                origin_fias=clean_text(row.get("origin_fias")),
                origin_name=clean_text(row.get("origin_name")),
                destination_fias=clean_text(row.get("destination_fias")),
                destination_name=clean_text(row.get("destination_name")),
                destination_region=clean_text(row.get("destination_region")),
                period_id=clean_text(row.get("period_id")),
                route_length=parse_float(row.get("route_length")),
                trip_count=parse_int(row.get("trip_count")),
                reference_price=parse_float(row.get("reference_price")),
            )
