"""Registry and readiness semantics for E0, E1, E2, E3 and ATI_REF."""

from __future__ import annotations

from collections.abc import Callable

from ml.evaluation.contracts import EvaluationRow, Prediction, VariantResult
from ml.evaluation.metrics import calculate_metrics, segment_metrics


class EvaluationVariant:
    name = "BASE"
    required_fields: tuple[str, ...] = ()
    blocker = "required inputs are unavailable"

    def value(self, row: EvaluationRow) -> float | None:
        raise NotImplementedError

    def predict(self, dataset: list[EvaluationRow]) -> VariantResult:
        predictions = tuple(
            Prediction(
                variant=self.name,
                key=row.key,
                predicted_price=self.value(row),
                status="predicted" if self.value(row) is not None else "unavailable",
                reason=None if self.value(row) is not None else self.blocker,
            )
            for row in dataset
        )
        available = [item for item in predictions if item.predicted_price is not None]
        total_qty = sum(max(row.qty or 0, 0) for row in dataset)
        available_keys = {item.key for item in available}
        available_qty = sum(max(row.qty or 0, 0) for row in dataset if row.key in available_keys)
        coverage = available_qty / total_qty if total_qty else 0.0
        if not available:
            return VariantResult(
                variant=self.name,
                status="blocked",
                predictions=predictions,
                metrics=None,
                coverage=coverage,
                blocker=self.blocker,
                required_fields=self.required_fields,
            )
        prediction_list = list(predictions)
        return VariantResult(
            variant=self.name,
            status="evaluated",
            predictions=predictions,
            metrics=calculate_metrics(dataset, prediction_list),
            coverage=coverage,
            required_fields=self.required_fields,
            segment_metrics=segment_metrics(dataset, prediction_list),
        )


class E0Variant(EvaluationVariant):
    name = "E0"
    required_fields = ("pulse_price",)
    blocker = "no matched Pulse price at the evaluation grain"

    def value(self, row: EvaluationRow) -> float | None:
        return row.pulse_price


class E0TripWeightedVariant(EvaluationVariant):
    name = "E0_trip_weighted"
    required_fields = ("pulse_trip_weighted_price",)
    blocker = "no bid-weighted Pulse price at the evaluation grain"

    def value(self, row: EvaluationRow) -> float | None:
        return row.pulse_trip_weighted_price


class E1Variant(EvaluationVariant):
    name = "E1"
    required_fields = ("pulse_rub_per_km", "trusted_distance_km")
    blocker = "trusted distance is unavailable"

    def value(self, row: EvaluationRow) -> float | None:
        if row.pulse_rub_per_km is None or row.distance_km is None:
            return None
        return row.pulse_rub_per_km * row.distance_km


class E2Variant(EvaluationVariant):
    name = "E2"
    required_fields = ("destination_fias_or_route_mix", "cluster_price")
    blocker = "actual ground truth has destination_region but no destination point/FIAS"

    def value(self, row: EvaluationRow) -> float | None:
        if row.destination_fias is None or row.cluster_id is None:
            return None
        return row.cluster_price


class E3Variant(EvaluationVariant):
    name = "E3"
    required_fields = (
        "destination_fias_or_route_mix",
        "cluster_rub_per_km",
        "trusted_distance_km",
    )
    blocker = "trusted distance and destination-level ground truth/route mix are unavailable"

    def value(self, row: EvaluationRow) -> float | None:
        if (
            row.destination_fias is None
            or row.cluster_id is None
            or row.cluster_rub_per_km is None
            or row.distance_km is None
        ):
            return None
        return row.cluster_rub_per_km * row.distance_km


class ATIReferenceVariant(EvaluationVariant):
    name = "ATI_REF"
    required_fields = ("market_rub_per_item",)
    blocker = "embedded ATI/market reference is unavailable"

    def __init__(self, horizon: int | None = None) -> None:
        self.horizon = horizon

    def value(self, row: EvaluationRow) -> float | None:
        if self.horizon is not None:
            return row.market_by_horizon.get(self.horizon)
        return row.market_rub_per_item


VARIANT_REGISTRY: dict[str, Callable[[], EvaluationVariant]] = {
    "E0": E0Variant,
    "E0_trip_weighted": E0TripWeightedVariant,
    "E1": E1Variant,
    "E2": E2Variant,
    "E3": E3Variant,
    "ATI_REF": ATIReferenceVariant,
}


def evaluate_variants(
    dataset: list[EvaluationRow], names: tuple[str, ...] | None = None
) -> dict[str, VariantResult]:
    selected = names or tuple(VARIANT_REGISTRY)
    unknown = sorted(set(selected) - set(VARIANT_REGISTRY))
    if unknown:
        raise ValueError(f"Unknown variants: {', '.join(unknown)}")
    return {name: VARIANT_REGISTRY[name]().predict(dataset) for name in selected}
