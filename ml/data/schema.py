"""Canonical contract shared by logistics research experiments."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

NULL_VALUES = frozenset({"", "null", "none", "nan", "n/a", "\\n"})


def clean_text(value: object) -> str | None:
    """Normalize CSV text and turn common null markers into ``None``."""
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized.casefold() in NULL_VALUES:
        return None
    return normalized


def parse_float(value: object) -> float | None:
    normalized = clean_text(value)
    if normalized is None:
        return None
    try:
        return float(normalized.replace(",", "."))
    except ValueError:
        return None


def parse_int(value: object) -> int | None:
    normalized = clean_text(value)
    if normalized is None:
        return None
    try:
        return int(normalized)
    except ValueError:
        return None


def parse_datetime(value: object) -> datetime | None:
    """Parse an ISO-like source timestamp while preserving invalid values as null."""
    normalized = clean_text(value)
    if normalized is None:
        return None
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class LogisticsRecord:
    """One normalized route-price observation.

    Coordinates are optional because the current Pulse export has no latitude or
    longitude. They will be joined by FIAS in a later spatial-data stage.
    """

    source: str
    origin_fias: str | None
    origin_name: str | None
    origin_region: str | None
    destination_fias: str | None
    destination_name: str | None
    destination_region: str | None
    latitude: float | None
    longitude: float | None
    period_id: str | None
    period_type: str | None
    price: float | None
    route_length: float | None
    trip_count: int | None
    vehicle_type: str | None
    tonnage_id: str | None
    price_type: str | None
    currency: str | None
    confidence: str | None
    origin_town_source: str | None = None
    origin_point_type: str | None = None
    origin_address: str | None = None
    destination_region_source: str | None = None
    destination_address: str | None = None
    destination_point_type: str | None = None
    nanos: int | None = None
    route_type: str | None = None
    tech_ts: datetime | None = None
    validation_errors: tuple[str, ...] = ()

    @property
    def rub_per_km(self) -> float | None:
        if self.price is None or self.route_length is None:
            return None
        if self.price <= 0 or self.route_length <= 0:
            return None
        return self.price / self.route_length

    def fingerprint(self) -> bytes:
        """Return a compact stable identifier used for duplicate detection."""
        values = (
            self.source,
            self.origin_fias,
            self.origin_name,
            self.origin_town_source,
            self.origin_region,
            self.origin_point_type,
            self.origin_address,
            self.destination_fias,
            self.destination_name,
            self.destination_region,
            self.destination_region_source,
            self.destination_address,
            self.destination_point_type,
            self.period_id,
            self.period_type,
            self.price,
            self.route_length,
            self.trip_count,
            self.nanos,
            self.route_type,
            self.vehicle_type,
            self.tonnage_id,
            self.price_type,
            self.currency,
            self.tech_ts.isoformat() if self.tech_ts is not None else None,
        )
        payload = "\x1f".join("" if value is None else str(value) for value in values)
        return hashlib.blake2b(payload.encode("utf-8"), digest_size=16).digest()
