import hashlib
import json

import pytest

from ml.experiments.boundary_audit import audit_boundary


def test_boundary_audit_checks_manifest_and_shipment_coverage(tmp_path):
    boundary = tmp_path / "boundary.geojson"
    boundary.write_text(
        json.dumps({"type": "Polygon", "coordinates": [[[30, 59.9], [30.2, 59.9], [30.2, 60], [30, 60], [30, 59.9]]]}),
        encoding="utf-8",
    )
    locations = tmp_path / "locations.json"
    locations.write_text(
        json.dumps(
            [
                {"latitude": 59.95, "longitude": 30.1, "shipment_count": 9},
                {"latitude": 60.5, "longitude": 30.1, "shipment_count": 1},
            ]
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "boundary_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "region": "Region A",
                "authority": "Rosreestr / NSPD",
                "source_type": "EGRN/NSPD",
                "retrieved_at": "2026-08-28",
                "effective_date": "2026-08-01",
                "crs": "EPSG:4326",
                "sha256": hashlib.sha256(boundary.read_bytes()).hexdigest(),
                "status": "official",
            }
        ),
        encoding="utf-8",
    )

    report = audit_boundary(
        boundary, locations, manifest_path=manifest, require_official=True
    )

    assert report["destination_points_inside"] == 1
    assert report["destination_points_outside"] == 1
    assert report["shipment_coverage_inside_pct"] == 90
    assert report["manifest"]["status"] == "official"


def test_production_boundary_rejects_unknown_provenance(tmp_path):
    boundary = tmp_path / "boundary.geojson"
    boundary.write_text(
        json.dumps({"type": "Polygon", "coordinates": [[[30, 59.9], [30.2, 59.9], [30.2, 60], [30, 60], [30, 59.9]]]}),
        encoding="utf-8",
    )
    locations = tmp_path / "locations.json"
    locations.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="provenance manifest"):
        audit_boundary(boundary, locations, require_official=True)
