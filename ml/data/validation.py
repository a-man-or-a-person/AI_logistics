"""Validation and field policy for Pulse analytics contracts."""

from __future__ import annotations

import re
from collections.abc import Mapping

from ml.data.schema import clean_text, parse_datetime, parse_float, parse_int

PERIOD_ID_PATTERN = re.compile(r"^\d{6}$")

CLUSTERING_FIELD_POLICY = {
    "units": {
        "role": "shipment_volume",
        "allowed_as_feature": False,
        "allowed_as_weight": True,
        "reason": "Confirmed source of shipment_count; never part of the x/y feature matrix.",
    },
    "period_type": {
        "role": "split_control",
        "allowed_as_feature": False,
        "reason": "Only current and retro rows enter the clustering dataset.",
    },
    "confidence": {
        "role": "diagnostic_only",
        "allowed_as_feature": False,
        "reason": "Pulse-derived confidence is not a clustering feature or weight.",
    },
    "bid_count": {
        "role": "diagnostic_only",
        "allowed_as_feature": False,
        "reason": "Pulse-derived bid_count is not shipment volume.",
    },
    "tech_load_ts": {
        "role": "point_in_time_control",
        "allowed_as_feature": False,
        "reason": "Used to establish availability, revisions, and temporal ordering.",
    },
}

# Kept as a compatibility export for deferred predictive documentation.
PREDICTIVE_FEATURE_POLICY = CLUSTERING_FIELD_POLICY


def pulse_row_validation_errors(row: Mapping[str, object]) -> tuple[str, ...]:
    """Return parse errors without conflating malformed values with source nulls."""
    errors: list[str] = []
    numeric_parsers = {
        "units": parse_float,
        "route_length": parse_float,
        "bid_count": parse_int,
        "nanos": parse_int,
    }
    for field, parser in numeric_parsers.items():
        value = row.get(field)
        if clean_text(value) is not None and parser(value) is None:
            errors.append(f"invalid_{field}")

    period_id = clean_text(row.get("period_id"))
    if period_id is not None and PERIOD_ID_PATTERN.fullmatch(period_id) is None:
        errors.append("invalid_period_id")

    tech_ts = row.get("tech_load_ts")
    if clean_text(tech_ts) is not None and parse_datetime(tech_ts) is None:
        errors.append("invalid_tech_load_ts")
    return tuple(errors)
