"""Origin registry extracted from Pulse without changing ``LogisticsRecord``."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ml.data.loader import default_csv_path
from ml.data.schema import clean_text


@dataclass(frozen=True, slots=True)
class PulseOrigin:
    origin_fias: str
    origin_name: str | None
    origin_town_source: str | None
    origin_region: str | None
    origin_address: str | None
    origin_point_type: str | None


def load_pulse_origins(path: str | Path | None = None) -> list[PulseOrigin]:
    source_path = Path(path) if path is not None else default_csv_path()
    origins: dict[str, PulseOrigin] = {}
    with source_path.open(encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream)
        if "shipment_point_locality_fias_id" not in set(reader.fieldnames or ()):
            raise ValueError("Pulse CSV is missing shipment_point_locality_fias_id")
        for row in reader:
            origin_fias = clean_text(row.get("shipment_point_locality_fias_id"))
            if origin_fias is None:
                continue
            candidate = PulseOrigin(
                origin_fias=origin_fias,
                origin_name=clean_text(row.get("shipment_point_name_town")),
                origin_town_source=clean_text(row.get("shipment_point_town_source")),
                origin_region=clean_text(row.get("shipment_point_region")),
                origin_address=clean_text(row.get("shipment_point_address")),
                origin_point_type=clean_text(row.get("shipment_point_point_type")),
            )
            previous = origins.get(origin_fias)
            if previous is not None and previous != candidate:
                # Keep the richest deterministic registry row; do not silently merge FIAS ids.
                values = sorted(
                    (previous, candidate),
                    key=lambda item: sum(
                        value is not None
                        for value in (
                            item.origin_name,
                            item.origin_town_source,
                            item.origin_region,
                            item.origin_address,
                            item.origin_point_type,
                        )
                    ),
                    reverse=True,
                )
                origins[origin_fias] = values[0]
            else:
                origins[origin_fias] = candidate
    return sorted(origins.values(), key=lambda item: item.origin_fias)
