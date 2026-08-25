import csv
from pathlib import Path

from ml.data.actual import ACTUAL_COLUMNS, stable_origin_id
from ml.data.cluster_assignments import CLUSTER_ASSIGNMENT_COLUMNS
from ml.data.distance import DISTANCE_COLUMNS
from ml.data.loader import PULSE_COLUMNS
from ml.data.matching import ORIGIN_MAPPING_COLUMNS
from ml.experiments.compare_variants import run_comparison


def _write(path, columns, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _actual_row(origin, town, region, snapshot, shipment, label):
    row = {column: "" for column in ACTUAL_COLUMNS}
    row.update(
        {
            "current_month": snapshot,
            "shipment_date_month": shipment,
            "month_label": label,
            "shipment_point_name": origin,
            "shipment_point_name_town": town,
            "delivery_point_name": region,
            "qty_total": "2",
            "net_weight_total": "20",
            "qty_auction": "1",
            "auction_percent": "0.5",
            "fact_rub_total": "2000",
            "market_rub_total": "1800",
            "fact_rub_per_item": "1000",
            "market_rub_per_item": "900",
            "market_spread": "0.1111",
            "filename": "synthetic.csv",
        }
    )
    return row


def _pulse_row(origin_fias, region, period):
    row = {column: "" for column in PULSE_COLUMNS}
    row.update(
        {
            "shipment_point_locality_fias_id": origin_fias,
            "shipment_point_region": "Origin Region",
            "shipment_point_town_source": origin_fias,
            "delivery_point_locality_fias_id": f"destination-{region}",
            "delivery_point_region_unified": region,
            "delivery_point_town": "Destination",
            "period_id": period.replace("-", ""),
            "period_type": "current",
            "bid_count": "2",
            "units": "1000",
            "price_type": "spot",
            "route_length": "100",
        }
    )
    return row


def test_synthetic_pipeline_calculates_all_variants(tmp_path):
    actual = tmp_path / "actual.csv"
    pulse = tmp_path / "pulse.csv"
    mapping = tmp_path / "mapping.csv"
    distance = tmp_path / "distance.csv"
    clusters = tmp_path / "clusters.csv"
    output = tmp_path / "reports" / "private" / "evaluation"
    origins = [(f"Factory {name}", f"Town {name}", f"pulse-{name.lower()}") for name in "ABC"]
    regions = ["Region A", "Region B"]
    months = [
        ("2026-01", "2025-12"),
        ("2026-02", "2026-01"),
        ("2026-03", "2026-02"),
        ("2026-04", "2026-03"),
    ]

    actual_rows = []
    pulse_rows = []
    mapping_rows = []
    distance_rows = []
    cluster_rows = []
    for origin, town, pulse_fias in origins:
        origin_id = stable_origin_id(origin)
        mapping_rows.append(
            {
                "actual_origin_id": origin_id,
                "actual_origin_town": town,
                "pulse_origin_fias": pulse_fias,
                "pulse_origin_name": town,
                "match_method": "manual",
                "match_status": "matched",
                "confidence": "1",
                "mapping_version": "synthetic-v1",
            }
        )
        for region in regions:
            for shipment, previous in months:
                actual_rows.extend(
                    [
                        _actual_row(origin, town, region, previous, shipment, "M1"),
                        _actual_row(origin, town, region, shipment, shipment, "M0"),
                    ]
                )
                pulse_rows.append(_pulse_row(pulse_fias, region, shipment))
                distance_rows.append(
                    {
                        "origin_fias": pulse_fias,
                        "destination_region": region,
                        "destination_fias": "",
                        "shipment_month": shipment,
                        "distance_km": "100",
                        "source": "manual_verified",
                        "confidence": "1",
                    }
                )
                cluster_rows.append(
                    {
                        "shipment_month": shipment,
                        "actual_origin_id": origin_id,
                        "destination_region": region,
                        "destination_fias": f"destination-{region}",
                        "cluster_id": "0",
                        "cluster_price": "1000",
                        "cluster_rub_per_km": "10",
                    }
                )

    _write(actual, ACTUAL_COLUMNS, actual_rows)
    _write(pulse, PULSE_COLUMNS, pulse_rows)
    _write(mapping, ORIGIN_MAPPING_COLUMNS, mapping_rows)
    _write(distance, DISTANCE_COLUMNS, distance_rows)
    _write(clusters, CLUSTER_ASSIGNMENT_COLUMNS, cluster_rows)

    report = run_comparison(
        actual_path=actual,
        pulse_path=pulse,
        mapping_path=mapping,
        output_dir=output,
        distance_path=distance,
        cluster_assignments_path=clusters,
        price_types={"spot"},
        period_types={"current"},
        bootstrap_iterations=20,
    )

    assert report["rows"] == 24
    assert all(report["results"][name].status == "evaluated" for name in ("E0", "E1", "E2", "E3"))
    assert all(report["results"][name].metrics.wape_pct == 0 for name in ("E0", "E1", "E2", "E3"))
    for relative in (
        "run_metadata.json",
        "data_quality.json",
        "coverage.json",
        "leaderboard.csv",
        "decision_gate_actual.json",
        "ati_reference/by_horizon.csv",
    ):
        assert (output / Path(relative)).exists()
