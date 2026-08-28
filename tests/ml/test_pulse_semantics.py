import csv
from dataclasses import fields

from ml.data.loader import PULSE_COLUMNS, iter_records
from ml.data.pulse_raw import PulseRawRecord, iter_raw_records


def _write(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _row(**changes):
    row = {column: "" for column in PULSE_COLUMNS}
    row.update(
        {
            "shipment_point_locality_fias_id": "origin-a",
            "shipment_point_name_town": "Factory A",
            "delivery_point_locality_fias_id": "destination-a",
            "delivery_point_region_unified": "Region A",
            "delivery_point_town": "Town A",
            "period_id": "202601",
            "period_type": "current",
            "units": "17.5",
            "bid_count": "900",
            "confidence": "derived",
            "route_length": "100",
            "price_type": "tender",
        }
    )
    row.update(changes)
    return row


def test_raw_contract_contains_exact_source_columns(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(source, [_row()])

    raw = next(iter_raw_records(source))

    assert isinstance(raw, PulseRawRecord)
    assert {field.name for field in fields(raw)} == set(PULSE_COLUMNS)
    assert raw.units == "17.5"
    assert raw.bid_count == "900"


def test_units_are_shipments_while_bid_and_confidence_stay_diagnostic(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(source, [_row()])

    record = next(iter_records(source))

    assert record.shipment_count == 17.5
    assert record.pulse_bid_count == 900
    assert record.pulse_confidence == "derived"
    assert not hasattr(record, "price")
    assert not hasattr(record, "trip_count")
