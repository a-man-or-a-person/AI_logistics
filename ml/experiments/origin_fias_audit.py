"""Write the volume-prioritized origin FIAS manual-review queue."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ml.data.loader import default_csv_path, iter_records
from ml.data.origin_mapping import build_origin_fias_candidates


def write_origin_fias_audit(
    source_path: str | Path | None = None,
    output_path: str | Path = "reports/private/origin_fias_review.csv",
) -> Path:
    candidates = build_origin_fias_candidates(list(iter_records(source_path)))
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "normalized_town", "source_names", "candidate_fias", "candidate_count",
        "shipment_count", "status", "selected_fias", "review_note",
    ]
    with destination.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for candidate in candidates:
            writer.writerow(
                {
                    "normalized_town": candidate.normalized_town,
                    "source_names": " | ".join(candidate.source_names),
                    "candidate_fias": " | ".join(candidate.candidate_fias),
                    "candidate_count": len(candidate.candidate_fias),
                    "shipment_count": candidate.trip_count,
                    "status": candidate.status,
                    "selected_fias": candidate.candidate_fias[0]
                    if candidate.status == "auto_unique"
                    else "",
                    "review_note": "",
                }
            )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=default_csv_path())
    parser.add_argument(
        "--output", type=Path, default=Path("reports/private/origin_fias_review.csv")
    )
    args = parser.parse_args()
    print(f"Review: {write_origin_fias_audit(args.path, args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
