"""One quantity-weighted metric engine for every evaluation variant."""

from __future__ import annotations

import math
import random
import statistics
from collections import defaultdict
from collections.abc import Callable, Iterable
from typing import Any

from ml.data.ground_truth import EvaluationKey
from ml.evaluation.contracts import EvaluationMetrics, EvaluationRow, Prediction


def _comparable(
    rows: Iterable[EvaluationRow], predictions: Iterable[Prediction]
) -> list[tuple[EvaluationRow, Prediction]]:
    row_by_key = {row.key: row for row in rows}
    result: list[tuple[EvaluationRow, Prediction]] = []
    for prediction in predictions:
        row = row_by_key.get(prediction.key)
        if (
            row is None
            or row.actual_price is None
            or row.actual_price <= 0
            or row.qty is None
            or row.qty <= 0
            or prediction.predicted_price is None
            or not math.isfinite(prediction.predicted_price)
        ):
            continue
        result.append((row, prediction))
    return result


def calculate_metrics(
    rows: Iterable[EvaluationRow], predictions: Iterable[Prediction]
) -> EvaluationMetrics:
    comparable = _comparable(rows, predictions)
    if not comparable:
        return EvaluationMetrics(0, 0.0, None, None, None, None, None, None)

    qty = sum(float(row.qty) for row, _ in comparable)
    absolute_error = sum(
        float(row.qty) * abs(float(prediction.predicted_price) - float(row.actual_price))
        for row, prediction in comparable
    )
    actual_total = sum(float(row.qty) * float(row.actual_price) for row, _ in comparable)
    signed_error = sum(
        float(row.qty) * (float(prediction.predicted_price) - float(row.actual_price))
        for row, prediction in comparable
    )
    ape = [
        100 * abs(float(prediction.predicted_price) - float(row.actual_price)) / float(row.actual_price)
        for row, prediction in comparable
    ]
    within_10_qty = sum(
        float(row.qty) for (row, _), value in zip(comparable, ape, strict=True) if value <= 10
    )
    within_20_qty = sum(
        float(row.qty) for (row, _), value in zip(comparable, ape, strict=True) if value <= 20
    )
    return EvaluationMetrics(
        n_evaluation_cells=len(comparable),
        qty_evaluated=qty,
        wape_pct=100 * absolute_error / actual_total if actual_total else None,
        weighted_mae_rub_per_item=absolute_error / qty if qty else None,
        mdape_pct=statistics.median(ape),
        bias_pct=100 * signed_error / actual_total if actual_total else None,
        within_10_pct=100 * within_10_qty / qty if qty else None,
        within_20_pct=100 * within_20_qty / qty if qty else None,
    )


def common_intersection(
    *prediction_sets: Iterable[Prediction],
) -> set[EvaluationKey]:
    available = [
        {item.key for item in predictions if item.predicted_price is not None}
        for predictions in prediction_sets
    ]
    return set.intersection(*available) if available else set()


def filter_predictions(
    predictions: Iterable[Prediction], keys: set[EvaluationKey]
) -> list[Prediction]:
    return [item for item in predictions if item.key in keys]


def segment_metrics(
    rows: list[EvaluationRow], predictions: list[Prediction]
) -> dict[str, dict[str, dict[str, Any]]]:
    prediction_by_key = {item.key: item for item in predictions}
    quantities = sorted(float(row.qty) for row in rows if row.qty is not None and row.qty > 0)
    thresholds = (
        quantities[len(quantities) // 4],
        quantities[len(quantities) // 2],
        quantities[(3 * len(quantities)) // 4],
    ) if quantities else (0.0, 0.0, 0.0)

    def volume_quantile(row: EvaluationRow) -> str:
        value = float(row.qty or 0)
        if value <= thresholds[0]:
            return "Q1"
        if value <= thresholds[1]:
            return "Q2"
        if value <= thresholds[2]:
            return "Q3"
        return "Q4"

    def auction_bin(row: EvaluationRow) -> str:
        value = row.auction_percent
        if value is None:
            return "missing"
        if value == 0:
            return "0"
        if value <= 0.25:
            return "(0,0.25]"
        if value <= 0.5:
            return "(0.25,0.5]"
        if value <= 0.75:
            return "(0.5,0.75]"
        return "(0.75,1]"

    dimensions: dict[str, Callable[[EvaluationRow], str]] = {
        "shipment_month": lambda row: row.key.shipment_month,
        "origin": lambda row: row.key.actual_origin_id,
        "destination_region": lambda row: row.key.destination_region,
        "target_horizon": lambda row: f"M{row.target_horizon}" if row.target_horizon is not None else "missing",
        "volume_quantile": volume_quantile,
        "auction_percent_posthoc": auction_bin,
    }
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for name, selector in dimensions.items():
        groups: dict[str, list[EvaluationRow]] = defaultdict(list)
        for row in rows:
            groups[selector(row)].append(row)
        result[name] = {}
        for label, grouped_rows in sorted(groups.items()):
            grouped_predictions = [
                prediction_by_key[row.key]
                for row in grouped_rows
                if row.key in prediction_by_key
            ]
            result[name][label] = calculate_metrics(grouped_rows, grouped_predictions).as_dict()
    return result


def paired_bootstrap_wape_delta(
    rows: list[EvaluationRow],
    baseline: list[Prediction],
    challenger: list[Prediction],
    *,
    iterations: int = 1000,
    seed: int = 42,
) -> dict[str, float | int | None]:
    keys = common_intersection(baseline, challenger)
    paired_rows = [row for row in rows if row.key in keys]
    if not paired_rows or iterations <= 0:
        return {"pairs": 0, "delta_wape_pct": None, "ci_low": None, "ci_high": None}
    baseline_by_key = {item.key: item for item in baseline}
    challenger_by_key = {item.key: item for item in challenger}
    rng = random.Random(seed)
    deltas: list[float] = []
    for _ in range(iterations):
        sample = [rng.choice(paired_rows) for _ in paired_rows]
        baseline_sample = [baseline_by_key[row.key] for row in sample]
        challenger_sample = [challenger_by_key[row.key] for row in sample]
        baseline_wape = calculate_metrics(sample, baseline_sample).wape_pct
        challenger_wape = calculate_metrics(sample, challenger_sample).wape_pct
        if baseline_wape is not None and challenger_wape is not None:
            deltas.append(challenger_wape - baseline_wape)
    if not deltas:
        return {"pairs": len(paired_rows), "delta_wape_pct": None, "ci_low": None, "ci_high": None}
    deltas.sort()
    low_index = max(0, int(0.025 * (len(deltas) - 1)))
    high_index = min(len(deltas) - 1, int(0.975 * (len(deltas) - 1)))
    baseline_wape = calculate_metrics(
        paired_rows, [baseline_by_key[row.key] for row in paired_rows]
    ).wape_pct
    challenger_wape = calculate_metrics(
        paired_rows, [challenger_by_key[row.key] for row in paired_rows]
    ).wape_pct
    return {
        "pairs": len(paired_rows),
        "delta_wape_pct": (
            challenger_wape - baseline_wape
            if baseline_wape is not None and challenger_wape is not None
            else None
        ),
        "ci_low": deltas[low_index],
        "ci_high": deltas[high_index],
    }
