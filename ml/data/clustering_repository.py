"""Lazy in-memory Pulse index for Clustering Product v1."""

from __future__ import annotations

import threading
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ml.data.clustering_dataset import (
    CLUSTERING_ALLOWED_PERIOD_TYPES,
    ClusteringRoute,
    aggregate_clustering_records,
)
from ml.data.loader import default_csv_path, iter_records
from ml.data.schema import LogisticsRecord


@dataclass(frozen=True, slots=True)
class FileFingerprint:
    path: str
    size: int
    mtime_ns: int

    @classmethod
    def from_path(cls, path: str | Path) -> FileFingerprint:
        resolved = Path(path).resolve()
        stat = resolved.stat()
        return cls(str(resolved), stat.st_size, stat.st_mtime_ns)

    def as_dict(self) -> dict[str, str | int]:
        return {"path": self.path, "size": self.size, "mtime_ns": self.mtime_ns}

    def cache_token(self) -> tuple[str, int, int]:
        return self.path, self.size, self.mtime_ns


@dataclass(frozen=True, slots=True)
class ClusteringSourceRow:
    origin_fias: str
    origin_name: str | None
    origin_region: str | None
    destination_fias: str | None
    destination_name: str | None
    destination_region: str
    period_id: str | None
    period_type: str | None
    price: float | None
    route_length: float | None
    trip_count: int | None
    vehicle_type: str | None
    tonnage_id: str | None
    price_type: str | None
    tech_ts: datetime | None
    validation_errors: tuple[str, ...]
    source_row_number: int

    @property
    def rub_per_km(self) -> float | None:
        if self.price is None or self.price <= 0:
            return None
        if self.route_length is None or self.route_length <= 0:
            return None
        return self.price / self.route_length


def _source_row(record: LogisticsRecord, source_row_number: int) -> ClusteringSourceRow | None:
    if not record.origin_fias or not record.destination_region:
        return None
    return ClusteringSourceRow(
        origin_fias=record.origin_fias,
        origin_name=record.origin_name,
        origin_region=record.origin_region,
        destination_fias=record.destination_fias,
        destination_name=record.destination_name,
        destination_region=record.destination_region,
        period_id=record.period_id,
        period_type=record.period_type,
        price=record.price,
        route_length=record.route_length,
        trip_count=record.trip_count,
        vehicle_type=record.vehicle_type,
        tonnage_id=record.tonnage_id,
        price_type=record.price_type,
        tech_ts=record.tech_ts,
        validation_errors=record.validation_errors,
        source_row_number=source_row_number,
    )


def _newest_first(row: ClusteringSourceRow) -> tuple[bool, int, bool, float, int]:
    period = (
        int(row.period_id)
        if row.period_id and len(row.period_id) == 6 and row.period_id.isdigit()
        else None
    )
    timestamp = row.tech_ts
    if timestamp is not None and timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return (
        period is None,
        -(period or 0),
        timestamp is None,
        -(timestamp.timestamp() if timestamp is not None else 0),
        -row.source_row_number,
    )


class ClusteringRepository:
    """Build and invalidate a compact index using the Pulse file fingerprint."""

    def __init__(self, source_path: str | Path | None = None) -> None:
        self.source_path = Path(source_path) if source_path is not None else default_csv_path()
        self._lock = threading.RLock()
        self._fingerprint: FileFingerprint | None = None
        self._index: dict[tuple[str, str], tuple[ClusteringSourceRow, ...]] = {}
        self._origin_metadata: dict[str, dict[str, Any]] = {}
        self._facet_index: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = {}
        self._raw_rows = 0
        self._load_count = 0

    @property
    def load_count(self) -> int:
        return self._load_count

    def fingerprint(self) -> FileFingerprint:
        current = FileFingerprint.from_path(self.source_path)
        with self._lock:
            if self._fingerprint != current:
                self._reload(current)
            return current

    def _reload(self, fingerprint: FileFingerprint) -> None:
        grouped: dict[tuple[str, str], list[ClusteringSourceRow]] = defaultdict(list)
        origin_names: dict[str, Counter[str]] = defaultdict(Counter)
        origin_regions: dict[str, Counter[str]] = defaultdict(Counter)
        raw_rows = 0
        for source_row_number, record in enumerate(iter_records(self.source_path), start=1):
            raw_rows += 1
            row = _source_row(record, source_row_number)
            if row is None:
                continue
            grouped[(row.origin_fias, row.destination_region)].append(row)
            if row.origin_name:
                origin_names[row.origin_fias][row.origin_name] += 1
            if row.origin_region:
                origin_regions[row.origin_fias][row.origin_region] += 1
        self._index = {key: tuple(value) for key, value in grouped.items()}
        origin_trips: Counter[str] = Counter()
        for (origin_fias, _), rows in self._index.items():
            origin_trips[origin_fias] += sum(max(row.trip_count or 0, 0) for row in rows)
        self._origin_metadata = {
            origin_fias: {
                "fias_id": origin_fias,
                "name": origin_names[origin_fias].most_common(1)[0][0]
                if origin_names[origin_fias]
                else "<missing>",
                "region": origin_regions[origin_fias].most_common(1)[0][0]
                if origin_regions[origin_fias]
                else "<missing>",
                "trip_count": origin_trips[origin_fias],
            }
            for origin_fias in sorted({key[0] for key in grouped})
        }
        self._facet_index = {
            key: {
                "period_types": self._facet(rows, "period_type"),
                "price_types": self._facet(rows, "price_type"),
                "vehicle_types": self._facet(rows, "vehicle_type"),
                "tonnage_ids": self._facet(rows, "tonnage_id"),
            }
            for key, rows in self._index.items()
        }
        self._raw_rows = raw_rows
        self._fingerprint = fingerprint
        self._load_count += 1

    def _rows(self, origin_fias: str, destination_region: str) -> tuple[ClusteringSourceRow, ...]:
        self.fingerprint()
        return self._index.get((origin_fias, destination_region), ())

    def has_origin(self, origin_fias: str) -> bool:
        self.fingerprint()
        return origin_fias in self._origin_metadata

    def destination_regions(self, origin_fias: str) -> list[str]:
        self.fingerprint()
        return sorted(region for origin, region in self._index if origin == origin_fias)

    def has_destination_region(self, origin_fias: str, destination_region: str) -> bool:
        return bool(self._rows(origin_fias, destination_region))

    def options(
        self, origin_fias: str | None = None, destination_region: str | None = None
    ) -> dict[str, Any]:
        fingerprint = self.fingerprint()
        result: dict[str, Any] = {
            "origins": list(self._origin_metadata.values()),
            "period_types": sorted(CLUSTERING_ALLOWED_PERIOD_TYPES),
            "dataset_fingerprint": fingerprint.as_dict(),
        }
        if origin_fias:
            result["destination_regions"] = self.destination_regions(origin_fias)
        if origin_fias and destination_region:
            result["facets"] = self._facet_index.get(
                (origin_fias, destination_region),
                {"period_types": [], "price_types": [], "vehicle_types": [], "tonnage_ids": []},
            )
        return result

    @staticmethod
    def _facet(rows: tuple[ClusteringSourceRow, ...], name: str) -> list[dict[str, Any]]:
        counts = Counter(getattr(row, name) for row in rows if getattr(row, name))
        return [{"value": value, "count": counts[value]} for value in sorted(counts)]

    def aggregate(
        self,
        *,
        origin_fias: str,
        destination_region: str,
        period_types: set[str],
        price_types: set[str],
        vehicle_types: set[str],
        tonnage_ids: set[str],
    ) -> tuple[list[ClusteringRoute], dict[str, Any]]:
        rows = self._rows(origin_fias, destination_region)
        return aggregate_clustering_records(
            rows,  # type: ignore[arg-type]
            source_path=self.source_path,
            destination_region=destination_region,
            origin_fias=origin_fias,
            period_types=period_types,
            price_types=price_types,
            vehicle_types=vehicle_types,
            tonnage_ids=tonnage_ids,
            dataset_raw_rows=self._raw_rows,
        )

    def source_rows(
        self,
        *,
        origin_fias: str,
        destination_region: str,
        destination_fias: str,
        period_types: set[str],
        price_types: set[str],
        vehicle_types: set[str],
        tonnage_ids: set[str],
    ) -> list[ClusteringSourceRow]:
        """Return one destination's normalized rows in deterministic newest-first order."""
        rows = (
            row
            for row in self._rows(origin_fias, destination_region)
            if row.destination_fias == destination_fias
            and (not period_types or row.period_type in period_types)
            and (not price_types or row.price_type in price_types)
            and (not vehicle_types or row.vehicle_type in vehicle_types)
            and (not tonnage_ids or row.tonnage_id in tonnage_ids)
        )
        return sorted(rows, key=_newest_first)
