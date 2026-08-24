"""Local Azimuthal Equidistant projection for one-region experiments."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache

EARTH_RADIUS_M = 6_371_008.8


@lru_cache(maxsize=32)
def _cached_transformers(center_latitude: float, center_longitude: float):
    try:
        from pyproj import CRS, Transformer
    except ImportError as error:
        raise RuntimeError(
            "pyproj is required for metric projection; install requirements-ml.txt"
        ) from error
    local_crs = CRS.from_proj4(
        "+proj=aeqd "
        f"+lat_0={center_latitude} +lon_0={center_longitude} "
        "+datum=WGS84 +units=m +no_defs"
    )
    forward = Transformer.from_crs("EPSG:4326", local_crs, always_xy=True)
    inverse = Transformer.from_crs(local_crs, "EPSG:4326", always_xy=True)
    return forward, inverse


def haversine_distance_m(
    first: tuple[float, float], second: tuple[float, float]
) -> float:
    """Return great-circle distance for ``(latitude, longitude)`` pairs."""
    lat1, lon1 = map(math.radians, first)
    lat2, lon2 = map(math.radians, second)
    delta_latitude = lat2 - lat1
    delta_longitude = lon2 - lon1
    value = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_longitude / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(value))


@dataclass(frozen=True, slots=True)
class LocalProjection:
    """WGS84 ↔ local metric AEQD projection centered on the selected region."""

    center_latitude: float
    center_longitude: float

    @classmethod
    def from_coordinates(
        cls, coordinates: Iterable[tuple[float, float]]
    ) -> LocalProjection:
        values = list(coordinates)
        if not values:
            raise ValueError("At least one coordinate is required")
        return cls(
            center_latitude=sum(latitude for latitude, _ in values) / len(values),
            center_longitude=sum(longitude for _, longitude in values) / len(values),
        )

    def _transformers(self):
        return _cached_transformers(self.center_latitude, self.center_longitude)

    def forward_transformer(self):
        """Return the cached pyproj transformer for WGS84 → local meters."""
        forward, _ = self._transformers()
        return forward

    def inverse_transformer(self):
        """Return the cached pyproj transformer for local meters → WGS84."""
        _, inverse = self._transformers()
        return inverse

    def project(self, latitude: float, longitude: float) -> tuple[float, float]:
        forward, _ = self._transformers()
        x, y = forward.transform(longitude, latitude)
        return float(x), float(y)

    def unproject(self, x: float, y: float) -> tuple[float, float]:
        _, inverse = self._transformers()
        longitude, latitude = inverse.transform(x, y)
        return float(latitude), float(longitude)
