from backend.data_processor import calculate_rub_per_km


def _record(price: float, route_length: float) -> dict:
    return {"price": price, "route_length": route_length}


def test_rub_per_km_uses_only_paired_values():
    records = [_record(100, 0), _record(0, 10), _record(240, 20)]

    assert calculate_rub_per_km(records) == 12


def test_rub_per_km_returns_zero_without_complete_routes():
    records = [_record(100, 0), _record(0, 10)]

    assert calculate_rub_per_km(records) == 0
