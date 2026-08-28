import csv

import pytest

from ml.data.actual import ACTUAL_COLUMNS, iter_actual_snapshots


def _row(**overrides):
    row = {column: "" for column in ACTUAL_COLUMNS}
    row.update(
        {
            "current_month": "2026-04",
            "shipment_date_month": "2026-06",
            "month_label": "M2",
            "shipment_point_name": "Factory A",
            "shipment_point_name_town": "Town A",
            "delivery_point_name": "Region A",
            "qty_total": "2",
            "net_weight_total": "20",
            "qty_auction": "1",
            "auction_percent": "0.5",
            "fact_rub_total": "2000",
            "market_rub_total": "1800",
            "fact_rub_per_item": "1000",
            "market_rub_per_item": "900",
            "market_spread": "0.1111",
            "tech_load_ts": "2026-04-01 00:00:00",
            "filename": "synthetic.csv",
            "tech_load_ts_core": "2026-04-01 00:01:00",
        }
    )
    row.update(overrides)
    return row


def _write(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=ACTUAL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def test_actual_loader_validates_horizon_and_numeric_contract(tmp_path):
    path = tmp_path / "actual.csv"
    _write(path, [_row()])

    record = list(iter_actual_snapshots(path))[0]

    assert record.horizon_months == 2
    assert record.month_label == "M2"
    assert record.auction_percent == 0.5
    assert record.actual_origin_id.startswith("actual_")


def test_actual_loader_rejects_wrong_label_and_duplicate_key(tmp_path):
    wrong = tmp_path / "wrong.csv"
    _write(wrong, [_row(month_label="M1")])
    with pytest.raises(ValueError, match="month_label"):
        list(iter_actual_snapshots(wrong))

    duplicate = tmp_path / "duplicate.csv"
    _write(duplicate, [_row(), _row()])
    with pytest.raises(ValueError, match="duplicate natural snapshot key"):
        list(iter_actual_snapshots(duplicate))
