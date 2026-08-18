import json
import logging
import os

from backend.data_processor import load_data
from backend.geocoder import _clean_town_name, _normalize_town

logging.basicConfig(level=logging.INFO)

def upgrade_cache():
    cache_path = os.path.join(os.path.dirname(__file__), 'backend', 'cache', 'coords_cache.json')
    if not os.path.exists(cache_path):
        print("Cache not found.")
        return
        
    with open(cache_path, encoding='utf-8') as f:
        cache = json.load(f)
        
    data = load_data()
    all_towns = set()
    for info in data['shipment_towns'].values():
        all_towns.add((info['town'], info['region']))
    for info in data['delivery_towns'].values():
        all_towns.add((info['town'], info['region']))
        
    updated = 0
    for town, region in all_towns:
        town_clean = _clean_town_name(town)
        normalized = _normalize_town(town_clean)
        
        cache_key = f"{town_clean}::{region}"
        if cache_key not in cache:
            # Check old cache formats
            coords = None
            if town_clean in cache:
                coords = cache[town_clean]
            elif normalized in cache:
                coords = cache[normalized]
                
            if coords is not None:
                cache[cache_key] = coords
                updated += 1
                
    if updated > 0:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print(f"Cache upgraded successfully! Migrated {updated} composite keys.")
    else:
        print("No keys needed migrating.")

if __name__ == '__main__':
    upgrade_cache()
