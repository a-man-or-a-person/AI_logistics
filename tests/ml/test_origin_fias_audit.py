import csv

from ml.data.loader import PULSE_COLUMNS, iter_records
from ml.data.origin_mapping import build_origin_fias_candidates, normalize_town


def _row(name, fias, units):
    row = {column: "" for column in PULSE_COLUMNS}
    row.update(
        {
            "shipment_point_locality_fias_id": fias,
            "shipment_point_name_town": name,
            "delivery_point_locality_fias_id": "destination",
            "delivery_point_region_unified": "Region A",
            "delivery_point_town": "Town A",
            "period_id": "202601",
            "period_type": "current",
            "units": str(units),
            "bid_count": "999",
            "price_type": "tender",
            "route_length": "100",
        }
    )
    return row


def test_town_mapping_auto_matches_unique_and_escalates_ambiguity(tmp_path):
    source = tmp_path / "pulse.csv"
    with source.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(
            [
                _row("г. Орёл", "fias-a", 2),
                _row("г Орел", "fias-a", 3),
                _row("пос. Тест", "fias-b", 10),
                _row("п Тест", "fias-c", 20),
            ]
        )

    candidates = build_origin_fias_candidates(list(iter_records(source)))
    by_town = {candidate.normalized_town: candidate for candidate in candidates}

    assert normalize_town(" г. ОрЁл ") == "орел"
    assert by_town["орел"].status == "auto_unique"
    assert by_town["орел"].shipment_count == 5
    assert by_town["тест"].status == "manual_required"
    assert by_town["тест"].candidate_fias == ("fias-b", "fias-c")
    assert candidates[0].normalized_town == "тест"
