"""Audit Pulse readiness specifically for point-and-volume clustering."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from ml.clustering.economics import relative_rate_delta, weighted_mean
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
    origin_fias: str | None = None,
) -> dict:
    routes, route_report = build_clustering_routes(
        path, destination_region=destination_region, origin_fias=origin_fias
    )
    locations, location_report = build_location_dataset(
        path,
        coordinate_cache_path=coordinate_cache_path,
        destination_region=destination_region,
        origin_fias=origin_fias,
    )
    counts = [float(route.trip_count) for route in routes]
    rates = [
        float(route.weighted_rub_per_km)
        for route in routes
        if route.weighted_rub_per_km is not None
    ]
    regional_rate = weighted_mean(
        (route.weighted_rub_per_km, route.trip_count) for route in routes
    )
    thresholds = (0.20, 0.25, 0.30, 0.35, 0.40, 0.50)
    return {
        **route_report,
        "trip_count": {
            "total": round(sum(counts), 4),
            "min": min(counts) if counts else None,
            "median": _percentile(counts, 0.5),
            "p75": _percentile(counts, 0.75),
            "p95": _percentile(counts, 0.95),
            "p99": _percentile(counts, 0.99),
            "max": max(counts) if counts else None,
        },
        "rub_per_km": {
            "regional_trip_weighted": regional_rate,
            "min": min(rates) if rates else None,
            "median": _percentile(rates, 0.5),
            "p75": _percentile(rates, 0.75),
            "p95": _percentile(rates, 0.95),
            "p99": _percentile(rates, 0.99),
            "max": max(rates) if rates else None,
        },
        "bear_threshold_sensitivity": {
            f"plus_{int(threshold * 100)}pct": {
                "point_count": sum(
                    (relative_rate_delta(route.weighted_rub_per_km, regional_rate) or 0)
                    >= threshold
                    for route in routes
                ),
                "reliable_ge_3_trip_count": sum(
                    route.trip_count >= 3
                    and (relative_rate_delta(route.weighted_rub_per_km, regional_rate) or 0)
                    >= threshold
                    for route in routes
                ),
            }
            for threshold in thresholds
        },
        "reliability": {
            "zero_or_missing_trip_count_points": sum(route.trip_count <= 0 for route in routes),
            "trip_count_1_2_points": sum(1 <= route.trip_count < 3 for route in routes),
            "trip_count_ge_3_points": sum(route.trip_count >= 3 for route in routes),
            "trip_count_ge_5_points": sum(route.trip_count >= 5 for route in routes),
        },
        "recommendations": {
            "bear_threshold": None,
            "reliability_threshold": None,
            "singleton_min_trip_count": None,
            "status": "pending_analytics_review",
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
    parser.add_argument("--destination-region", required=True)
    parser.add_argument("--origin-fias", required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/clustering_data/audit.json"))
    args = parser.parse_args()
    report = build_clustering_data_audit(
        args.path,
        coordinate_cache_path=args.coordinate_cache,
        destination_region=args.destination_region,
        origin_fias=args.origin_fias,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Audit: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
