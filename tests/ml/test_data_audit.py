import csv

from ml.data.audit import audit_file, write_reports
from ml.data.loader import PULSE_COLUMNS, iter_records


def _write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _row(**overrides):
    row = {column: "" for column in PULSE_COLUMNS}
    row.update(
        {
            "shipment_point_locality_fias_id": "origin-1",
            "shipment_point_region": "Origin region",
            "shipment_point_name_town": "Origin town",
            "delivery_point_locality_fias_id": "destination-1",
            "delivery_point_region_unified": "Destination region",
            "delivery_point_town": "Destination town",
            "period_id": "202601",
            "period_type": "retro",
            "bid_count": "3",
            "confidence": "medium",
            "units": "12000",
            "price_type": "tender",
            "route_length": "200",
            "tonnage_id": "7",
            "vehicle_body_type": "tent truck",
            "currency": "RUB",
        }
    )
    row.update(overrides)
    return row


def test_loader_builds_canonical_record_and_calculates_rub_per_km(tmp_path):
    source = tmp_path / "pulse.csv"
    _write_csv(source, [_row()])

    record = next(iter_records(source))

    assert record.source == "pulse"
    assert record.destination_fias == "destination-1"
    assert record.trip_count == 3
    assert record.rub_per_km == 60
    assert record.latitude is None


def test_audit_reports_quality_metrics_and_writes_both_formats(tmp_path):
    source = tmp_path / "pulse.csv"
    duplicate = _row()
    invalid = _row(
        delivery_point_locality_fias_id="NULL",
        delivery_point_town="Other town",
        bid_count="2",
        units="0",
        route_length="0",
    )
    _write_csv(source, [duplicate, duplicate, invalid])

    report = audit_file(source)
    json_path, csv_path = write_reports(report, tmp_path / "reports")

    assert report["rows"]["total"] == 3
    assert report["rows"]["duplicates"] == 1
    assert report["entities"]["unique_destination_fias"] == 1
    assert report["nulls"]["destination_fias"]["count"] == 1
    assert report["invalid_values"] == {"price_le_zero": 1, "route_length_le_zero": 1}
    assert report["rub_per_km"]["median"] == 60
    assert report["trips_per_destination"]["count"] == 2
    assert json_path.exists()
    assert csv_path.exists()
