import pytest

from backend.product_modes import (
    BearVolumeZonesParameters,
    BearVolumeZonesProductMode,
    BearZonesParameters,
    BearZonesProductMode,
    ModeDataset,
    ProductClusteringError,
)
from ml.clustering.base import ClusterPoint, ClusterResult
from ml.clustering.bear_volume_zones import BearVolumeZoneDetector
from ml.clustering.bear_zones import BearZoneDetector
from ml.spatial.graph import SpatialEdge, SpatialGraph


class RecordingBearClusterer:
    algorithm = "recording_bear"

    def __init__(self) -> None:
        self.points = []
        self.parameters = {}

    def fit(self, points, parameters):
        self.points = list(points)
        self.parameters = dict(parameters)
        return ClusterResult(
            self.algorithm,
            {key: value for key, value in parameters.items() if key != "spatial_graph"},
            {point.id: -1 for point in points},
            (),
            tuple(point.id for point in points),
            {},
        )


class FailingBearClusterer:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def fit(self, points, parameters):
        raise self.error


def _points() -> tuple[ClusterPoint, ...]:
    return (
        ClusterPoint("a", "A", "R", 0.0, 0.0, 10, 100.0, 10.0),
        ClusterPoint("b", "B", "R", 1.0, 0.0, 0, 200.0, 20.0),
        ClusterPoint("c", "C", "R", 2.0, 0.0, 5, None, None),
        ClusterPoint("d", "D", "R", 3.0, 0.0, 8, 400.0, 40.0),
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


def test_bear_zones_adapter_normalizes_implicit_defaults():
    mode = BearZonesProductMode(BearZoneDetector())

    selection = mode.select({})

    assert BearZonesParameters.from_selection(selection) == BearZonesParameters(
        bear_threshold=0.35,
        singleton_threshold=0.7,
    )


def test_bear_zones_filters_economics_and_returns_successful_no_bears():
    clusterer = RecordingBearClusterer()
    mode = BearZonesProductMode(clusterer)
    selection = mode.select({"bear_threshold": 0.4})

    outcome = mode.evaluate(selection, ModeDataset(_points(), _graph()), "run")

    assert tuple(point.id for point in clusterer.points) == ("a", "d")
    graph = clusterer.parameters["spatial_graph"]
    assert graph.node_ids == ("a", "d")
    assert graph.edges == ()
    assert graph.parameters["induced_subgraph"] is True
    assert clusterer.parameters == {
        "spatial_graph": graph,
        "bear_threshold": 0.4,
        "singleton_threshold": 0.7,
    }
    assert outcome.status == "no_bears"
    assert outcome.result.point_assignments == {"a": -1, "d": -1}


def test_bear_volume_zones_adapter_normalizes_implicit_defaults():
    mode = BearVolumeZonesProductMode(RecordingBearClusterer())

    selection = mode.select({})

    assert BearVolumeZonesParameters.from_selection(selection) == BearVolumeZonesParameters(
        volume_threshold=0.35,
        singleton_threshold=0.7,
    )


def test_bear_volume_zones_filters_positive_volume_and_returns_successful_no_bears():
    clusterer = RecordingBearClusterer()
    mode = BearVolumeZonesProductMode(clusterer)
    selection = mode.select({"volume_threshold": 0.25})

    outcome = mode.evaluate(selection, ModeDataset(_points(), _graph()), "run")

    assert tuple(point.id for point in clusterer.points) == ("a", "c", "d")
    assert all(point.weighted_price is None for point in clusterer.points)
    assert all(point.weighted_rub_per_km is None for point in clusterer.points)
    graph = clusterer.parameters["spatial_graph"]
    assert graph.node_ids == ("a", "c", "d")
    assert graph.edges == (SpatialEdge("c", "d", 1.0),)
    assert graph.parameters["induced_subgraph"] is True
    assert clusterer.parameters == {
        "spatial_graph": graph,
        "volume_threshold": 0.25,
        "singleton_threshold": 0.7,
    }
    assert outcome.status == "no_bears"
    assert outcome.result.point_assignments == {"a": -1, "c": -1, "d": -1}


@pytest.mark.parametrize(
    ("mode", "name"),
    [
        (BearZonesProductMode(RecordingBearClusterer()), "bear_threshold"),
        (BearVolumeZonesProductMode(RecordingBearClusterer()), "volume_threshold"),
    ],
)
def test_bear_adapters_accept_only_advertised_threshold_presets(mode, name):
    for threshold in (0.2, 0.25, 0.3, 0.35, 0.4, 0.5):
        assert mode.select({name: threshold}).as_parameters()[name] == threshold

    with pytest.raises(ProductClusteringError) as error:
        mode.select({name: 0.33})

    assert error.value.code == "INVALID_MODE_PARAMETERS"
    assert error.value.status == 400


@pytest.mark.parametrize(
    "mode",
    [
        BearZonesProductMode(RecordingBearClusterer()),
        BearVolumeZonesProductMode(RecordingBearClusterer()),
    ],
)
def test_bear_adapters_keep_singleton_threshold_fixed(mode):
    with pytest.raises(ProductClusteringError) as error:
        mode.select({"singleton_threshold": 0.8})

    assert error.value.code == "INVALID_MODE_PARAMETERS"
    assert error.value.status == 400


@pytest.mark.parametrize(
    ("mode", "points", "cluster_type"),
    [
        (
            BearZonesProductMode(BearZoneDetector()),
            (
                ClusterPoint("low-a", "Low A", "R", 0.0, 0.0, 50, 100.0, 100.0),
                ClusterPoint("low-b", "Low B", "R", 1.0, 0.0, 50, 100.0, 100.0),
                ClusterPoint("high", "High", "R", 2.0, 0.0, 1, 300.0, 300.0),
            ),
            "expensive_singleton",
        ),
        (
            BearVolumeZonesProductMode(BearVolumeZoneDetector()),
            (
                ClusterPoint("low-a", "Low A", "R", 0.0, 0.0, 10),
                ClusterPoint("low-b", "Low B", "R", 1.0, 0.0, 10),
                ClusterPoint("high", "High", "R", 2.0, 0.0, 100),
            ),
            "high_volume_singleton",
        ),
    ],
)
def test_bear_adapters_preserve_singleton_cluster_semantics(mode, points, cluster_type):
    graph = SpatialGraph(
        node_ids=("low-a", "low-b", "high"),
        edges=(SpatialEdge("low-a", "low-b", 1.0),),
        adjacency={
            "low-a": frozenset({"low-b"}),
            "low-b": frozenset({"low-a"}),
            "high": frozenset(),
        },
        connected_components=(("low-a", "low-b"), ("high",)),
        isolated_point_ids=("high",),
        method="test",
        parameters={},
        audit={},
    )
    selection = mode.select({})

    outcome = mode.evaluate(selection, ModeDataset(points, graph), "run")

    singleton = next(
        cluster for cluster in outcome.result.clusters if cluster.cluster_type == cluster_type
    )
    assert outcome.status == "success"
    assert singleton.point_ids == ("high",)
    assert outcome.result.point_assignments["high"] == singleton.cluster_id
    assert outcome.result.point_assignments["low-a"] == -1
    assert outcome.result.point_assignments["low-b"] == -1


@pytest.mark.parametrize(
    ("mode", "points", "code"),
    [
        (
            BearZonesProductMode(RecordingBearClusterer()),
            (ClusterPoint("missing", "Missing", "R", 0.0, 0.0, 10),),
            "INSUFFICIENT_ECONOMICS",
        ),
        (
            BearVolumeZonesProductMode(RecordingBearClusterer()),
            (ClusterPoint("zero", "Zero", "R", 0.0, 0.0, 0),),
            "INSUFFICIENT_POINTS",
        ),
    ],
)
def test_bear_adapters_preserve_missing_eligible_data_errors(mode, points, code):
    with pytest.raises(ProductClusteringError) as error:
        mode.evaluate(mode.select({}), ModeDataset(points, None), "run")

    assert error.value.code == code
    assert error.value.status == 422


@pytest.mark.parametrize(
    ("mode", "raised", "code"),
    [
        (
            BearZonesProductMode(FailingBearClusterer(ValueError("economic failure"))),
            ValueError,
            "INSUFFICIENT_ECONOMICS",
        ),
        (
            BearVolumeZonesProductMode(FailingBearClusterer(ValueError("volume failure"))),
            ValueError,
            "INSUFFICIENT_POINTS",
        ),
        (
            BearZonesProductMode(FailingBearClusterer(AssertionError("disconnected"))),
            AssertionError,
            "CONNECTIVITY_VIOLATION",
        ),
    ],
)
def test_bear_adapters_preserve_algorithm_error_mapping(mode, raised, code):
    with pytest.raises(ProductClusteringError) as error:
        mode.evaluate(mode.select({}), ModeDataset(_points(), _graph()), "run")

    assert isinstance(error.value.__cause__, raised)
    assert error.value.code == code
    assert error.value.status == 422
