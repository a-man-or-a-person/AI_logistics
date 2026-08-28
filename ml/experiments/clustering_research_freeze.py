"""Run the research-freeze diagnostics on five or more Pulse directions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ml.clustering.base import ClusterPoint
from ml.data.loader import default_csv_path
from ml.data.locations import build_location_dataset
from ml.experiments.clustering_modes import run_clustering_modes


def _cluster_points(locations: list[Any]) -> list[ClusterPoint]:
    return [
        ClusterPoint(
            point.id,
            point.name,
            point.region,
            point.x,
            point.y,
            point.trip_count,
            point.weighted_price,
            point.weighted_rub_per_km,
            point.data_quality_flags,
        )
        for point in locations
        if point.x is not None
    ]


def run_research_freeze(
    pilots: list[dict[str, Any]],
    *,
    source_path: str | Path | None = None,
    coordinate_cache_path: str | Path = "backend/cache/coords_cache.json",
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    if len(pilots) < 5:
        raise ValueError("Research freeze requires at least five diverse pilots")
    source = Path(source_path) if source_path is not None else default_csv_path()
    results = []
    for pilot in pilots:
        filters = {
            "origin_fias": str(pilot["origin_fias"]),
            "destination_region": str(pilot["destination_region"]),
            "period_types": list(
                pilot.get("period_types") or ["retro", "current", "forecast"]
            ),
            "price_types": list(pilot.get("price_types") or []),
            "vehicle_types": list(pilot.get("vehicle_types") or []),
            "tonnage_ids": list(pilot.get("tonnage_ids") or []),
        }
        locations, audit = build_location_dataset(
            source,
            coordinate_cache_path=coordinate_cache_path,
            origin_fias=filters["origin_fias"],
            destination_region=filters["destination_region"],
            period_types=set(filters["period_types"]),
            price_types=set(filters["price_types"]),
            vehicle_types=set(filters["vehicle_types"]),
            tonnage_ids=set(filters["tonnage_ids"]),
        )
        points = _cluster_points(locations)
        if len(points) < 3:
            results.append(
                {
                    "pilot": pilot,
                    "status": "insufficient_resolved_points",
                    "data_quality": audit["data_quality"],
                }
            )
            continue
        report = run_clustering_modes(
            points,
            filters=filters,
            n_clusters="auto",
            source_data_quality=audit["data_quality"],
        )
        results.append(
            {
                "pilot": pilot,
                "status": "completed",
                "source_rows": audit["filtered_source_rows"],
                "data_quality": audit["data_quality"],
                **report,
            }
        )
    payload = {
        "contract": "clustering-contract-v1-research-freeze",
        "pilot_count": len(pilots),
        "completed_pilot_count": sum(
            result["status"] == "completed" for result in results
        ),
        "automatic_winner": None,
        "pilots": results,
    }
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilots", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=default_csv_path())
    parser.add_argument(
        "--coordinate-cache",
        type=Path,
        default=Path("backend/cache/coords_cache.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pilots = json.loads(args.pilots.read_text(encoding="utf-8"))
    result = run_research_freeze(
        pilots,
        source_path=args.source,
        coordinate_cache_path=args.coordinate_cache,
        output_path=args.output,
    )
    print(
        f"Completed {result['completed_pilot_count']} of "
        f"{result['pilot_count']} pilots"
    )
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
