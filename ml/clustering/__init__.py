"""Algorithm-neutral clustering contracts."""

from ml.clustering.base import (
    Clusterer,
    ClusterPoint,
    ClusterResult,
    ClusterSummary,
    summarize_assignments,
)

__all__ = [
    "ClusterPoint",
    "ClusterResult",
    "ClusterSummary",
    "Clusterer",
    "summarize_assignments",
]
