"""Shared contracts for actual-price experiment variants."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ml.data.ground_truth import FORBIDDEN_PREDICTION_FIELDS, EvaluationKey


@dataclass(frozen=True, slots=True)
class EvaluationRow:
    key: EvaluationKey
    actual_price: float | None
    qty: float | None
    pulse_price: float | None = None
    pulse_trip_weighted_price: float | None = None
    pulse_rub_per_km: float | None = None
    pulse_trip_weighted_rub_per_km: float | None = None
    market_rub_per_item: float | None = None
    market_by_horizon: dict[int, float] = field(default_factory=dict)
    distance_km: float | None = None
    distance_status: str = "missing"
    destination_fias: str | None = None
    cluster_id: int | None = None
    cluster_price: float | None = None
    cluster_rub_per_km: float | None = None
    mapping_status: str = "unmatched"
    temporal_status: str = "unknown"
    target_status: str = "missing"
    target_horizon: int | None = None
    auction_percent: float | None = None


@dataclass(frozen=True, slots=True)
class Prediction:
    variant: str
    key: EvaluationKey
    predicted_price: float | None
    status: str
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    n_evaluation_cells: int
    qty_evaluated: float
    wape_pct: float | None
    weighted_mae_rub_per_item: float | None
    mdape_pct: float | None
    bias_pct: float | None
    within_10_pct: float | None
    within_20_pct: float | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CoverageReport:
    ground_truth_cell_coverage: float
    ground_truth_qty_coverage: float
    origin_mapping_cell_coverage: float
    origin_mapping_qty_coverage: float
    pulse_match_cell_coverage: float
    pulse_match_qty_coverage: float
    distance_coverage: float
    cluster_coverage: float
    final_evaluation_cell_coverage: float
    final_evaluation_qty_coverage: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VariantResult:
    variant: str
    status: str
    predictions: tuple[Prediction, ...]
    metrics: EvaluationMetrics | None
    coverage: float
    blocker: str | None = None
    required_fields: tuple[str, ...] = ()
    segment_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExperimentMetadata:
    methodology_version: str
    created_at: str
    git_commit_sha: str | None
    pulse_file_hash: str
    actual_file_hash: str
    mapping_file_hash: str
    distance_file_hash: str | None
    cluster_assignment_hash: str | None
    as_of: str | None
    target_months: tuple[str, ...]
    price_types: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_prediction_features(fields: set[str] | frozenset[str]) -> None:
    forbidden = sorted(set(fields) & FORBIDDEN_PREDICTION_FIELDS)
    if forbidden:
        raise ValueError(f"Forbidden prediction fields: {', '.join(forbidden)}")
