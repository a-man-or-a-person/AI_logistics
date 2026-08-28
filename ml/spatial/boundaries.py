"""Strict loading and validation for approved regional GeoJSON boundaries."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

DEFAULT_NAME_FIELDS = (
    "name",
    "NAME",
    "region",
    "region_name",
    "subject",
    "subject_name",
)


def _normalized_name(value: object) -> str:
    return " ".join(str(value).strip().casefold().replace("ё", "е").split())


def _features(document: dict[str, Any]) -> list[dict[str, Any]]:
    document_type = document.get("type")
    if document_type == "FeatureCollection":
        features = document.get("features")
        if not isinstance(features, list) or not features:
            raise ValueError("GeoJSON FeatureCollection must contain features")
        return features
    if document_type == "Feature":
        return [document]
    if document_type in {"Polygon", "MultiPolygon"}:
        return [{"type": "Feature", "properties": {}, "geometry": document}]
    raise ValueError("Boundary GeoJSON must be a Polygon, MultiPolygon, or FeatureCollection")


def _matches_region(
    feature: dict[str, Any],
    region_name: str,
    name_fields: Iterable[str],
) -> bool:
    properties = feature.get("properties") or {}
    if not isinstance(properties, dict):
        return False
    expected = _normalized_name(region_name)
    return any(
        _normalized_name(properties.get(field)) == expected
        for field in name_fields
        if properties.get(field) is not None
    )


def _validate_wgs84_geometry(geometry: BaseGeometry) -> None:
    if geometry.is_empty:
        raise ValueError("Region boundary must not be empty")
    if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Region boundary must contain only polygon geometry")
    if not geometry.is_valid:
        raise ValueError("Region boundary geometry is invalid")
    min_x, min_y, max_x, max_y = geometry.bounds
    if min_x < -180 or max_x > 180 or min_y < -90 or max_y > 90:
        raise ValueError("Region boundary coordinates must use WGS84 longitude/latitude")


def load_region_boundary(
    path: str | Path,
    *,
    region_name: str | None = None,
    name_fields: Iterable[str] = DEFAULT_NAME_FIELDS,
) -> BaseGeometry:
    """Load one approved WGS84 boundary without fuzzy or bbox fallbacks.

    A multi-feature file requires an explicit ``region_name``. Matching is exact
    after conservative whitespace/case normalization and checks only known name
    properties. Multiple matching polygon parts are dissolved into one geometry.
    """
    source = Path(path)
    try:
        document = json.loads(source.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read boundary GeoJSON: {source}") from error
    if not isinstance(document, dict):
        raise ValueError("Boundary GeoJSON root must be an object")

    features = _features(document)
    if region_name is None:
        if len(features) != 1:
            raise ValueError("region_name is required for a multi-feature boundary file")
        selected = features
    else:
        selected = [
            feature
            for feature in features
            if isinstance(feature, dict)
            and _matches_region(feature, region_name, name_fields)
        ]
        if not selected:
            raise ValueError(f"Region {region_name!r} was not found in boundary GeoJSON")

    geometries = []
    for feature in selected:
        geometry_document = feature.get("geometry")
        if not isinstance(geometry_document, dict):
            raise ValueError("Boundary feature must contain a GeoJSON geometry")
        try:
            geometry = shape(geometry_document)
        except (TypeError, ValueError) as error:
            raise ValueError("Boundary feature contains invalid GeoJSON geometry") from error
        _validate_wgs84_geometry(geometry)
        geometries.append(geometry)

    boundary = unary_union(geometries)
    _validate_wgs84_geometry(boundary)
    return boundary
