"""Provenance contract for administrative boundaries used in territorialization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

BOUNDARY_STATUSES = frozenset({"official", "development", "unknown"})


def boundary_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class BoundaryManifest:
    region: str
    authority: str
    source_type: str
    retrieved_at: str
    effective_date: str | None
    crs: str
    sha256: str
    status: str

    @property
    def official(self) -> bool:
        return self.status == "official"


def load_boundary_manifest(
    path: str | Path,
    *,
    boundary_path: str | Path | None = None,
    require_official: bool = False,
) -> BoundaryManifest:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
        manifest = BoundaryManifest(
            region=str(payload["region"]),
            authority=str(payload["authority"]),
            source_type=str(payload["source_type"]),
            retrieved_at=str(payload["retrieved_at"]),
            effective_date=(str(payload["effective_date"]) if payload.get("effective_date") else None),
            crs=str(payload["crs"]),
            sha256=str(payload["sha256"]),
            status=str(payload.get("status", "official" if payload.get("official") else "unknown")),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError(f"Cannot read boundary manifest: {source}") from error
    if manifest.status not in BOUNDARY_STATUSES:
        raise ValueError(f"Boundary status must be one of {sorted(BOUNDARY_STATUSES)}")
    if manifest.crs != "EPSG:4326":
        raise ValueError("Boundary manifest CRS must be EPSG:4326")
    if require_official and not manifest.official:
        raise ValueError("Production territorialization requires an official boundary")
    if boundary_path is not None and boundary_sha256(boundary_path) != manifest.sha256:
        raise ValueError("Boundary file SHA-256 does not match its manifest")
    return manifest
