import pytest

from ml.data.ground_truth import EvaluationKey
from ml.evaluation.contracts import EvaluationRow, Prediction
from ml.evaluation.metrics import calculate_metrics, common_intersection


def test_weighted_metrics_match_hand_calculation():
    first = EvaluationRow(EvaluationKey("2026-01", "a", "r"), 100, 1)
    second = EvaluationRow(EvaluationKey("2026-02", "a", "r"), 200, 3)
    predictions = [
        Prediction("E0", first.key, 110, "predicted"),
        Prediction("E0", second.key, 180, "predicted"),
    ]

    metrics = calculate_metrics([first, second], predictions)

    assert metrics.wape_pct == 10
    assert metrics.weighted_mae_rub_per_item == 17.5
    assert metrics.mdape_pct == 10
    assert metrics.bias_pct == pytest.approx(-100 * 50 / 700)
    assert metrics.within_10_pct == 100
    assert metrics.within_20_pct == 100


def test_metrics_ignore_zero_denominator_and_intersection_is_paired():
    valid = EvaluationRow(EvaluationKey("2026-01", "a", "r"), 100, 1)
    invalid = EvaluationRow(EvaluationKey("2026-02", "a", "r"), 0, 1)
    baseline = [Prediction("E0", valid.key, 90, "predicted")]
    challenger = [
        Prediction("E1", valid.key, 95, "predicted"),
        Prediction("E1", invalid.key, 10, "predicted"),
    ]

    assert calculate_metrics([valid, invalid], challenger).n_evaluation_cells == 1
    assert common_intersection(baseline, challenger) == {valid.key}
