from ml.data.pulse_evaluation import PulseEvaluationRecord
from ml.evaluation.economic import evaluate_rates


def _record(destination, price, distance, period="train"):
    return PulseEvaluationRecord(
        origin_fias="origin",
        destination_fias=destination,
        destination_region="Region",
        period_id=period,
        period_type="retro",
        price=price,
        route_length=distance,
        bid_count=1,
        price_type="tender",
        source_snapshot_time=None,
        origin_name="Origin",
        destination_name=destination,
    )


def test_cluster_rates_improve_when_geographic_groups_have_different_economics():
    train = [_record("a", 100, 10), _record("b", 200, 10)]
    test = [_record("a", 100, 10, "test"), _record("b", 200, 10, "test")]

    report, predictions = evaluate_rates(train, test, {"a": 0, "b": 1})

    assert report["overall"]["cluster"]["wape_pct"] == 0
    assert report["overall"]["regional"]["wape_pct"] > 0
    assert report["overall"]["relative_wape_improvement_pct"] == 100
    assert len(predictions) == 2


def test_unresolved_destinations_are_reported_not_silently_fallbacked():
    train = [_record("a", 100, 10)]
    test = [_record("missing", 100, 10, "test")]

    report, predictions = evaluate_rates(train, test, {"a": 0})

    assert predictions == []
    assert report["coverage"]["unmatched_rows"] == 1
