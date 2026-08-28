"""Build the canonical forecast-free route dataset used by clustering."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ml.data.loader import default_csv_path, iter_records

CLUSTERING_ALLOWED_PERIOD_TYPES = frozenset({"current", "retro"})
FORBIDDEN_CLUSTERING_FIELDS = frozenset(
    {"price", "rub_per_km", "market", "fact", "bid_count", "confidence", "forecast"}
)


@dataclass(frozen=True, slots=True)
class ClusteringRoute:
    origin_fias: str
    destination_fias: str
    destination_region: str
    period_id: str
    shipment_count: float
    route_length: float | None = None
    route_type: str | None = None
    vehicle_type: str | None = None
    tonnage_id: str | None = None


def build_clustering_routes(
    path: str | Path | None = None,
    *,
    destination_region: str | None = None,
    origin_fias: str | None = None,
) -> tuple[list[ClusteringRoute], dict[str, Any]]:
    """Collapse usable Pulse rows to route-period cells with ``units`` as volume."""
    source_path = Path(path) if path is not None else default_csv_path()
    raw_rows = forecast_rows = unsupported_rows = unusable_rows = 0
    totals: dict[tuple[str, str, str, str], float] = {}
    metadata: dict[tuple[str, str, str, str], tuple[float | None, str | None, str | None, str | None]] = {}
    origins: set[str] = set()
    destinations: set[str] = set()
    regions: Counter[str] = Counter()

    for record in iter_records(source_path):
        raw_rows += 1
        if record.period_type == "forecast":
            forecast_rows += 1
            continue
        if record.period_type not in CLUSTERING_ALLOWED_PERIOD_TYPES:
            unsupported_rows += 1
            continue
        if destination_region and record.destination_region != destination_region:
            continue
        if origin_fias and record.origin_fias != origin_fias:
            continue
        if (
            not record.origin_fias
            or not record.destination_fias
            or not record.destination_region
            or not record.period_id
            or record.shipment_count is None
            or record.shipment_count < 0
        ):
            unusable_rows += 1
            continue
        key = (
            record.origin_fias,
            record.destination_fias,
            record.destination_region,
            record.period_id,
        )
        totals[key] = totals.get(key, 0.0) + record.shipment_count
        metadata.setdefault(
            key,
            (record.route_length, record.route_type, record.vehicle_type, record.tonnage_id),
        )
        origins.add(record.origin_fias)
        destinations.add(record.destination_fias)
        regions[record.destination_region] += record.shipment_count

    routes = [
        ClusteringRoute(*key, shipment_count=total, route_length=metadata[key][0], route_type=metadata[key][1], vehicle_type=metadata[key][2], tonnage_id=metadata[key][3])
        for key, total in totals.items()
    ]
    routes.sort(key=lambda row: (row.period_id, row.origin_fias, row.destination_fias))
    report = {
        "source_path": str(source_path.resolve()),
        "raw_rows": raw_rows,
        "forecast_rows_excluded": forecast_rows,
        "unsupported_period_type_rows_excluded": unsupported_rows,
        "unusable_rows_excluded": unusable_rows,
        "usable_source_rows": raw_rows - forecast_rows - unsupported_rows - unusable_rows,
        "canonical_route_rows": len(routes),
        "unique_origin_fias": len(origins),
        "unique_destination_fias": len(destinations),
        "unique_destination_regions": len(regions),
        "shipment_count_total": round(sum(totals.values()), 4),
        "shipments_by_region": dict(regions.most_common()),
        "contract": {
            "allowed_period_types": sorted(CLUSTERING_ALLOWED_PERIOD_TYPES),
            "shipment_count_source": "Pulse.units",
            "diagnostic_only": ["bid_count", "confidence"],
            "clustering_features": ["projected_x", "projected_y"],
        },
    }
    return routes, report


def write_clustering_routes(
    routes: list[ClusteringRoute], report: dict[str, Any], output_dir: str | Path
) -> tuple[Path, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    routes_path = destination / "routes.csv"
    audit_path = destination / "audit.json"
    fields = list(asdict(routes[0])) if routes else ["origin_fias", "destination_fias", "destination_region", "period_id", "shipment_count"]
    with routes_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(asdict(route) for route in routes)
    audit_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return routes_path, audit_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=default_csv_path())
    parser.add_argument("--output-dir", type=Path, default=Path("reports/clustering_data"))
    parser.add_argument("--destination-region")
    parser.add_argument("--origin-fias")
    parser.add_argument(
        "--coordinate-cache", type=Path, default=Path("backend/cache/coords_cache.json")
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    routes, report = build_clustering_routes(
        args.path, destination_region=args.destination_region, origin_fias=args.origin_fias
    )
    routes_path, audit_path = write_clustering_routes(routes, report, args.output_dir)
    from ml.data.locations import build_location_dataset, write_location_dataset

    locations, location_report = build_location_dataset(
        args.path,
        coordinate_cache_path=args.coordinate_cache,
        destination_region=args.destination_region,
        origin_fias=args.origin_fias,
    )
    _, locations_path, _ = write_location_dataset(locations, location_report, args.output_dir)
    report["coordinates"] = location_report["coordinates"]
    report["locations"] = location_report["locations"]
    _, audit_path = write_clustering_routes(routes, report, args.output_dir)
    print(f"Routes: {routes_path}")
    print(f"Locations: {locations_path}")
    print(f"Audit: {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
