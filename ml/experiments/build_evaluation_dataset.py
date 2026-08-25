"""Build the private canonical evaluation dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml.data.actual import default_actual_path, iter_actual_snapshots
from ml.data.cluster_assignments import load_cluster_assignments
from ml.data.distance import load_distances
from ml.data.ground_truth import build_ground_truth
from ml.data.loader import default_csv_path
from ml.data.matching import load_origin_mapping
from ml.data.pulse_evaluation import iter_pulse_evaluation_records
from ml.evaluation.dataset import build_evaluation_dataset, write_evaluation_dataset


def _csv_set(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actual", type=Path, default=default_actual_path())
    parser.add_argument("--pulse", type=Path, default=default_csv_path())
    parser.add_argument("--origin-map", type=Path, required=True)
    parser.add_argument("--distance", type=Path)
    parser.add_argument("--cluster-assignments", type=Path)
    parser.add_argument("--price-types", type=_csv_set, default=set())
    parser.add_argument("--period-types", type=_csv_set, default=set())
    parser.add_argument(
        "--output", type=Path, default=Path("reports/private/evaluation_dataset.csv")
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    snapshots = list(iter_actual_snapshots(args.actual))
    result = build_evaluation_dataset(
        build_ground_truth(snapshots),
        iter_pulse_evaluation_records(args.pulse),
        load_origin_mapping(args.origin_map),
        distances=load_distances(args.distance) if args.distance else None,
        cluster_assignments=(
            load_cluster_assignments(args.cluster_assignments)
            if args.cluster_assignments
            else None
        ),
        price_types=args.price_types,
        period_types=args.period_types,
    )
    write_evaluation_dataset(result.rows, args.output)
    metadata = args.output.with_suffix(".metadata.json")
    metadata.write_text(
        json.dumps(
            {"coverage": result.coverage.as_dict(), "data_quality": result.data_quality},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Evaluation rows: {len(result.rows)}")
    print(f"CSV: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
