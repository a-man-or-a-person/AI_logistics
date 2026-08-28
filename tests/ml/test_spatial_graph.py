from ml.clustering.base import ClusterPoint
from ml.spatial.graph import SpatialGraphBuilder


def _point(identifier, x, y=0):
    return ClusterPoint(identifier, identifier, "R", x, y, 1, 1000, 10)


def test_graph_is_deterministic_and_detects_components():
    points = [
        _point("a", 0, 0),
        _point("b", 1, 0),
        _point("c", 0, 1),
        _point("d", 100, 0),
        _point("e", 101, 0),
        _point("f", 100, 1),
    ]
    builder = SpatialGraphBuilder()

    first = builder.build(points)
    second = builder.build(list(reversed(points)))

    assert first.edges == second.edges
    assert first.connected_components == second.connected_components
    assert len(first.connected_components) == 2
    assert first.audit["pruned_edge_count"] > 0


def test_very_distant_point_is_not_forced_into_graph():
    points = [
        _point("a", 0, 0),
        _point("b", 1, 0),
        _point("c", 0, 1),
        _point("far", 100, 100),
    ]

    graph = SpatialGraphBuilder().build(points)

    assert graph.isolated_point_ids == ("far",)
    assert not graph.adjacency["far"]


def test_mutual_knn_is_available_as_benchmark():
    points = [_point(str(index), index) for index in range(6)]

    graph = SpatialGraphBuilder(method="mutual_knn", knn_k=2).build(points)

    assert graph.method == "mutual_knn"
    assert graph.audit["edge_count"] > 0
