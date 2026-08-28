"""Town-based origin FIAS candidates for the clustering milestone."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from ml.data.schema import LogisticsRecord

_PREFIX = re.compile(
    r"^(?:г(?:ород)?|г\.|п(?:ос(?:елок)?)?|п\.|пос\.|рп\.|гп\.)\s+",
    flags=re.IGNORECASE,
)


def normalize_town(value: str | None) -> str:
    normalized = " ".join((value or "").strip().casefold().replace("ё", "е").split())
    return _PREFIX.sub("", normalized).strip(" .,")


@dataclass(frozen=True, slots=True)
class OriginFiasCandidate:
    normalized_town: str
    source_names: tuple[str, ...]
    candidate_fias: tuple[str, ...]
    trip_count: int
    status: str


def build_origin_fias_candidates(
    records: list[LogisticsRecord],
) -> list[OriginFiasCandidate]:
    names: dict[str, set[str]] = defaultdict(set)
    fias: dict[str, set[str]] = defaultdict(set)
    shipments: dict[str, float] = defaultdict(float)
    for record in records:
        if record.period_type not in {"current", "retro"}:
            continue
        source_name = record.origin_town_source or record.origin_name
        town = normalize_town(source_name)
        if not town:
            continue
        if source_name:
            names[town].add(source_name)
        if record.origin_fias:
            fias[town].add(record.origin_fias)
        shipments[town] += max(record.trip_count or 0, 0)
    result = [
        OriginFiasCandidate(
            normalized_town=town,
            source_names=tuple(sorted(names[town])),
            candidate_fias=tuple(sorted(fias[town])),
            trip_count=int(shipments[town]),
            status="auto_unique" if len(fias[town]) == 1 else "manual_required",
        )
        for town in names
    ]
    return sorted(result, key=lambda item: (-item.trip_count, item.normalized_town))
