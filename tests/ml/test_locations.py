import csv
import json

from ml.data.loader import PULSE_COLUMNS
from ml.data.locations import build_location_dataset


def _write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _row(fias, name, bids, units="1000", distance="100", period_type="current"):
    row = {column: "" for column in PULSE_COLUMNS}
    row.update(
        {
            "shipment_point_locality_fias_id": "origin-1",
            "shipment_point_region": "Origin",
            "delivery_point_locality_fias_id": fias,
            "delivery_point_region_unified": "Ленинградская область",
            "delivery_point_town": name,
            "period_id": "202608",
            "period_type": period_type,
            "bid_count": str(bids),
            "units": units,
            "price_type": "tender",
            "route_length": distance,
        }
    )
    return row


def test_locations_are_unique_by_fias_and_do_not_use_region_center(tmp_path):
    source = tmp_path / "pulse.csv"
    cache = tmp_path / "cache.json"
    _write_csv(
        source,
        [
            _row("fias-1", "г Тихвин", 2),
            _row("fias-1", "г Тихвин", 3, units="1200"),
            _row("fias-2", "Неизвестный", 4),
        ],
    )
    cache.write_text(
        json.dumps({"г Тихвин::Ленинградская область": [59.64, 33.54]}), encoding="utf-8"
    )

    points, report = build_location_dataset(source, coordinate_cache_path=cache)

    assert len(points) == 2
    assert points[0].shipment_count == 2200
    assert points[0].coordinate_source == "cache_exact"
    assert points[1].latitude is None
    assert report["coordinates"]["location_coverage_pct"] == 50
    assert report["coordinates"]["shipment_coverage_pct"] == 68.75
    assert report["contract"]["region_center_fallback"] is False


def test_missing_fias_uses_explicit_name_region_fallback(tmp_path):
    source = tmp_path / "pulse.csv"
    cache = tmp_path / "cache.json"
    _write_csv(source, [_row("", "поселок Тестовый", 1)])
    cache.write_text("{}", encoding="utf-8")

    points, report = build_location_dataset(
        source, coordinate_cache_path=cache, allow_name_fallback=True
    )

    assert points[0].id_source == "name_region_fallback"
    assert points[0].id.startswith("fallback:")
    assert report["locations"]["fallback"] == 1
