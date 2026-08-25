"""Build private conservative origin candidates and a safe aggregate summary."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from ml.data.actual import default_actual_path, iter_actual_snapshots
from ml.data.ground_truth import build_ground_truth
from ml.data.loader import default_csv_path
from ml.data.matching import ORIGIN_MAPPING_COLUMNS, build_origin_candidates
from ml.data.pulse_registry import load_pulse_origins


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actual", type=Path, default=default_actual_path())
    parser.add_argument("--pulse", type=Path, default=default_csv_path())
    parser.add_argument(
        "--output", type=Path, default=Path("reports/private/origin_matching_candidates.csv")
    )
    parser.add_argument(
        "--summary", type=Path, default=Path("reports/private/origin_matching_summary.json")
    )
    parser.add_argument(
        "--mapping-template",
        type=Path,
        default=Path("ml/configs/private/origin_mapping.csv"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    snapshots = list(iter_actual_snapshots(args.actual))
    candidates = build_origin_candidates(snapshots, load_pulse_origins(args.pulse))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(candidates[0])) if candidates else ["actual_origin_id"]
    with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(item) for item in candidates)
    args.mapping_template.parent.mkdir(parents=True, exist_ok=True)
    with args.mapping_template.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=ORIGIN_MAPPING_COLUMNS)
        writer.writeheader()
        for item in candidates:
            writer.writerow(
                {
                    "actual_origin_id": item.actual_origin_id,
                    "actual_origin_town": item.actual_origin_town,
                    "pulse_origin_fias": item.pulse_origin_fias,
                    "pulse_origin_name": item.pulse_origin_name,
                    "match_method": item.match_method,
                    "match_status": item.match_status,
                    "confidence": item.confidence,
                    "mapping_version": "candidate-v1",
                }
            )
    statuses = {status: sum(item.match_status == status for item in candidates) for status in ("matched", "ambiguous", "unmatched")}
    ground_truth = build_ground_truth(snapshots)
    qty_by_origin: dict[str, float] = {}
    cells_by_origin: dict[str, int] = {}
    for item in ground_truth:
        origin_id = item.evaluation_key.actual_origin_id
        qty_by_origin[origin_id] = qty_by_origin.get(origin_id, 0) + max(item.qty_total or 0, 0)
        cells_by_origin[origin_id] = cells_by_origin.get(origin_id, 0) + 1
    matched = {item.actual_origin_id for item in candidates if item.match_status == "matched"}
    total_qty = sum(qty_by_origin.values())
    total_cells = sum(cells_by_origin.values())
    summary = {
        "actual_origins_total": len(candidates),
        **statuses,
        "matched_qty_coverage": sum(qty_by_origin.get(key, 0) for key in matched) / total_qty if total_qty else 0,
        "matched_business_cell_coverage": sum(cells_by_origin.get(key, 0) for key in matched) / total_cells if total_cells else 0,
    }
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Candidates: {args.output}")
    print(f"Mapping template: {args.mapping_template}")
    print(f"Summary: {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
