import os
import json
from backend.geocoder import KNOWN_COORDS

def clean_cache():
    cache_path = os.path.join(os.path.dirname(__file__), 'backend', 'cache', 'coords_cache.json')
    if not os.path.exists(cache_path):
        print("Cache not found.")
        return
        
    with open(cache_path, 'r', encoding='utf-8') as f:
        cache = json.load(f)
        
    # Собераем все координаты больших городов из словаря
    known_values = set()
    for coords in KNOWN_COORDS.values():
        known_values.add(tuple(coords))

    rural_prefixes = ("д ", "с ", "п ", "пос ", "х ", "ст ", "рп ", "с/с ", "пгт ")
    
    deleted = 0
    keys_to_delete = []
    
    for key, coords in cache.items():
        if coords is None:
            continue
            
        town = key.split("::")[0].strip()
        is_rural = any(town.startswith(p) for p in rural_prefixes)
        
        if is_rural:
            # Если координаты этой деревни полностью совпадают с координатами крупного города
            if tuple(coords) in known_values:
                keys_to_delete.append(key)
                
    for k in keys_to_delete:
        del cache[k]
        deleted += 1
        print(f"Удален ошибочный кэш для: {k}")
        
    if deleted > 0:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print(f"Очистка кэша завершена! Удалено {deleted} неправильных записей.")
    else:
        print("Очистка кэша завершена! Ошибочных записей не найдено.")

if __name__ == '__main__':
    clean_cache()
