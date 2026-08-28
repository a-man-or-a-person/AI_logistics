"""Validation and leakage policy for the predictive Pulse ML data contract."""

from __future__ import annotations

import re
from collections.abc import Mapping

from ml.data.schema import clean_text, parse_datetime, parse_float, parse_int

PERIOD_ID_PATTERN = re.compile(r"^\d{6}$")

# This policy is intentionally conservative until the business semantics are confirmed.
PREDICTIVE_FEATURE_POLICY = {
    "units": {
        "role": "target_candidate",
        "allowed_as_feature": False,
        "reason": "Candidate price target; exact business semantics are still open.",
    },
    "period_type": {
        "role": "split_control",
        "allowed_as_feature": False,
        "reason": "forecast rows must not be used as ordinary training labels.",
    },
    "confidence": {
        "role": "blocked_pending_semantics",
        "allowed_as_feature": False,
        "reason": "May be derived from the external price calculation and leak the target.",
    },
    "bid_count": {
        "role": "blocked_pending_semantics",
        "allowed_as_feature": False,
        "reason": "It is unknown whether the value exists at prediction time.",
    },
    "tech_load_ts": {
        "role": "point_in_time_control",
        "allowed_as_feature": False,
        "reason": "Used to establish availability, revisions, and temporal ordering.",
    },
}


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
