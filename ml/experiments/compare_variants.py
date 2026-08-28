"""Run E0-E3 and ATI_REF against one canonical actual-price dataset."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ml.data.actual import ActualSnapshotRecord, default_actual_path, iter_actual_snapshots
from ml.data.cluster_assignments import load_cluster_assignments
from ml.data.distance import load_distances
from ml.data.ground_truth import EvaluationKey, build_ground_truth, snapshot_revision_report
from ml.data.loader import default_csv_path
from ml.data.matching import default_origin_mapping_path, load_origin_mapping
from ml.data.normalization import normalize_region
from ml.data.pulse_evaluation import iter_pulse_evaluation_records
from ml.evaluation.contracts import ExperimentMetadata, VariantResult
from ml.evaluation.dataset import build_evaluation_dataset, write_evaluation_dataset
from ml.evaluation.metrics import (
    calculate_metrics,
    common_intersection,
    filter_predictions,
    paired_bootstrap_wape_delta,
)
from ml.evaluation.variants import ATIReferenceVariant, evaluate_variants

METHODOLOGY_VERSION = "analytics-evaluation-v1"


def _csv_set(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def _hash_file(path: Path | None) -> str | None:
    if path is None:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_sha() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _market_history(
    snapshots: list[ActualSnapshotRecord],
) -> dict[EvaluationKey, dict[int, float]]:
    history: dict[EvaluationKey, dict[int, tuple[str, float]]] = {}
    for item in snapshots:
        region = normalize_region(item.destination_region)
        if region is None or item.market_rub_per_item is None or item.market_rub_per_item <= 0:
            continue
        key = EvaluationKey(item.shipment_month, item.actual_origin_id, region)
        current = history.setdefault(key, {}).get(item.horizon_months)
        if current is None or item.snapshot_month > current[0]:
            history[key][item.horizon_months] = (item.snapshot_month, item.market_rub_per_item)
    return {
        key: {horizon: value for horizon, (_, value) in values.items()}
        for key, values in history.items()
    }


def _prediction_rows(result: VariantResult) -> list[dict[str, Any]]:
    return [
        {
            "shipment_month": item.key.shipment_month,
            "actual_origin_id": item.key.actual_origin_id,
            "destination_region": item.key.destination_region,
            "predicted_price": item.predicted_price,
            "status": item.status,
            "reason": item.reason,
        }
        for item in result.predictions
    ]


def _write_predictions(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "shipment_month",
        "actual_origin_id",
        "destination_region",
        "predicted_price",
        "status",
        "reason",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _serialize_result(result: VariantResult) -> dict[str, Any]:
    return {
        "variant": result.variant,
        "status": result.status,
        "blocker": result.blocker,
        "required_fields": list(result.required_fields),
        "coverage": result.coverage,
        "metrics": result.metrics.as_dict() if result.metrics else None,
        "segments": result.segment_metrics,
    }


def _leaderboard(
    rows: list[Any], results: dict[str, VariantResult]
) -> list[dict[str, Any]]:
    baseline = results["E0"]
    output: list[dict[str, Any]] = []
    for name, result in results.items():
        metrics = result.metrics
        output.append(
            {
                "variant": name,
                "scope": "all_available",
                "status": result.status,
                "coverage": result.coverage,
                "wape_pct": metrics.wape_pct if metrics else None,
                "bias_pct": metrics.bias_pct if metrics else None,
                "cells": metrics.n_evaluation_cells if metrics else 0,
                "qty": metrics.qty_evaluated if metrics else 0,
                "relative_wape_improvement_pct": None,
            }
        )
        if name == "E0" or result.status != "evaluated" or baseline.status != "evaluated":
            continue
        keys = common_intersection(baseline.predictions, result.predictions)
        base_metrics = calculate_metrics(rows, filter_predictions(baseline.predictions, keys))
        variant_metrics = calculate_metrics(rows, filter_predictions(result.predictions, keys))
        improvement = (
            100 * (base_metrics.wape_pct - variant_metrics.wape_pct) / base_metrics.wape_pct
            if base_metrics.wape_pct not in {None, 0} and variant_metrics.wape_pct is not None
            else None
        )
        output.append(
            {
                "variant": name,
                "scope": "common_intersection_with_E0",
                "status": result.status,
                "coverage": len(keys) / len(rows) if rows else 0,
                "wape_pct": variant_metrics.wape_pct,
                "bias_pct": variant_metrics.bias_pct,
                "cells": variant_metrics.n_evaluation_cells,
                "qty": variant_metrics.qty_evaluated,
                "relative_wape_improvement_pct": improvement,
            }
        )
    return output


def _write_leaderboard(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "variant",
        "scope",
        "status",
        "coverage",
        "wape_pct",
        "bias_pct",
        "cells",
        "qty",
        "relative_wape_improvement_pct",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _h1_success_details(
    rows: list[Any],
    baseline: VariantResult,
    challenger: VariantResult,
    *,
    improvement_threshold_pct: float,
    bias_tolerance_pct_points: float = 1.0,
) -> dict[str, Any]:
    keys = common_intersection(baseline.predictions, challenger.predictions)
    baseline_predictions = filter_predictions(baseline.predictions, keys)
    challenger_predictions = filter_predictions(challenger.predictions, keys)
    baseline_metrics = calculate_metrics(rows, baseline_predictions)
    challenger_metrics = calculate_metrics(rows, challenger_predictions)
    improvement = (
        100 * (baseline_metrics.wape_pct - challenger_metrics.wape_pct) / baseline_metrics.wape_pct
        if baseline_metrics.wape_pct not in {None, 0} and challenger_metrics.wape_pct is not None
        else None
    )
    baseline_bias = abs(baseline_metrics.bias_pct or 0)
    challenger_bias = abs(challenger_metrics.bias_pct or 0)
    bias_ok = challenger_bias <= baseline_bias + bias_tolerance_pct_points
    improved_months = 0
    comparable_months = 0
    for month in sorted({key.shipment_month for key in keys}):
        month_keys = {key for key in keys if key.shipment_month == month}
        base = calculate_metrics(rows, filter_predictions(baseline.predictions, month_keys))
        challenge = calculate_metrics(rows, filter_predictions(challenger.predictions, month_keys))
        if base.wape_pct in {None, 0} or challenge.wape_pct is None:
            continue
        comparable_months += 1
        if challenge.wape_pct < base.wape_pct:
            improved_months += 1
    required_improved_months = max(2, math.ceil(comparable_months / 2))
    months_ok = comparable_months >= 2 and improved_months >= required_improved_months
    return {
        "common_intersection_cells": len(keys),
        "relative_wape_improvement_pct": improvement,
        "bias_ok": bias_ok,
        "baseline_bias_pct": baseline_metrics.bias_pct,
        "challenger_bias_pct": challenger_metrics.bias_pct,
        "bias_tolerance_pct_points": bias_tolerance_pct_points,
        "improved_months": improved_months,
        "comparable_months": comparable_months,
        "months_ok": months_ok,
        "success": bool(
            improvement is not None
            and improvement >= improvement_threshold_pct
            and bias_ok
            and months_ok
        ),
    }


def run_comparison(
    *,
    actual_path: Path,
    pulse_path: Path,
    mapping_path: Path,
    output_dir: Path,
    distance_path: Path | None = None,
    cluster_assignments_path: Path | None = None,
    as_of: str | None = None,
    shipment_months: set[str] | None = None,
    price_types: set[str] | None = None,
    period_types: set[str] | None = None,
    bootstrap_iterations: int = 1000,
    improvement_threshold_pct: float = 5.0,
) -> dict[str, Any]:
    snapshots = list(iter_actual_snapshots(actual_path))
    target_months = shipment_months or set()
    if as_of:
        snapshots = [item for item in snapshots if item.snapshot_month <= as_of]
    ground_truth = build_ground_truth(snapshots)
    if target_months:
        ground_truth = [
            item for item in ground_truth if item.evaluation_key.shipment_month in target_months
        ]
    built = build_evaluation_dataset(
        ground_truth,
        iter_pulse_evaluation_records(pulse_path),
        load_origin_mapping(mapping_path),
        distances=load_distances(distance_path) if distance_path else None,
        cluster_assignments=(
            load_cluster_assignments(cluster_assignments_path)
            if cluster_assignments_path
            else None
        ),
        price_types=price_types,
        period_types=period_types,
    )
    history = _market_history(snapshots)
    rows = [replace(row, market_by_horizon=history.get(row.key, {})) for row in built.rows]
    results = evaluate_variants(rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_evaluation_dataset(rows, output_dir / "evaluation_dataset.csv")
    _write_json(output_dir / "coverage.json", built.coverage.as_dict())
    _write_json(
        output_dir / "data_quality.json",
        {**built.data_quality, "snapshot_revisions": snapshot_revision_report(snapshots)},
    )

    directory_names = {
        "E0": "e0",
        "E0_trip_weighted": "e0_trip_weighted",
        "E1": "e1",
        "E2": "e2",
        "E3": "e3",
        "ATI_REF": "ati_reference",
    }
    for name, result in results.items():
        destination = output_dir / directory_names[name]
        _write_json(destination / ("metrics.json" if result.status == "evaluated" else "status.json"), _serialize_result(result))
        if result.status == "evaluated":
            _write_predictions(destination / "predictions.csv", _prediction_rows(result))

    horizon_rows: list[dict[str, Any]] = []
    horizons = sorted({horizon for row in rows for horizon in row.market_by_horizon})
    for horizon in horizons:
        result = ATIReferenceVariant(horizon).predict(rows)
        metrics = result.metrics
        horizon_rows.append(
            {
                "horizon": f"M{horizon}",
                "status": result.status,
                "coverage": result.coverage,
                "wape_pct": metrics.wape_pct if metrics else None,
                "mdape_pct": metrics.mdape_pct if metrics else None,
                "bias_pct": metrics.bias_pct if metrics else None,
                "within_20_pct": metrics.within_20_pct if metrics else None,
                "cells": metrics.n_evaluation_cells if metrics else 0,
                "qty": metrics.qty_evaluated if metrics else 0,
            }
        )
    horizon_path = output_dir / "ati_reference" / "by_horizon.csv"
    horizon_path.parent.mkdir(parents=True, exist_ok=True)
    with horizon_path.open("w", encoding="utf-8-sig", newline="") as stream:
        fieldnames = ["horizon", "status", "coverage", "wape_pct", "mdape_pct", "bias_pct", "within_20_pct", "cells", "qty"]
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(horizon_rows)

    leaderboard = _leaderboard(rows, results)
    _write_leaderboard(output_dir / "leaderboard.csv", leaderboard)
    bootstrap = (
        paired_bootstrap_wape_delta(
            rows,
            list(results["E0"].predictions),
            list(results["E1"].predictions),
            iterations=bootstrap_iterations,
        )
        if results["E0"].status == "evaluated" and results["E1"].status == "evaluated"
        else {"pairs": 0, "delta_wape_pct": None, "ci_low": None, "ci_high": None}
    )
    _write_json(output_dir / "paired_bootstrap.json", bootstrap)

    metadata = ExperimentMetadata(
        methodology_version=METHODOLOGY_VERSION,
        created_at=datetime.now(UTC).isoformat(),
        git_commit_sha=_git_sha(),
        pulse_file_hash=str(_hash_file(pulse_path)),
        actual_file_hash=str(_hash_file(actual_path)),
        mapping_file_hash=str(_hash_file(mapping_path)),
        distance_file_hash=_hash_file(distance_path),
        cluster_assignment_hash=_hash_file(cluster_assignments_path),
        as_of=as_of,
        target_months=tuple(sorted(target_months)),
        price_types=tuple(sorted(price_types or set())),
    )
    _write_json(output_dir / "run_metadata.json", metadata.as_dict())

    h1_success = (
        _h1_success_details(
            rows,
            results["E0"],
            results["E1"],
            improvement_threshold_pct=improvement_threshold_pct,
        )
        if results["E0"].status == "evaluated" and results["E1"].status == "evaluated"
        else {
            "common_intersection_cells": 0,
            "relative_wape_improvement_pct": None,
            "bias_ok": False,
            "improved_months": 0,
            "comparable_months": 0,
            "months_ok": False,
            "success": False,
        }
    )
    decision = {
        "data_readiness": {
            "ready": built.coverage.ground_truth_qty_coverage >= 0.9
            and built.coverage.origin_mapping_qty_coverage >= 0.9,
            "fact_qty_coverage": built.coverage.ground_truth_qty_coverage,
            "origin_mapping_qty_coverage": built.coverage.origin_mapping_qty_coverage,
        },
        "variants": {
            name: {
                "status": result.status,
                "blocker": result.blocker,
                "coverage": result.coverage,
            }
            for name, result in results.items()
            if name in {"E0", "E1", "E2", "E3"}
        },
        "h1_readiness": built.coverage.distance_coverage >= 0.8,
        "h2_readiness": built.coverage.cluster_coverage >= 0.8,
        "h2_destination_level_coverage": built.coverage.cluster_coverage,
        "hypothesis_success": bool(h1_success["success"] and built.coverage.distance_coverage >= 0.8),
        "h1_success_details": h1_success,
        "relative_wape_improvement_threshold_pct": improvement_threshold_pct,
        "bootstrap": bootstrap,
    }
    _write_json(output_dir / "decision_gate_actual.json", decision)
    return {"rows": len(rows), "results": results, "decision": decision, "leaderboard": leaderboard}


def build_parser() -> argparse.ArgumentParser:
    default_mapping = default_origin_mapping_path()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actual", type=Path, default=default_actual_path())
    parser.add_argument("--pulse", type=Path, default=default_csv_path())
    parser.add_argument("--origin-map", type=Path, default=default_mapping, required=default_mapping is None)
    parser.add_argument("--distance", type=Path)
    parser.add_argument("--cluster-assignments", type=Path)
    parser.add_argument("--as-of")
    parser.add_argument("--shipment-months", type=_csv_set, default=set())
    parser.add_argument("--price-types", type=_csv_set, default=set())
    parser.add_argument("--period-types", type=_csv_set, default=set())
    parser.add_argument("--bootstrap-iterations", type=int, default=1000)
    parser.add_argument("--improvement-threshold-pct", type=float, default=5.0)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/private/evaluation"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_comparison(
        actual_path=args.actual,
        pulse_path=args.pulse,
        mapping_path=args.origin_map,
        output_dir=args.output_dir,
        distance_path=args.distance,
        cluster_assignments_path=args.cluster_assignments,
        as_of=args.as_of,
        shipment_months=args.shipment_months,
        price_types=args.price_types,
        period_types=args.period_types,
        bootstrap_iterations=args.bootstrap_iterations,
        improvement_threshold_pct=args.improvement_threshold_pct,
    )
    print(f"Evaluation rows: {report['rows']}")
    print(f"Output: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
