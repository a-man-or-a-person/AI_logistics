"""Aggregate-only audit for the confidential actual snapshot source."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from ml.data.actual import default_actual_path, iter_actual_snapshots
from ml.data.ground_truth import build_ground_truth, snapshot_revision_report


def audit_actual(path: str | Path, *, limit: int | None = None) -> dict[str, Any]:
    snapshots = list(iter_actual_snapshots(path, limit=limit))
    ground_truth = build_ground_truth(snapshots)
    snapshot_counts = Counter(
        (item.shipment_month, item.actual_origin_id, item.destination_region) for item in snapshots
    )
    return {
        "rows": len(snapshots),
        "business_keys": len(ground_truth),
        "snapshots": len({item.snapshot_month for item in snapshots}),
        "shipment_month_range": (
            [min(item.shipment_month for item in snapshots), max(item.shipment_month for item in snapshots)]
            if snapshots
            else None
        ),
        "snapshot_month_range": (
            [min(item.snapshot_month for item in snapshots), max(item.snapshot_month for item in snapshots)]
            if snapshots
            else None
        ),
        "fact_coverage": (
            sum(item.fact_rub_per_item is not None for item in snapshots) / len(snapshots)
            if snapshots
            else 0
        ),
        "market_coverage": (
            sum(item.market_rub_per_item is not None for item in snapshots) / len(snapshots)
            if snapshots
            else 0
        ),
        "unique_origins": len({item.actual_origin_id for item in snapshots}),
        "unique_origin_towns": len({item.origin_town for item in snapshots if item.origin_town}),
        "unique_destination_regions": len({item.destination_region for item in snapshots}),
        "snapshot_counts_per_business_key": dict(sorted(Counter(snapshot_counts.values()).items())),
        "month_label_distribution": dict(sorted(Counter(item.month_label for item in snapshots).items())),
        "revisions": snapshot_revision_report(snapshots),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=default_actual_path())
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, default=Path("reports/private/actual_audit.json"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = audit_actual(args.path, limit=args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Audited {report['rows']} snapshots into {report['business_keys']} business keys")
    print(f"JSON: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
