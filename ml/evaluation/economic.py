"""Out-of-time regional-rate versus cluster-rate evaluation."""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from ml.data.pulse_evaluation import PulseEvaluationRecord


@dataclass(slots=True)
class WeightedRate:
    price_sum: float = 0
    distance_sum: float = 0

    def add(self, record: PulseEvaluationRecord) -> None:
        if record.price is None or record.route_length is None:
            return
        if record.price <= 0 or record.route_length <= 0:
            return
        weight = max(record.bid_count or 0, 1)
        self.price_sum += record.price * weight
        self.distance_sum += record.route_length * weight

    @property
    def rub_per_km(self) -> float | None:
        return self.price_sum / self.distance_sum if self.distance_sum else None


def prediction_metrics(
    rows: list[dict[str, Any]], prediction_field: str
) -> dict[str, float | int | None]:
    comparable = [
        row
        for row in rows
        if row.get(prediction_field) is not None
        and row.get("actual_price") is not None
        and row["actual_price"] > 0
    ]
    if not comparable:
        return {
            "rows": 0,
            "trip_weight": 0,
            "mae_rub": None,
            "wape_pct": None,
            "median_ape_pct": None,
            "bias_rub": None,
            "bias_pct": None,
            "within_10_pct": None,
            "within_20_pct": None,
        }
    total_weight = sum(row["weight"] for row in comparable)
    absolute_error = sum(
        abs(row[prediction_field] - row["actual_price"]) * row["weight"]
        for row in comparable
    )
    signed_error = sum(
        (row[prediction_field] - row["actual_price"]) * row["weight"]
        for row in comparable
    )
    actual_total = sum(row["actual_price"] * row["weight"] for row in comparable)
    percentage_errors = [
        100 * abs(row[prediction_field] - row["actual_price"]) / row["actual_price"]
        for row in comparable
    ]
    within_10_weight = sum(
        row["weight"]
        for row, percentage in zip(comparable, percentage_errors, strict=True)
        if percentage <= 10
    )
    within_20_weight = sum(
        row["weight"]
        for row, percentage in zip(comparable, percentage_errors, strict=True)
        if percentage <= 20
    )
    return {
        "rows": len(comparable),
        "trip_weight": total_weight,
        "mae_rub": round(absolute_error / total_weight, 4),
        "wape_pct": round(100 * absolute_error / actual_total, 4),
        "median_ape_pct": round(statistics.median(percentage_errors), 4),
        "bias_rub": round(signed_error / total_weight, 4),
        "bias_pct": round(100 * signed_error / actual_total, 4),
        "within_10_pct": round(100 * within_10_weight / total_weight, 4),
        "within_20_pct": round(100 * within_20_weight / total_weight, 4),
    }


def evaluate_rates(
    train_records: list[PulseEvaluationRecord],
    test_records: list[PulseEvaluationRecord],
    assignments: dict[str, int],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Fit rates on train only and evaluate route prices on later periods."""
    regional = WeightedRate()
    by_cluster: dict[int, WeightedRate] = defaultdict(WeightedRate)
    for record in train_records:
        regional.add(record)
        if record.destination_fias in assignments:
            by_cluster[assignments[record.destination_fias]].add(record)
    regional_rate = regional.rub_per_km
    cluster_rates = {
        cluster_id: accumulator.rub_per_km
        for cluster_id, accumulator in by_cluster.items()
        if accumulator.rub_per_km is not None
    }

    predictions: list[dict[str, Any]] = []
    unmatched_rows = 0
    unmatched_trip_weight = 0
    for record in test_records:
        if record.price is None or record.route_length is None:
            continue
        if record.price <= 0 or record.route_length <= 0:
            continue
        weight = max(record.bid_count or 0, 1)
        cluster_id = assignments.get(record.destination_fias or "")
        if cluster_id is None:
            unmatched_rows += 1
            unmatched_trip_weight += weight
            continue
        cluster_rate = cluster_rates.get(cluster_id)
        predictions.append(
            {
                "destination_fias": record.destination_fias,
                "destination_name": record.destination_name,
                "period_id": record.period_id,
                "cluster_id": cluster_id,
                "route_length": record.route_length,
                "weight": weight,
                "actual_price": record.price,
                "regional_rub_per_km": regional_rate,
                "cluster_rub_per_km": cluster_rate,
                "regional_prediction": (
                    regional_rate * record.route_length if regional_rate is not None else None
                ),
                "cluster_prediction": (
                    cluster_rate * record.route_length if cluster_rate is not None else None
                ),
            }
        )

    regional_metrics = prediction_metrics(predictions, "regional_prediction")
    cluster_metrics = prediction_metrics(predictions, "cluster_prediction")
    regional_wape = regional_metrics["wape_pct"]
    cluster_wape = cluster_metrics["wape_pct"]
    improvement = (
        100 * (float(regional_wape) - float(cluster_wape)) / float(regional_wape)
        if regional_wape not in {None, 0} and cluster_wape is not None
        else None
    )
    periods: dict[str, dict[str, Any]] = {}
    for period in sorted({row["period_id"] for row in predictions if row["period_id"]}):
        period_rows = [row for row in predictions if row["period_id"] == period]
        periods[str(period)] = {
            "regional": prediction_metrics(period_rows, "regional_prediction"),
            "cluster": prediction_metrics(period_rows, "cluster_prediction"),
        }
    report = {
        "rates": {
            "regional_rub_per_km": round(regional_rate, 4) if regional_rate else None,
            "cluster_rub_per_km": {
                str(key): round(float(value), 4) for key, value in sorted(cluster_rates.items())
            },
        },
        "coverage": {
            "matched_rows": len(predictions),
            "unmatched_rows": unmatched_rows,
            "unmatched_trip_weight": unmatched_trip_weight,
        },
        "overall": {
            "regional": regional_metrics,
            "cluster": cluster_metrics,
            "relative_wape_improvement_pct": round(improvement, 4) if improvement is not None else None,
        },
        "by_test_period": periods,
    }
    return report, predictions
