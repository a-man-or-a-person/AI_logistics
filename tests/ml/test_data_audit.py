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
            "nanos": "0",
            "units": "12000",
            "price_type": "tender",
            "route_length": "200",
            "route_type": "default",
            "tonnage_id": "7",
            "vehicle_body_type": "tent truck",
            "currency": "RUB",
            "tech_load_ts": "2026-01-15 12:30:00",
        }
    )
    row.update(overrides)
    return row


def test_loader_maps_units_to_price_and_bids_to_trip_count(tmp_path):
    source = tmp_path / "pulse.csv"
    _write_csv(source, [_row()])

    record = next(iter_records(source))

    assert record.source == "pulse"
    assert record.destination_fias == "destination-1"
    assert record.price == 12000
    assert record.trip_count == 3
    assert record.rub_per_km == 60
    assert record.latitude is None
    assert record.route_type == "default"
    assert record.tech_ts.isoformat() == "2026-01-15T12:30:00"
    assert record.nanos == 0
    assert record.validation_errors == ()


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
    assert report["invalid_values"] == {"route_length_zero": 1}
    assert report["price"]["median"] == 12000
    assert report["price"]["min"] == 0
    assert report["periods"]["tech_ts_range"]["min"] == "2026-01-15T12:30:00"
    assert report["route_history"]["routes_seen_1_month"] == 2
    assert report["schema"]["source_column_count"] == 25
    assert report["clustering"]["status"] == "current_milestone"
    assert report["trips_per_destination"]["count"] == 2
    assert json_path.exists()
    assert csv_path.exists()


def test_loader_distinguishes_invalid_values_from_source_nulls(tmp_path):
    source = tmp_path / "pulse.csv"
    _write_csv(
        source,
        [
            _row(
                units="broken",
                route_length="?",
                bid_count="many",
                nanos="fraction",
                period_id="January",
                tech_load_ts="not-a-timestamp",
            )
        ],
    )

    record = next(iter_records(source))
    report = audit_file(source)

    assert record.price is None
    assert record.trip_count is None
    assert record.route_length is None
    assert set(record.validation_errors) == {
        "invalid_units",
        "invalid_route_length",
        "invalid_bid_count",
        "invalid_nanos",
        "invalid_period_id",
        "invalid_tech_load_ts",
    }
    assert report["nulls"]["price"]["count"] == 1
    assert report["parse_errors"] == {error: 1 for error in record.validation_errors}
