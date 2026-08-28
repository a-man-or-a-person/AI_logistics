from ml.clustering.base import ClusterPoint, summarize_assignments
from ml.evaluation.clustering_stability import mode_slice_stability


def test_mode_slice_stability_reports_common_fias_ari_and_nmi():
    # summarize_assignments is immutable; dataclasses.replace keeps the test concise.
    from dataclasses import replace

    left = replace(
        summarize_assignments(
            [
                ClusterPoint("a", "a", "R", 0, 0),
                ClusterPoint("b", "b", "R", 1, 0),
                ClusterPoint("c", "c", "R", 2, 0),
            ],
            {"a": 0, "b": 0, "c": 1},
            algorithm="test",
            parameters={},
        ),
        mode="geography",
    )
    right = replace(left)

    report = mode_slice_stability(
        {"current": {"geography": left}, "without_current": {"geography": right}}
    )

    pair = report["modes"]["geography"]["pairwise_membership"][0]
    assert pair["ari"] == 1
    assert pair["nmi"] == 1
    assert pair["common_assigned_point_count"] == 3
