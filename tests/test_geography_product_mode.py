from __future__ import annotations

import pytest

from backend.product_modes import GeographyProductMode, ModeDataset
from backend.services.clustering_service import ProductClusteringError
from ml.clustering.base import ClusterPoint, ClusterResult
from ml.spatial.graph import SpatialGraph


class RecordingGeographyClusterer:
    algorithm = "recording_geography"

    def __init__(self) -> None:
        self.points: list[ClusterPoint] = []
        self.parameters = {}

    def fit(self, points, parameters):
        self.points = list(points)
        self.parameters = dict(parameters)
        return ClusterResult(
            algorithm=self.algorithm,
            parameters={"n_clusters": parameters["n_clusters"]},
            point_assignments={point.id: 0 for point in points},
            clusters=(),
            noise_point_ids=(),
            metrics={},
        )


def _graph(*point_ids: str) -> SpatialGraph:
    return SpatialGraph(
        node_ids=point_ids,
        edges=(),
        adjacency={point_id: frozenset() for point_id in point_ids},
        connected_components=tuple((point_id,) for point_id in point_ids),
        isolated_point_ids=point_ids,
        method="test",
        parameters={},
        audit={},
    )


def _points() -> tuple[ClusterPoint, ...]:
    return (
        ClusterPoint("a", "A", "Region", 0.0, 0.0, 2, 1000.0, 10.0),
        ClusterPoint("b", "B", "Region", 1.0, 1.0, 3, 2000.0, 20.0),
    )


def test_geography_adapter_owns_defaults_and_manual_k_validation():
    mode = GeographyProductMode(RecordingGeographyClusterer())

    assert mode.select({}).as_parameters() == {
        "k_mode": "auto",
        "n_clusters": "auto",
    }
    assert mode.select({"n_clusters": 2}).as_parameters() == {
        "k_mode": "manual",
        "n_clusters": 2,
    }

    with pytest.raises(ProductClusteringError) as captured:
        mode.select({"k_mode": "manual", "n_clusters": 1})

    assert captured.value.code == "INVALID_CLUSTER_COUNT"
    assert captured.value.status == 400
    assert str(captured.value) == "n_clusters должен быть целым числом от 2 до 20."


def test_geography_adapter_previews_all_coordinate_eligible_points_without_a_graph():
    mode = GeographyProductMode(RecordingGeographyClusterer())
    selection = mode.select({})

    preview = mode.evaluate(selection, ModeDataset(_points(), None), "preview")

    assert preview.selection == selection
    assert preview.eligible_point_ids == ("a", "b")


def test_geography_adapter_redacts_economics_and_translates_algorithm_parameters():
    clusterer = RecordingGeographyClusterer()
    mode = GeographyProductMode(clusterer)
    selection = mode.select({"k_mode": "auto", "n_clusters": "auto"})
    graph = _graph("a", "b")

    outcome = mode.evaluate(selection, ModeDataset(_points(), graph), "run")

    assert outcome.status == "success"
    assert all(point.weighted_price is None for point in clusterer.points)
    assert all(point.weighted_rub_per_km is None for point in clusterer.points)
    assert clusterer.parameters == {
        "spatial_graph": graph,
        "n_clusters": "auto",
        "k_min": 2,
        "k_max": 20,
    }


def test_geography_adapter_preserves_manual_k_feasibility_error():
    mode = GeographyProductMode(RecordingGeographyClusterer())
    selection = mode.select({"k_mode": "manual", "n_clusters": 2})

    with pytest.raises(ProductClusteringError) as captured:
        mode.evaluate(selection, ModeDataset(_points(), _graph("a", "b")), "run")

    assert captured.value.code == "INVALID_CLUSTER_COUNT"
    assert str(captured.value) == "K=2 невозможно для 0 связанных точек в 0 компонентах."
