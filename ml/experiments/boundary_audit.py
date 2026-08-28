"""Validate boundary provenance and shipment-weighted point containment."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from pyproj import Geod
from shapely.geometry import Point

from ml.spatial.boundaries import load_region_boundary
from ml.spatial.boundary_manifest import load_boundary_manifest


def audit_boundary(
    boundary_path: str | Path,
    locations_path: str | Path,
    *,
    region_name: str | None = None,
    manifest_path: str | Path | None = None,
    require_official: bool = False,
) -> dict:
    boundary_source = Path(boundary_path)
    boundary = load_region_boundary(boundary_source, region_name=region_name)
    manifest = (
        load_boundary_manifest(
            manifest_path,
            boundary_path=boundary_source,
            require_official=require_official,
        )
        if manifest_path is not None
        else None
    )
    if require_official and manifest is None:
        raise ValueError("Production boundary QA requires a provenance manifest")
    locations = json.loads(Path(locations_path).read_text(encoding="utf-8"))
    resolved = [
        row
        for row in locations
        if row.get("latitude") is not None and row.get("longitude") is not None
    ]
    inside = [
        row
        for row in resolved
        if boundary.covers(Point(float(row["longitude"]), float(row["latitude"])))
    ]
    total_shipments = sum(float(row.get("shipment_count") or 0) for row in resolved)
    inside_shipments = sum(float(row.get("shipment_count") or 0) for row in inside)
    geod = Geod(ellps="WGS84")
    area_m2, _ = geod.geometry_area_perimeter(boundary)
    return {
        "geometry_valid": boundary.is_valid,
        "crs": "EPSG:4326",
        "region_name": region_name or (manifest.region if manifest else None),
        "area_km2": round(abs(area_m2) / 1_000_000, 4),
        "bbox": list(boundary.bounds),
        "destination_points_total": len(resolved),
        "destination_points_inside": len(inside),
        "destination_points_outside": len(resolved) - len(inside),
        "shipment_count_inside": round(inside_shipments, 4),
        "shipment_count_outside": round(total_shipments - inside_shipments, 4),
        "shipment_coverage_inside_pct": round(100 * inside_shipments / total_shipments, 4)
        if total_shipments
        else 0,
        "manifest": asdict(manifest) if manifest else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--locations", type=Path, required=True)
    parser.add_argument("--region-name")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--require-official", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_boundary(
        args.boundary,
        args.locations,
        region_name=args.region_name,
        manifest_path=args.manifest,
        require_official=args.require_official,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Boundary audit: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
