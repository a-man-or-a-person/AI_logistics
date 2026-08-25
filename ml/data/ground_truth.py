"""Collapse versioned actual snapshots into canonical finalized ground truth."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from ml.data.actual import ActualSnapshotRecord
from ml.data.normalization import normalize_region

FORBIDDEN_PREDICTION_FIELDS = frozenset(
    {"fact_rub_total", "fact_rub_per_item", "market_spread"}
)

FIELD_AVAILABILITY = {
    "shipment_month": "known_before",
    "actual_origin_id": "known_before",
    "destination_region": "known_before",
    "market_rub_per_item": "known_at_booking",
    "qty_total": "known_after_transport",
    "net_weight_total": "known_after_transport",
    "qty_auction": "diagnostic_only",
    "auction_percent": "diagnostic_only",
    "fact_rub_total": "target",
    "fact_rub_per_item": "target",
    "market_spread": "diagnostic_only",
}


@dataclass(frozen=True, slots=True, order=True)
class EvaluationKey:
    shipment_month: str
    actual_origin_id: str
    destination_region: str


@dataclass(frozen=True, slots=True)
class GroundTruthRecord:
    evaluation_key: EvaluationKey
    fact_rub_per_item: float | None
    fact_rub_total: float | None
    qty_total: float | None
    net_weight_total: float | None
    qty_auction: float | None
    auction_percent: float | None
    target_snapshot_month: str
    target_horizon: int
    target_status: str
    market_rub_per_item_at_final: float | None
    fact_available: bool
    market_available: bool


def _status(snapshot: ActualSnapshotRecord, has_fact: bool) -> str:
    if not has_fact:
        return "missing"
    if snapshot.horizon_months < 0:
        return "final_post_shipment"
    if snapshot.horizon_months == 0:
        return "m0_only"
    return "pre_shipment_only"


def build_ground_truth(
    snapshots: list[ActualSnapshotRecord],
) -> list[GroundTruthRecord]:
    grouped: dict[EvaluationKey, list[ActualSnapshotRecord]] = defaultdict(list)
    for snapshot in snapshots:
        region = normalize_region(snapshot.destination_region)
        if region is None:
            continue
        key = EvaluationKey(snapshot.shipment_month, snapshot.actual_origin_id, region)
        grouped[key].append(snapshot)

    records: list[GroundTruthRecord] = []
    for key, versions in sorted(grouped.items()):
        ordered = sorted(versions, key=lambda item: item.snapshot_month)
        with_fact = [item for item in ordered if item.fact_rub_per_item is not None]
        selected = with_fact[-1] if with_fact else ordered[-1]
        records.append(
            GroundTruthRecord(
                evaluation_key=key,
                fact_rub_per_item=selected.fact_rub_per_item,
                fact_rub_total=selected.fact_rub_total,
                qty_total=selected.qty_total,
                net_weight_total=selected.net_weight_total,
                qty_auction=selected.qty_auction,
                auction_percent=selected.auction_percent,
                target_snapshot_month=selected.snapshot_month,
                target_horizon=selected.horizon_months,
                target_status=_status(selected, bool(with_fact)),
                market_rub_per_item_at_final=selected.market_rub_per_item,
                fact_available=selected.fact_rub_per_item is not None,
                market_available=selected.market_rub_per_item is not None,
            )
        )
    return records


def _relative_change(first: float | None, last: float | None) -> float | None:
    if first is None or last is None or first == 0:
        return None
    return abs(last - first) / abs(first)


def snapshot_revision_report(snapshots: list[ActualSnapshotRecord]) -> dict[str, Any]:
    groups: dict[EvaluationKey, list[ActualSnapshotRecord]] = defaultdict(list)
    for item in snapshots:
        region = normalize_region(item.destination_region)
        if region is not None:
            groups[EvaluationKey(item.shipment_month, item.actual_origin_id, region)].append(item)

    fields = {
        "fact": "fact_rub_per_item",
        "market": "market_rub_per_item",
        "qty": "qty_total",
        "auction": "auction_percent",
    }
    result: dict[str, Any] = {"business_keys": len(groups)}
    for label, field_name in fields.items():
        changes: list[float] = []
        for versions in groups.values():
            ordered = sorted(versions, key=lambda item: item.snapshot_month)
            change = _relative_change(getattr(ordered[0], field_name), getattr(ordered[-1], field_name))
            if change is not None:
                changes.append(change)
        result[label] = {
            "comparable_keys": len(changes),
            "revision_gt_1_pct": sum(change > 0.01 for change in changes),
            "revision_gt_5_pct": sum(change > 0.05 for change in changes),
            "revision_gt_1_pct_share": (
                sum(change > 0.01 for change in changes) / len(changes) if changes else None
            ),
            "revision_gt_5_pct_share": (
                sum(change > 0.05 for change in changes) / len(changes) if changes else None
            ),
        }
    return result
