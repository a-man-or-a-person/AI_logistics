import pytest

from ml.data.distance import DistanceRecord
from ml.data.ground_truth import EvaluationKey, GroundTruthRecord
from ml.data.matching import OriginMapping
from ml.data.pulse_evaluation import PulseEvaluationRecord
from ml.evaluation.dataset import build_evaluation_dataset


def _pulse(price, distance, bids):
    return PulseEvaluationRecord(
        origin_fias="pulse-a",
        destination_fias="destination-a",
        destination_region="Region A",
        period_id="202606",
        period_type="current",
        price=price,
        route_length=distance,
        bid_count=bids,
        price_type="spot",
        source_snapshot_time="2026-06-01",
    )


def test_dataset_builds_e0_cells_and_coverage_on_canonical_grain():
    target = GroundTruthRecord(
        EvaluationKey("2026-06", "actual-a", "region a"),
        1000,
        2000,
        2,
        20,
        1,
        0.5,
        "2026-06",
        0,
        "m0_only",
        900,
        True,
        True,
    )
    mapping = OriginMapping(
        "actual-a", "Town A", "pulse-a", "Town A", "manual", "matched", 1.0, "v1"
    )
    distance = DistanceRecord(
        "pulse-a", "region a", None, "2026-06", 100, "manual_verified", 1.0
    )

    result = build_evaluation_dataset(
        [target],
        [_pulse(100, 10, 1), _pulse(300, 20, 3)],
        {"actual-a": mapping},
        distances=[distance],
        price_types={"spot"},
    )
    row = result.rows[0]

    assert row.pulse_price == 200
    assert row.pulse_trip_weighted_price == 250
    assert row.pulse_rub_per_km == pytest.approx(400 / 30)
    assert row.pulse_trip_weighted_rub_per_km == pytest.approx(1000 / 70)
    assert row.distance_km == 100
    assert result.coverage.final_evaluation_qty_coverage == 1
