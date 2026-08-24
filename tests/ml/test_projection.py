import math

from ml.spatial.projection import LocalProjection, haversine_distance_m


def test_local_projected_distance_matches_haversine_within_region():
    saint_petersburg = (59.9343, 30.3351)
    vyborg = (60.7131, 28.7326)
    projection = LocalProjection.from_coordinates([saint_petersburg, vyborg])

    first = projection.project(*saint_petersburg)
    second = projection.project(*vyborg)
    projected = math.dist(first, second)
    haversine = haversine_distance_m(saint_petersburg, vyborg)

    assert abs(projected - haversine) / haversine < 0.01


def test_projection_round_trip():
    projection = LocalProjection(59.9, 31.0)
    original = (60.1, 30.2)

    restored = projection.unproject(*projection.project(*original))

    assert math.isclose(restored[0], original[0], abs_tol=1e-8)
    assert math.isclose(restored[1], original[1], abs_tol=1e-8)
