from __future__ import annotations

import pytest

from backend.product_modes import (
    GeoCostParameters,
    GeoCostProductMode,
    GeoVolumeParameters,
    GeoVolumeProductMode,
    ModeDataset,
    ProductClusteringError,
)
from ml.clustering.base import ClusterPoint, ClusterResult
from ml.clustering.geo_cost import GeoCostClusterer
from ml.clustering.geo_volume import GeoVolumeClusterer
from ml.spatial.graph import SpatialEdge, SpatialGraph


class RecordingClusterer:
    algorithm = "recording"

    def __init__(self) -> None:
        self.points = []
        self.parameters = {}

    def fit(self, points, parameters):
        self.points = list(points)
        self.parameters = dict(parameters)
        return ClusterResult(
            self.algorithm,
            {key: value for key, value in parameters.items() if key != "spatial_graph"},
            {point.id: index % 2 for index, point in enumerate(points)},
            (),
            (),
            {},
        )


def _points() -> tuple[ClusterPoint, ...]:
    return (
        ClusterPoint("a", "A", "R", 0.0, 0.0, 10, 100.0, 10.0),
        ClusterPoint("b", "B", "R", 1.0, 0.0, 0, None, None),
        ClusterPoint("c", "C", "R", 2.0, 0.0, -2, 300.0, 30.0),
        ClusterPoint("d", "D", "R", 3.0, 0.0, 5, 400.0, 40.0),
    )


def _graph() -> SpatialGraph:
    return SpatialGraph(
        node_ids=("a", "b", "c", "d"),
        edges=(
            SpatialEdge("a", "b", 1.0),
            SpatialEdge("b", "c", 1.0),
            SpatialEdge("c", "d", 1.0),
        ),
        adjacency={
            "a": frozenset({"b"}),
            "b": frozenset({"a", "c"}),
            "c": frozenset({"b", "d"}),
            "d": frozenset({"c"}),
        },
        connected_components=(("a", "b", "c", "d"),),
        isolated_point_ids=(),
        method="test",
        parameters={"source": "full"},
        audit={"node_count": 4, "edge_count": 3},
    )


def test_geo_volume_adapter_normalizes_implicit_defaults():
    mode = GeoVolumeProductMode(GeoVolumeClusterer())

    selection = mode.select({})

    assert GeoVolumeParameters.from_selection(selection) == GeoVolumeParameters(
        k_mode="auto",
        n_clusters="auto",
        geography_weight=0.7,
        volume_weight=0.3,
    )


def test_geo_volume_keeps_all_spatial_points_and_the_full_graph():
    clusterer = RecordingClusterer()
    mode = GeoVolumeProductMode(clusterer)
    selection = mode.select(
        {
            "k_mode": "auto",
            "n_clusters": "auto",
            "geography_weight": 0.8,
            "volume_weight": 0.2,
        }
    )
    graph = _graph()

    outcome = mode.evaluate(selection, ModeDataset(_points(), graph), "run")

    assert tuple(point.id for point in clusterer.points) == ("a", "b", "c", "d")
    assert tuple(point.trip_count for point in clusterer.points) == (10, 0, -2, 5)
    assert all(point.weighted_price is None for point in clusterer.points)
    assert all(point.weighted_rub_per_km is None for point in clusterer.points)
    assert clusterer.parameters == {
        "spatial_graph": graph,
        "n_clusters": "auto",
        "k_min": 2,
        "k_max": 20,
        "geography_weight": 0.8,
        "volume_weight": 0.2,
    }
    assert outcome.status == "success"
    assert outcome.result.point_assignments == {"a": 0, "b": 1, "c": 0, "d": 1}


def test_geo_cost_adapter_normalizes_implicit_defaults():
    mode = GeoCostProductMode(RecordingClusterer())

    selection = mode.select({})

    assert GeoCostParameters.from_selection(selection) == GeoCostParameters(
        k_mode="auto",
        n_clusters="auto",
        geography_weight=0.7,
        economics_weight=0.3,
    )


def test_geo_cost_filters_economics_then_uses_an_induced_full_graph():
    clusterer = RecordingClusterer()
    mode = GeoCostProductMode(clusterer)
    selection = mode.select(
        {
            "k_mode": "auto",
            "n_clusters": "auto",
            "geography_weight": 0.6,
            "economics_weight": 0.4,
        }
    )

    outcome = mode.evaluate(selection, ModeDataset(_points(), _graph()), "run")

    assert tuple(point.id for point in clusterer.points) == ("a", "d")
    graph = clusterer.parameters["spatial_graph"]
    assert graph.node_ids == ("a", "d")
    assert graph.edges == ()
    assert graph.parameters["induced_subgraph"] is True
    assert clusterer.parameters == {
        "spatial_graph": graph,
        "n_clusters": "auto",
        "k_min": 2,
        "k_max": 20,
        "geography_weight": 0.6,
        "economics_weight": 0.4,
    }
    assert outcome.status == "success"


@pytest.mark.parametrize(
    ("mode", "business_name"),
    [
        (GeoVolumeProductMode(RecordingClusterer()), "volume_weight"),
        (GeoCostProductMode(RecordingClusterer()), "economics_weight"),
    ],
)
def test_business_partition_adapters_accept_only_the_frozen_weight_presets(mode, business_name):
    for geography_weight, business_weight in ((0.8, 0.2), (0.7, 0.3), (0.6, 0.4)):
        selection = mode.select(
            {
                "geography_weight": geography_weight,
                business_name: business_weight,
            }
        )
        assert selection.as_parameters()[business_name] == business_weight

    with pytest.raises(ProductClusteringError) as captured:
        mode.select({"geography_weight": 0.5, business_name: 0.5})
    assert captured.value.code == "INVALID_MODE_PARAMETERS"
    assert captured.value.status == 400


@pytest.mark.parametrize(
    "mode",
    [GeoVolumeProductMode(RecordingClusterer()), GeoCostProductMode(RecordingClusterer())],
)
def test_business_partition_adapters_reject_unknown_parameters_and_invalid_manual_k(mode):
    with pytest.raises(ProductClusteringError) as unknown:
        mode.select({"unsupported": True})
    assert unknown.value.code == "INVALID_MODE_PARAMETERS"

    with pytest.raises(ProductClusteringError) as invalid_k:
        mode.select({"k_mode": "manual", "n_clusters": 21})
    assert invalid_k.value.code == "INVALID_CLUSTER_COUNT"
    assert invalid_k.value.status == 400


def test_geo_cost_reports_missing_economics_before_invoking_the_algorithm():
    mode = GeoCostProductMode(RecordingClusterer())
    points = (
        ClusterPoint("a", "A", "R", 0.0, 0.0, 1, 100.0, 10.0),
        ClusterPoint("b", "B", "R", 1.0, 0.0, 1, None, None),
    )
    graph = SpatialGraph(
        node_ids=("a", "b"),
        edges=(SpatialEdge("a", "b", 1.0),),
        adjacency={"a": frozenset({"b"}), "b": frozenset({"a"})},
        connected_components=(("a", "b"),),
        isolated_point_ids=(),
        method="test",
        parameters={},
        audit={},
    )

    with pytest.raises(ProductClusteringError) as captured:
        mode.evaluate(mode.select({}), ModeDataset(points, graph), "run")

    assert captured.value.code == "INSUFFICIENT_ECONOMICS"
    assert str(captured.value) == "Недостаточно точек с валидными price, route_length и ₽/км."


@pytest.mark.parametrize(
    ("mode_factory", "business_name"),
    [
        (GeoVolumeProductMode, "volume_weight"),
        (GeoCostProductMode, "economics_weight"),
    ],
)
def test_business_partition_adapters_translate_valid_manual_k(mode_factory, business_name):
    clusterer = RecordingClusterer()
    mode = mode_factory(clusterer)
    points = tuple(
        ClusterPoint(
            point.id,
            point.name,
            point.region,
            point.x,
            point.y,
            max(point.trip_count, 1),
            point.weighted_price or 100.0,
            point.weighted_rub_per_km or 10.0,
        )
        for point in _points()
    )
    selection = mode.select({"k_mode": "manual", "n_clusters": 2, business_name: 0.3})

    mode.evaluate(selection, ModeDataset(points, _graph()), "run")

    assert clusterer.parameters["n_clusters"] == 2
    assert clusterer.parameters["k_min"] == 2
    assert clusterer.parameters["k_max"] == 20


def test_geo_volume_checks_manual_k_against_its_full_effective_graph():
    clusterer = RecordingClusterer()
    mode = GeoVolumeProductMode(clusterer)

    with pytest.raises(ProductClusteringError) as captured:
        mode.evaluate(
            mode.select({"k_mode": "manual", "n_clusters": 5}),
            ModeDataset(_points(), _graph()),
            "run",
        )

    assert captured.value.code == "INVALID_CLUSTER_COUNT"
    assert str(captured.value) == "K=5 невозможно для 4 связанных точек в 1 компонентах."
    assert clusterer.points == []


def test_geo_cost_checks_manual_k_after_economic_eligibility_and_induction():
    clusterer = RecordingClusterer()
    mode = GeoCostProductMode(clusterer)

    with pytest.raises(ProductClusteringError) as captured:
        mode.evaluate(
            mode.select({"k_mode": "manual", "n_clusters": 2}),
            ModeDataset(_points(), _graph()),
            "run",
        )

    assert captured.value.code == "INVALID_CLUSTER_COUNT"
    assert str(captured.value) == "K=2 невозможно для 0 связанных точек в 0 компонентах."
    assert clusterer.points == []


@pytest.mark.parametrize(
    ("mode_factory", "clusterer_factory", "business_name"),
    [
        (GeoVolumeProductMode, GeoVolumeClusterer, "volume_weight"),
        (GeoCostProductMode, GeoCostClusterer, "economics_weight"),
    ],
)
def test_business_partition_adapter_outcomes_are_deterministic(
    mode_factory, clusterer_factory, business_name
):
    mode = mode_factory(clusterer_factory())
    points = tuple(
        ClusterPoint(
            point.id,
            point.name,
            point.region,
            point.x,
            point.y,
            max(point.trip_count, 1),
            point.weighted_price or 100.0,
            point.weighted_rub_per_km or 10.0,
        )
        for point in _points()
    )
    selection = mode.select({"k_mode": "manual", "n_clusters": 2, business_name: 0.3})
    dataset = ModeDataset(points, _graph())

    first = mode.evaluate(selection, dataset, "run")
    second = mode.evaluate(selection, dataset, "run")

    assert first == second
