"""Cross-slice stability diagnostics for deterministic clustering modes."""

from __future__ import annotations

from collections.abc import Iterable

from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from ml.clustering.base import ClusterResult


def common_membership_stability(
    left: ClusterResult, right: ClusterResult
) -> dict[str, float | int | None]:
    common = sorted(set(left.point_assignments) & set(right.point_assignments))
    common_assigned = [
        point_id
        for point_id in common
        if left.point_assignments[point_id] >= 0
        and right.point_assignments[point_id] >= 0
    ]
    if len(common_assigned) < 2:
        return {
            "common_point_count": len(common),
            "common_assigned_point_count": len(common_assigned),
            "ari": None,
            "nmi": None,
        }
    left_labels = [left.point_assignments[point_id] for point_id in common_assigned]
    right_labels = [right.point_assignments[point_id] for point_id in common_assigned]
    return {
        "common_point_count": len(common),
        "common_assigned_point_count": len(common_assigned),
        "ari": float(adjusted_rand_score(left_labels, right_labels)),
        "nmi": float(normalized_mutual_info_score(left_labels, right_labels)),
    }


def candidate_recurrence(results: Iterable[ClusterResult]) -> dict[str, float]:
    values = list(results)
    if not values:
        return {}
    occurrences: dict[str, int] = {}
    for result in values:
        candidates = {
            point_id
            for cluster in result.clusters
            if cluster.cluster_type in {"bear_zone", "expensive_singleton"}
            for point_id, cluster_id in result.point_assignments.items()
            if cluster_id == cluster.cluster_id
        }
        for point_id in candidates:
            occurrences[point_id] = occurrences.get(point_id, 0) + 1
    return {
        point_id: count / len(values)
        for point_id, count in sorted(occurrences.items())
    }


def mode_slice_stability(
    results_by_slice: dict[str, dict[str, ClusterResult]]
) -> dict[str, object]:
    """Compare leave-period-out or period-specific results supplied by a runner."""
    slices = sorted(results_by_slice)
    modes = sorted(
        {
            mode
            for slice_results in results_by_slice.values()
            for mode in slice_results
        }
    )
    report: dict[str, object] = {"slices": slices, "modes": {}}
    mode_report = report["modes"]
    assert isinstance(mode_report, dict)
    for mode in modes:
        available = [
            (slice_name, results_by_slice[slice_name][mode])
            for slice_name in slices
            if mode in results_by_slice[slice_name]
        ]
        pairs = [
            {
                "left_slice": left_name,
                "right_slice": right_name,
                **common_membership_stability(left, right),
            }
            for index, (left_name, left) in enumerate(available)
            for right_name, right in available[index + 1 :]
        ]
        payload: dict[str, object] = {"pairwise_membership": pairs}
        if mode == "bear_zones":
            payload["candidate_recurrence"] = candidate_recurrence(
                result for _, result in available
            )
        mode_report[mode] = payload
    return report
