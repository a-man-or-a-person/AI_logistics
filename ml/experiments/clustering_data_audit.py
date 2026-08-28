"""Audit Pulse readiness specifically for point-and-volume clustering."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from ml.data.clustering_dataset import build_clustering_routes
from ml.data.loader import default_csv_path
from ml.data.locations import build_location_dataset


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower, upper = math.floor(index), math.ceil(index)
    return ordered[lower] if lower == upper else ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def build_clustering_data_audit(
    path: str | Path | None = None,
    *,
    coordinate_cache_path: str | Path = "backend/cache/coords_cache.json",
    destination_region: str | None = None,
) -> dict:
    routes, route_report = build_clustering_routes(path, destination_region=destination_region)
    locations, location_report = build_location_dataset(
        path,
        coordinate_cache_path=coordinate_cache_path,
        destination_region=destination_region,
    )
    counts = [route.shipment_count for route in routes]
    return {
        **route_report,
        "shipment_count": {
            "total": round(sum(counts), 4),
            "min": min(counts) if counts else None,
            "median": _percentile(counts, 0.5),
            "p75": _percentile(counts, 0.75),
            "p95": _percentile(counts, 0.95),
            "p99": _percentile(counts, 0.99),
            "max": max(counts) if counts else None,
        },
        "coordinates": location_report["coordinates"],
        "locations": {
            "total": len(locations),
            "resolved": sum(location.latitude is not None for location in locations),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=default_csv_path())
    parser.add_argument("--coordinate-cache", type=Path, default=Path("backend/cache/coords_cache.json"))
    parser.add_argument("--destination-region")
    parser.add_argument("--output", type=Path, default=Path("reports/clustering_data/audit.json"))
    args = parser.parse_args()
    report = build_clustering_data_audit(
        args.path,
        coordinate_cache_path=args.coordinate_cache,
        destination_region=args.destination_region,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Audit: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
