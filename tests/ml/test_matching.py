from dataclasses import replace

from ml.data.actual import ActualSnapshotRecord
from ml.data.matching import build_origin_candidates
from ml.data.pulse_registry import PulseOrigin


def _snapshot(name="Factory A", town="Town A"):
    return ActualSnapshotRecord(
        snapshot_month="2026-06",
        shipment_month="2026-06",
        horizon_months=0,
        month_label="M0",
        origin_external_name=name,
        origin_town=town,
        destination_region="Region A",
        qty_total=1,
        net_weight_total=1,
        qty_auction=0,
        auction_percent=0,
        fact_rub_total=100,
        fact_rub_per_item=100,
        market_rub_total=90,
        market_rub_per_item=90,
        market_spread=0.1,
        tech_load_ts=None,
        source_filename="synthetic.csv",
        source_loaded_at=None,
    )


def _pulse(fias="pulse-a", town="Town A"):
    return PulseOrigin(fias, town, town, "Origin Region", None, None)


def test_unique_town_is_auto_matched():
    result = build_origin_candidates([_snapshot()], [_pulse()])

    assert result[0].match_status == "matched"
    assert result[0].pulse_origin_fias == "pulse-a"


def test_ambiguous_town_is_not_auto_matched():
    first = _snapshot()
    second = replace(first, origin_external_name="Factory B")

    result = build_origin_candidates([first, second], [_pulse(), _pulse("pulse-b")])

    assert {item.match_status for item in result} == {"ambiguous"}
    assert all(item.pulse_origin_fias is None for item in result)
