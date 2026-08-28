"""Build the canonical one-row-per-business-key evaluation dataset."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ml.data.cluster_assignments import ClusterEvaluationAssignment
from ml.data.distance import DistanceRecord
from ml.data.ground_truth import GroundTruthRecord
from ml.data.matching import OriginMapping
from ml.data.normalization import normalize_region
from ml.data.pulse_evaluation import PulseEvaluationRecord
from ml.evaluation.contracts import CoverageReport, EvaluationRow


@dataclass(slots=True)
class PulseAggregate:
    prices: list[float]
    weighted_price_sum: float = 0.0
    bid_count: int = 0
    price_sum: float = 0.0
    distance_sum: float = 0.0
    weighted_distance_sum: float = 0.0
    period_types: set[str] | None = None

    def __init__(self) -> None:
        self.prices = []
        self.weighted_price_sum = 0.0
        self.bid_count = 0
        self.price_sum = 0.0
        self.distance_sum = 0.0
        self.weighted_distance_sum = 0.0
        self.period_types = set()

    def add(self, record: PulseEvaluationRecord) -> None:
        if record.period_type:
            self.period_types.add(record.period_type)
        if record.price is None or record.price <= 0:
            return
        self.prices.append(record.price)
        bids = max(record.bid_count or 0, 0)
        self.weighted_price_sum += record.price * bids
        self.bid_count += bids
        if record.route_length is not None and record.route_length > 0:
            self.price_sum += record.price
            self.distance_sum += record.route_length
            self.weighted_distance_sum += record.route_length * bids

    @property
    def mean_price(self) -> float | None:
        return sum(self.prices) / len(self.prices) if self.prices else None

    @property
    def weighted_mean_price(self) -> float | None:
        return self.weighted_price_sum / self.bid_count if self.bid_count else None

    @property
    def rub_per_km(self) -> float | None:
        return self.price_sum / self.distance_sum if self.distance_sum else None

    @property
    def weighted_rub_per_km(self) -> float | None:
        return self.weighted_price_sum / self.weighted_distance_sum if self.weighted_distance_sum else None


@dataclass(frozen=True, slots=True)
class DatasetBuildResult:
    rows: tuple[EvaluationRow, ...]
    coverage: CoverageReport
    data_quality: dict[str, Any]


def _period_id(month: str) -> str:
    return month.replace("-", "")


def _temporal_status(period_types: set[str]) -> str:
    if not period_types:
        return "missing"
    if period_types == {"current"}:
        return "contemporaneous"
    if period_types == {"retro"}:
        return "retrospective_diagnostic"
    if period_types == {"forecast"}:
        return "forecast_with_realized_actual"
    return "mixed_period_types"


def _ratio(matched: float, total: float) -> float:
    return matched / total if total else 0.0


def _distance_index(
    distances: list[DistanceRecord],
) -> dict[tuple[str, str, str | None], list[DistanceRecord]]:
    index: dict[tuple[str, str, str | None], list[DistanceRecord]] = defaultdict(list)
    for item in distances:
        index[(item.origin_fias, item.destination_region, item.shipment_month)].append(item)
    return index


def build_evaluation_dataset(
    ground_truth: list[GroundTruthRecord],
    pulse_records: list[PulseEvaluationRecord],
    mappings: dict[str, OriginMapping],
    *,
    distances: list[DistanceRecord] | None = None,
    cluster_assignments: list[ClusterEvaluationAssignment] | None = None,
    price_types: set[str] | None = None,
    period_types: set[str] | None = None,
) -> DatasetBuildResult:
    selected_prices = price_types or set()
    selected_periods = period_types or set()
    pulse: dict[tuple[str, str, str], PulseAggregate] = defaultdict(PulseAggregate)
    for record in pulse_records:
        region = normalize_region(record.destination_region)
        if record.origin_fias is None or region is None or record.period_id is None:
            continue
        if selected_prices and record.price_type not in selected_prices:
            continue
        if selected_periods and record.period_type not in selected_periods:
            continue
        pulse[(record.origin_fias, region, record.period_id)].add(record)

    distance_lookup = _distance_index(distances or [])
    assignment_lookup = {
        (item.shipment_month, item.actual_origin_id, item.destination_region): item
        for item in (cluster_assignments or [])
    }
    rows: list[EvaluationRow] = []
    total_cells = len(ground_truth)
    total_qty = sum(max(item.qty_total or 0, 0) for item in ground_truth)
    fact_cells = mapping_cells = pulse_cells = distance_cells = cluster_cells = final_cells = 0
    fact_qty = mapping_qty = pulse_qty = distance_qty = cluster_qty = final_qty = 0.0

    for target in ground_truth:
        qty = max(target.qty_total or 0, 0)
        eligible_target = target.target_status in {"final_post_shipment", "m0_only"}
        has_fact = (
            eligible_target
            and target.fact_rub_per_item is not None
            and target.fact_rub_per_item > 0
        )
        if has_fact:
            fact_cells += 1
            fact_qty += qty
        mapping = mappings.get(target.evaluation_key.actual_origin_id)
        is_mapped = bool(
            mapping
            and mapping.match_status == "matched"
            and mapping.pulse_origin_fias
        )
        if is_mapped:
            mapping_cells += 1
            mapping_qty += qty
        aggregate = (
            pulse.get(
                (
                    str(mapping.pulse_origin_fias),
                    target.evaluation_key.destination_region,
                    _period_id(target.evaluation_key.shipment_month),
                )
            )
            if is_mapped
            else None
        )
        has_pulse = bool(aggregate and aggregate.mean_price is not None)
        if has_pulse:
            pulse_cells += 1
            pulse_qty += qty

        distance: DistanceRecord | None = None
        distance_status = "missing"
        if is_mapped:
            exact = distance_lookup.get(
                (
                    str(mapping.pulse_origin_fias),
                    target.evaluation_key.destination_region,
                    target.evaluation_key.shipment_month,
                ),
                [],
            )
            fallback = distance_lookup.get(
                (str(mapping.pulse_origin_fias), target.evaluation_key.destination_region, None), []
            )
            candidates = exact or fallback
            if len(candidates) == 1:
                distance = candidates[0]
                distance_status = "matched"
                distance_cells += 1
                distance_qty += qty
            elif len(candidates) > 1:
                distance_status = "ambiguous"

        if has_fact and has_pulse:
            final_cells += 1
            final_qty += qty
        assignment = assignment_lookup.get(
            (
                target.evaluation_key.shipment_month,
                target.evaluation_key.actual_origin_id,
                target.evaluation_key.destination_region,
            )
        )
        if assignment is not None:
            cluster_cells += 1
            cluster_qty += qty
        rows.append(
            EvaluationRow(
                key=target.evaluation_key,
                actual_price=target.fact_rub_per_item if eligible_target else None,
                qty=target.qty_total,
                pulse_price=aggregate.mean_price if aggregate else None,
                pulse_trip_weighted_price=aggregate.weighted_mean_price if aggregate else None,
                pulse_rub_per_km=aggregate.rub_per_km if aggregate else None,
                pulse_trip_weighted_rub_per_km=(aggregate.weighted_rub_per_km if aggregate else None),
                market_rub_per_item=target.market_rub_per_item_at_final,
                distance_km=distance.distance_km if distance else None,
                distance_status=distance_status,
                destination_fias=assignment.destination_fias if assignment else None,
                cluster_id=assignment.cluster_id if assignment else None,
                cluster_price=assignment.cluster_price if assignment else None,
                cluster_rub_per_km=assignment.cluster_rub_per_km if assignment else None,
                mapping_status=mapping.match_status if mapping else "unmatched",
                temporal_status=_temporal_status(aggregate.period_types) if aggregate else "missing",
                target_status=target.target_status,
                target_horizon=target.target_horizon,
                auction_percent=target.auction_percent,
            )
        )

    coverage = CoverageReport(
        ground_truth_cell_coverage=_ratio(fact_cells, total_cells),
        ground_truth_qty_coverage=_ratio(fact_qty, total_qty),
        origin_mapping_cell_coverage=_ratio(mapping_cells, total_cells),
        origin_mapping_qty_coverage=_ratio(mapping_qty, total_qty),
        pulse_match_cell_coverage=_ratio(pulse_cells, total_cells),
        pulse_match_qty_coverage=_ratio(pulse_qty, total_qty),
        distance_coverage=_ratio(distance_qty, total_qty),
        cluster_coverage=_ratio(cluster_qty, total_qty),
        final_evaluation_cell_coverage=_ratio(final_cells, total_cells),
        final_evaluation_qty_coverage=_ratio(final_qty, total_qty),
    )
    data_quality = {
        "evaluation_cells": total_cells,
        "qty_total": total_qty,
        "price_types": sorted(selected_prices),
        "period_types": sorted(selected_periods),
        "price_type_filter_explicit": bool(selected_prices),
        "destination_grain": "region",
        "cluster_business_evaluation_supported": cluster_cells > 0,
    }
    return DatasetBuildResult(tuple(rows), coverage, data_quality)


def write_evaluation_dataset(rows: list[EvaluationRow] | tuple[EvaluationRow, ...], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "shipment_month",
        "actual_origin_id",
        "destination_region",
        "fact_rub_per_item",
        "qty_total",
        "pulse_price",
        "pulse_trip_weighted_price",
        "pulse_rub_per_km",
        "pulse_trip_weighted_rub_per_km",
        "market_rub_per_item",
        "distance_km",
        "distance_status",
        "cluster_id",
        "mapping_status",
        "temporal_status",
        "target_status",
        "target_horizon",
    ]
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            raw = asdict(row)
            key = raw.pop("key")
            writer.writerow(
                {
                    "shipment_month": key["shipment_month"],
                    "actual_origin_id": key["actual_origin_id"],
                    "destination_region": key["destination_region"],
                    "fact_rub_per_item": row.actual_price,
                    "qty_total": row.qty,
                    **{name: raw.get(name) for name in fieldnames},
                }
            )
    return output
