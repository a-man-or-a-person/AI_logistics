"""Run Product v1 real-data and cache regression on the frozen pilot profiles."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from backend.services.clustering_service import (
    BEAR_THRESHOLD_OPTIONS,
    GEO_COST_PRESETS,
    GEO_VOLUME_PRESETS,
    ClusteringRequest,
    ClusteringService,
    ProductClusteringError,
)


def _request(
    pilot: dict[str, Any], mode: str, parameters: dict[str, Any]
) -> ClusteringRequest:
    return ClusteringRequest.from_payload(
        {
            "origin_fias": pilot["origin_fias"],
            "destination_region": pilot["destination_region"],
            "period_types": pilot.get("period_types", ["retro", "current", "forecast"]),
            "price_types": pilot.get("price_types", ["spot", "tender"]),
            "vehicle_types": pilot.get("vehicle_types", []),
            "tonnage_ids": pilot.get("tonnage_ids", []),
            "mode": mode,
            "parameters": parameters,
        }
    )


def _run(
    service: ClusteringService,
    pilot: dict[str, Any],
    mode: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = service.run(_request(pilot, mode, parameters))
    except ProductClusteringError as error:
        return {
            "mode": mode,
            "parameters": parameters,
            "status": "error",
            "error_code": error.code,
            "error": str(error),
            "elapsed_seconds": round(time.perf_counter() - started, 6),
        }
    metrics = result.get("metrics", {})
    return {
        "mode": mode,
        "parameters": parameters,
        "status": result["status"],
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "selected_k": result["analysis"]["parameters"].get("n_clusters"),
        "cluster_count": len(result["clusters"]),
        "candidate_count": metrics.get("candidate_count"),
        "singleton_count": metrics.get("singleton_count"),
        "connectivity_violations": metrics.get("connectivity_violations"),
        "p95_radius_m": metrics.get("p95_distance_to_medoid_m"),
        "point_coverage_pct": result["data_quality"]["point_coverage_pct"],
        "trip_weight_coverage_pct": result["data_quality"]["trip_weight_coverage_pct"],
        "outlier_count": len(result["outliers"]),
    }


def run_product_smoke(
    pilots: list[dict[str, Any]],
    *,
    service: ClusteringService | None = None,
) -> dict[str, Any]:
    if len(pilots) < 5:
        raise ValueError("Product smoke requires at least five pilot profiles")
    product = service or ClusteringService()
    warm_started = time.perf_counter()
    product.options()
    repository_load_seconds = time.perf_counter() - warm_started
    results = []
    for pilot in pilots:
        runs = [
            _run(product, pilot, "geography", {"k_mode": "auto", "n_clusters": "auto"})
        ]
        runs.extend(
            _run(
                product,
                pilot,
                "geo_cost",
                {
                    "k_mode": "auto",
                    "n_clusters": "auto",
                    "geography_weight": geography,
                    "economics_weight": economics,
                },
            )
            for geography, economics in GEO_COST_PRESETS
        )
        runs.extend(
            _run(
                product,
                pilot,
                "geo_volume",
                {
                    "k_mode": "auto",
                    "n_clusters": "auto",
                    "geography_weight": geography,
                    "volume_weight": volume,
                },
            )
            for geography, volume in GEO_VOLUME_PRESETS
        )
        runs.extend(
            _run(
                product,
                pilot,
                "bear_zones",
                {"bear_threshold": threshold, "singleton_threshold": 0.70},
            )
            for threshold in BEAR_THRESHOLD_OPTIONS
        )
        runs.extend(
            _run(
                product,
                pilot,
                "bear_volume_zones",
                {"volume_threshold": threshold, "singleton_threshold": 0.70},
            )
            for threshold in BEAR_THRESHOLD_OPTIONS
        )
        repeat = _run(
            product, pilot, "geography", {"k_mode": "auto", "n_clusters": "auto"}
        )
        results.append({"pilot": pilot, "runs": runs, "cached_repeat": repeat})
    completed = [
        run
        for pilot in results
        for run in pilot["runs"]
        if run["status"] != "error"
    ]
    violations = [
        run
        for run in completed
        if run["connectivity_violations"] != 0
    ]
    error_run_count = sum(
        run["status"] == "error" for pilot in results for run in pilot["runs"]
    )
    return {
        "contract": "clustering-product-v1-real-data-smoke",
        "winner": None,
        "repository_load_seconds": round(repository_load_seconds, 6),
        "pilot_count": len(pilots),
        "run_count": sum(len(pilot["runs"]) for pilot in results),
        "completed_run_count": len(completed),
        "error_run_count": error_run_count,
        "connectivity_violation_run_count": len(violations),
        "acceptance_passed": error_run_count == 0
        and not violations
        and all(
            pilot["cached_repeat"]["status"] != "error" for pilot in results
        ),
        "pilots": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pilots",
        type=Path,
        default=Path("ml/configs/clustering_research_pilots.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/clustering_product_v1_final_smoke.json"),
    )
    args = parser.parse_args()
    pilots = json.loads(args.pilots.read_text(encoding="utf-8"))
    report = run_product_smoke(pilots)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Pilots={report['pilot_count']} runs={report['run_count']} "
        f"errors={report['error_run_count']} acceptance={report['acceptance_passed']}"
    )
    print(f"Report: {args.output}")
    return 0 if report["acceptance_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
