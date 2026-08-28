"""Conservative normalization helpers for analytics joins."""

from __future__ import annotations

import re
import unicodedata

_DASHES = re.compile(r"[\u2010-\u2015\u2212]+")
_SPACES = re.compile(r"\s+")

REGION_ALIASES = {
    "г москва": "москва",
    "город москва": "москва",
    "г санкт петербург": "санкт-петербург",
    "город санкт петербург": "санкт-петербург",
    "санкт петербург": "санкт-петербург",
}


def normalize_name(value: str | None) -> str | None:
    """Normalize spelling without performing fuzzy matching."""
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value).strip().casefold().replace("ё", "е")
    normalized = _DASHES.sub("-", normalized)
    normalized = _SPACES.sub(" ", normalized)
    return normalized or None


def normalize_town(value: str | None) -> str | None:
    return normalize_name(value)


def normalize_region(value: str | None) -> str | None:
    normalized = normalize_name(value)
    if normalized is None:
        return None
    return REGION_ALIASES.get(normalized, normalized)
