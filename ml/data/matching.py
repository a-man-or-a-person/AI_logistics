"""Conservative, auditable actual-to-Pulse origin matching."""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ml.data.actual import ActualSnapshotRecord
from ml.data.normalization import normalize_town
from ml.data.pulse_registry import PulseOrigin
from ml.data.schema import clean_text, parse_float

ORIGIN_MAPPING_COLUMNS = (
    "actual_origin_id",
    "actual_origin_town",
    "pulse_origin_fias",
    "pulse_origin_name",
    "match_method",
    "match_status",
    "confidence",
    "mapping_version",
)


@dataclass(frozen=True, slots=True)
class OriginMapping:
    actual_origin_id: str
    actual_origin_town: str | None
    pulse_origin_fias: str | None
    pulse_origin_name: str | None
    match_method: str
    match_status: str
    confidence: float | None
    mapping_version: str


@dataclass(frozen=True, slots=True)
class OriginCandidate:
    actual_origin_id: str
    actual_origin_name: str
    actual_origin_town: str | None
    pulse_origin_fias: str | None
    pulse_origin_name: str | None
    match_method: str
    match_status: str
    confidence: float | None


def default_origin_mapping_path() -> Path | None:
    configured = os.environ.get("LOGISTICS_ORIGIN_MAP_FILE")
    return Path(configured) if configured else None


def load_origin_mapping(path: str | Path) -> dict[str, OriginMapping]:
    mappings: dict[str, OriginMapping] = {}
    with Path(path).open(encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or ())
        missing = sorted(set(ORIGIN_MAPPING_COLUMNS) - headers)
        if missing:
            raise ValueError(f"Origin mapping is missing columns: {', '.join(missing)}")
        for row_number, row in enumerate(reader, start=2):
            actual_origin_id = clean_text(row.get("actual_origin_id"))
            if actual_origin_id is None:
                raise ValueError(f"origin mapping row {row_number}: actual_origin_id is required")
            if actual_origin_id in mappings:
                raise ValueError(f"origin mapping row {row_number}: duplicate actual_origin_id")
            mappings[actual_origin_id] = OriginMapping(
                actual_origin_id=actual_origin_id,
                actual_origin_town=clean_text(row.get("actual_origin_town")),
                pulse_origin_fias=clean_text(row.get("pulse_origin_fias")),
                pulse_origin_name=clean_text(row.get("pulse_origin_name")),
                match_method=clean_text(row.get("match_method")) or "manual",
                match_status=clean_text(row.get("match_status")) or "unmatched",
                confidence=parse_float(row.get("confidence")),
                mapping_version=clean_text(row.get("mapping_version")) or "unknown",
            )
    return mappings


def build_origin_candidates(
    snapshots: list[ActualSnapshotRecord], pulse_origins: list[PulseOrigin]
) -> list[OriginCandidate]:
    actual_origins: dict[str, tuple[str, str | None]] = {}
    for snapshot in snapshots:
        actual_origins.setdefault(
            snapshot.actual_origin_id, (snapshot.origin_external_name, snapshot.origin_town)
        )

    actual_by_town: dict[str, list[str]] = defaultdict(list)
    for origin_id, (_, town) in actual_origins.items():
        normalized = normalize_town(town)
        if normalized is not None:
            actual_by_town[normalized].append(origin_id)

    pulse_by_town: dict[str, list[PulseOrigin]] = defaultdict(list)
    for origin in pulse_origins:
        normalized = normalize_town(origin.origin_town_source or origin.origin_name)
        if normalized is not None:
            pulse_by_town[normalized].append(origin)

    candidates: list[OriginCandidate] = []
    for origin_id, (origin_name, town) in sorted(actual_origins.items()):
        normalized = normalize_town(town)
        actual_matches = actual_by_town.get(normalized or "", [])
        pulse_matches = pulse_by_town.get(normalized or "", [])
        if normalized and len(actual_matches) == 1 and len(pulse_matches) == 1:
            pulse = pulse_matches[0]
            candidates.append(
                OriginCandidate(
                    actual_origin_id=origin_id,
                    actual_origin_name=origin_name,
                    actual_origin_town=town,
                    pulse_origin_fias=pulse.origin_fias,
                    pulse_origin_name=pulse.origin_name or pulse.origin_town_source,
                    match_method="unique_town",
                    match_status="matched",
                    confidence=1.0,
                )
            )
            continue
        status = "ambiguous" if normalized and (len(actual_matches) > 1 or len(pulse_matches) > 1) else "unmatched"
        candidates.append(
            OriginCandidate(
                actual_origin_id=origin_id,
                actual_origin_name=origin_name,
                actual_origin_town=town,
                pulse_origin_fias=None,
                pulse_origin_name=None,
                match_method="unique_town",
                match_status=status,
                confidence=None,
            )
        )
    return candidates
