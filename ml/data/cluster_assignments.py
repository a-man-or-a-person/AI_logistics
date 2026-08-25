"""Optional destination-level route assignments supplied by the ML/data owner."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ml.data.normalization import normalize_region
from ml.data.schema import clean_text, parse_float, parse_int

CLUSTER_ASSIGNMENT_COLUMNS = (
    "shipment_month",
    "actual_origin_id",
    "destination_region",
    "destination_fias",
    "cluster_id",
    "cluster_price",
    "cluster_rub_per_km",
)


@dataclass(frozen=True, slots=True)
class ClusterEvaluationAssignment:
    shipment_month: str
    actual_origin_id: str
    destination_region: str
    destination_fias: str
    cluster_id: int
    cluster_price: float | None
    cluster_rub_per_km: float | None


def load_cluster_assignments(path: str | Path) -> list[ClusterEvaluationAssignment]:
    records: list[ClusterEvaluationAssignment] = []
    seen: set[tuple[str, str, str]] = set()
    with Path(path).open(encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or ())
        missing = sorted(set(CLUSTER_ASSIGNMENT_COLUMNS) - headers)
        if missing:
            raise ValueError(f"Cluster assignment CSV is missing columns: {', '.join(missing)}")
        for row_number, row in enumerate(reader, start=2):
            shipment_month = clean_text(row.get("shipment_month"))
            origin_id = clean_text(row.get("actual_origin_id"))
            region = normalize_region(clean_text(row.get("destination_region")))
            destination_fias = clean_text(row.get("destination_fias"))
            cluster_id = parse_int(row.get("cluster_id"))
            if None in {shipment_month, origin_id, region, destination_fias, cluster_id}:
                raise ValueError(f"cluster assignment row {row_number}: key fields are required")
            key = (str(shipment_month), str(origin_id), str(region))
            if key in seen:
                raise ValueError(
                    f"cluster assignment row {row_number}: route mix must collapse to one row per evaluation key"
                )
            seen.add(key)
            records.append(
                ClusterEvaluationAssignment(
                    shipment_month=str(shipment_month),
                    actual_origin_id=str(origin_id),
                    destination_region=str(region),
                    destination_fias=str(destination_fias),
                    cluster_id=int(cluster_id),
                    cluster_price=parse_float(row.get("cluster_price")),
                    cluster_rub_per_km=parse_float(row.get("cluster_rub_per_km")),
                )
            )
    return records
