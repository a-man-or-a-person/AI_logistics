"""Evaluate saved clustering runs against later Pulse periods."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from ml.data.loader import default_csv_path
from ml.data.pulse_evaluation import iter_pulse_evaluation_records
from ml.evaluation.economic import evaluate_rates


def _read_assignments(path: Path) -> dict[str, int]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return {
            row["id"]: int(row["cluster_id"])
            for row in csv.DictReader(stream)
            if row.get("id") and row.get("cluster_id") not in {None, ""}
        }


def _write_predictions(path: Path, predictions: list[dict[str, Any]]) -> None:
    fieldnames = list(predictions[0]) if predictions else ["destination_fias"]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(predictions)


def evaluate_clustering_directory(
    pulse_path: str | Path,
    clustering_dir: str | Path,
    *,
    destination_region: str,
    origin_fias: str,
    train_periods: set[str],
    test_periods: set[str],
) -> list[dict[str, Any]]:
    if train_periods & test_periods:
        raise ValueError("Train and test periods must be disjoint")
    source_path = Path(pulse_path)
    destination = Path(clustering_dir)
    train_records = []
    test_records = []
    train_period_types: set[str] = set()
    test_period_types: set[str] = set()
    for record in iter_pulse_evaluation_records(source_path):
        if record.destination_region != destination_region or record.origin_fias != origin_fias:
            continue
        if record.period_id in train_periods:
            train_records.append(record)
            if record.period_type:
                train_period_types.add(record.period_type)
        elif record.period_id in test_periods:
            test_records.append(record)
            if record.period_type:
                test_period_types.add(record.period_type)

    leaderboard: list[dict[str, Any]] = []
    for run_dir in sorted(destination.glob("kmeans_k*"), key=lambda path: int(path.name[8:])):
        assignments_path = run_dir / "assignments.csv"
        metrics_path = run_dir / "metrics.json"
        if not assignments_path.exists() or not metrics_path.exists():
            continue
        assignments = _read_assignments(assignments_path)
        report, predictions = evaluate_rates(train_records, test_records, assignments)
        run_metadata = json.loads(metrics_path.read_text(encoding="utf-8"))
        report = {
            "experiment_id": run_metadata["experiment_id"],
            "algorithm": run_metadata["algorithm"],
            "parameters": run_metadata["parameters"],
            "filters": {
                "destination_region": destination_region,
                "origin_fias": origin_fias,
                "train_periods": sorted(train_periods),
                "test_periods": sorted(test_periods),
                "train_period_types": sorted(train_period_types),
                "test_period_types": sorted(test_period_types),
            },
            "target_semantics": (
                "Pulse test-period prices; forecast periods are a proxy, not realized actuals"
            ),
            **report,
        }
        (run_dir / "economic_evaluation.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        _write_predictions(run_dir / "economic_predictions.csv", predictions)
        overall = report["overall"]
        leaderboard.append(
            {
                "experiment_id": report["experiment_id"],
                "algorithm": report["algorithm"],
                "parameters": json.dumps(report["parameters"], sort_keys=True),
                "regional_wape": overall["regional"]["wape_pct"],
                "cluster_wape": overall["cluster"]["wape_pct"],
                "relative_wape_improvement_pct": overall["relative_wape_improvement_pct"],
                "regional_mae_rub": overall["regional"]["mae_rub"],
                "cluster_mae_rub": overall["cluster"]["mae_rub"],
                "cluster_bias_pct": overall["cluster"]["bias_pct"],
                "cluster_within_10_pct": overall["cluster"]["within_10_pct"],
                "matched_rows": report["coverage"]["matched_rows"],
                "unmatched_rows": report["coverage"]["unmatched_rows"],
            }
        )
    output_path = destination / "economic_leaderboard.csv"
    with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(leaderboard[0]) if leaderboard else ["algorithm"]
        )
        writer.writeheader()
        writer.writerows(leaderboard)
    return leaderboard


def _csv_set(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pulse", type=Path, default=default_csv_path())
    parser.add_argument("--clustering-dir", type=Path, required=True)
    parser.add_argument("--destination-region", required=True)
    parser.add_argument("--origin-fias", required=True)
    parser.add_argument("--train-periods", type=_csv_set, required=True)
    parser.add_argument("--test-periods", type=_csv_set, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    leaderboard = evaluate_clustering_directory(
        args.pulse,
        args.clustering_dir,
        destination_region=args.destination_region,
        origin_fias=args.origin_fias,
        train_periods=args.train_periods,
        test_periods=args.test_periods,
    )
    print(f"Evaluated {len(leaderboard)} clustering experiments")
    print(f"Leaderboard: {args.clustering_dir / 'economic_leaderboard.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
