"""Approved, locally configured region-boundary access."""

from __future__ import annotations

import os
from pathlib import Path

from shapely.geometry.base import BaseGeometry

from ml.spatial.boundaries import load_region_boundary


class BoundaryProvider:
    """Read region geometry from an explicitly configured local GeoJSON file.

    Absence of a configured file or of the requested region is a supported
    product state. Invalid configured data remains an error: it must never be
    replaced by a bbox, generated rectangle, or downloaded geometry.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        configured = path if path is not None else os.environ.get(
            "LOGISTICS_REGION_BOUNDARIES_FILE"
        )
        self.path = Path(configured) if configured else None

    def get_region_boundary(self, region: str) -> BaseGeometry | None:
        if self.path is None or not self.path.is_file():
            return None
        try:
            return load_region_boundary(self.path, region_name=region)
        except ValueError as error:
            if "was not found in boundary GeoJSON" in str(error):
                return None
            raise
