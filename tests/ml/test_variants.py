import pytest

from ml.data.ground_truth import EvaluationKey
from ml.evaluation.contracts import EvaluationRow, validate_prediction_features
from ml.evaluation.variants import evaluate_variants


def test_variants_calculate_e0_e1_e2_e3_when_inputs_exist():
    row = EvaluationRow(
        key=EvaluationKey("2026-06", "actual-a", "region a"),
        actual_price=50000,
        qty=2,
        pulse_price=49000,
        pulse_trip_weighted_price=49500,
        pulse_rub_per_km=50,
        distance_km=1000,
        destination_fias="destination-a",
        cluster_id=0,
        cluster_price=50000,
        cluster_rub_per_km=50,
        market_rub_per_item=48000,
    )

    results = evaluate_variants([row])

    assert results["E0"].predictions[0].predicted_price == 49000
    assert results["E0_trip_weighted"].predictions[0].predicted_price == 49500
    assert results["E1"].predictions[0].predicted_price == 50000
    assert results["E2"].predictions[0].predicted_price == 50000
    assert results["E3"].predictions[0].predicted_price == 50000
    assert all(results[name].status == "evaluated" for name in ("E0", "E1", "E2", "E3"))


def test_missing_distance_and_destination_grain_return_clean_blockers():
    row = EvaluationRow(
        EvaluationKey("2026-06", "actual-a", "region a"),
        1000,
        1,
        pulse_price=900,
        pulse_rub_per_km=10,
    )

    results = evaluate_variants([row])

    assert results["E1"].status == "blocked"
    assert "trusted distance" in str(results["E1"].blocker)
    assert results["E2"].status == "blocked"
    assert "destination point/FIAS" in str(results["E2"].blocker)


def test_leakage_fields_are_rejected_centrally():
    with pytest.raises(ValueError, match="market_spread"):
        validate_prediction_features({"origin", "market_spread", "fact_rub_per_item"})
