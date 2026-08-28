from dataclasses import replace

from ml.data.actual import ActualSnapshotRecord
from ml.data.ground_truth import build_ground_truth, snapshot_revision_report


def _snapshot():
    return ActualSnapshotRecord(
        snapshot_month="2026-04",
        shipment_month="2026-06",
        horizon_months=2,
        month_label="M2",
        origin_external_name="Factory A",
        origin_town="Town A",
        destination_region="Region A",
        qty_total=2,
        net_weight_total=20,
        qty_auction=1,
        auction_percent=0.5,
        fact_rub_total=1800,
        fact_rub_per_item=900,
        market_rub_total=1700,
        market_rub_per_item=850,
        market_spread=0.05,
        tech_load_ts=None,
        source_filename="synthetic.csv",
        source_loaded_at=None,
    )


def test_ground_truth_collapses_snapshots_to_latest_fact():
    first = _snapshot()
    final = replace(
        first,
        snapshot_month="2026-07",
        horizon_months=-1,
        month_label="M-1",
        fact_rub_total=2000,
        fact_rub_per_item=1000,
        market_rub_per_item=900,
    )

    result = build_ground_truth([first, final])

    assert len(result) == 1
    assert result[0].fact_rub_per_item == 1000
    assert result[0].target_snapshot_month == "2026-07"
    assert result[0].target_status == "final_post_shipment"


def test_revision_report_detects_material_change():
    first = _snapshot()
    final = replace(first, snapshot_month="2026-06", horizon_months=0, fact_rub_per_item=1000)

    report = snapshot_revision_report([first, final])

    assert report["fact"]["revision_gt_5_pct"] == 1
