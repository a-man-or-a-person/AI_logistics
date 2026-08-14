"""Diagnostic: check missing geocode towns — output to file."""
import json
from backend.data_processor import load_data
from backend.geocoder import geocode_batch, KNOWN_COORDS, _cache

data = load_data()
all_towns = set()
for k, v in data['shipment_towns'].items():
    all_towns.add((v['town'], v['region']))
for k, v in data['delivery_towns'].items():
    all_towns.add((v['town'], v['region']))

coords = geocode_batch(list(all_towns), offline_only=True)
found = sum(1 for c in coords.values() if c is not None)
missing = [(t, r) for (t, r) in all_towns if coords.get(t) is None]

result = {
    "total_unique_towns": len(all_towns),
    "shipment_towns_count": len(data['shipment_towns']),
    "delivery_towns_count": len(data['delivery_towns']),
    "geocoded": found,
    "missing_count": len(missing),
    "known_coords_entries": len(KNOWN_COORDS),
    "cache_entries": len(_cache),
    "missing_towns_sample": sorted(missing)[:200],
}

with open("diag_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("Done. See diag_result.json")
