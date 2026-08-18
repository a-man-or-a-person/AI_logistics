"""
Геокодер: преобразует название города в координаты.
Стратегия:
  1. Встроенный словарь (быстро, без сети)
  2. Кэш из JSON файла
  3. Nominatim (geopy) — только если нет в кэше
  4. Fallback — координаты центра региона
"""

import json
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

CACHE_FILE = os.path.join(os.path.dirname(__file__), "cache", "coords_cache.json")

# ── Центры регионов России (fallback) ─────────────────────────────────────────
REGION_CENTERS: dict[str, tuple[float, float]] = {
    "Москва": (55.7558, 37.6173),
    "Московская область": (55.8167, 37.0333),
    "Санкт-Петербург": (59.9311, 30.3609),
    "Ленинградская область": (59.9311, 30.3609),
    "Республика Адыгея": (44.6087, 40.1069),
    "Республика Алтай": (51.9583, 85.9603),
    "Республика Башкортостан": (54.7348, 55.9578),
    "Республика Бурятия": (51.8340, 107.5849),
    "Республика Дагестан": (42.9849, 47.5047),
    "Республика Ингушетия": (43.1667, 44.9667),
    "Кабардино-Балкарская Республика": (43.4961, 43.6186),
    "Республика Калмыкия": (46.3078, 44.2558),
    "Карачаево-Черкесская Республика": (44.2269, 42.0486),
    "Республика Карелия": (61.785, 34.347),
    "Республика Коми": (61.6689, 50.8364),
    "Республика Крым": (44.9521, 34.1024),
    "Республика Марий Эл": (56.6344, 47.8864),
    "Республика Мордовия": (54.1878, 45.1833),
    "Республика Саха (Якутия)": (62.0355, 129.6755),
    "Республика Северная Осетия-Алания": (43.0205, 44.6819),
    "Республика Татарстан": (55.7887, 49.1221),
    "Республика Тыва": (51.7191, 94.4378),
    "Удмуртская Республика": (56.8489, 53.2044),
    "Республика Хакасия": (53.7153, 91.4292),
    "Чеченская Республика": (43.3179, 45.6950),
    "Чувашская Республика": (56.1439, 47.2489),
    "Алтайский край": (53.3481, 83.7798),
    "Забайкальский край": (52.0341, 113.5005),
    "Камчатский край": (53.0667, 158.6333),
    "Краснодарский край": (45.0353, 38.9753),
    "Красноярский край": (56.0153, 92.8932),
    "Пермский край": (58.0105, 56.2502),
    "Приморский край": (43.1332, 131.9113),
    "Ставропольский край": (45.0472, 41.9692),
    "Хабаровский край": (48.4827, 135.0840),
    "Амурская область": (50.2907, 128.4844),
    "Архангельская область": (64.5397, 40.5156),
    "Астраханская область": (46.3497, 48.0408),
    "Белгородская область": (50.5958, 36.5875),
    "Брянская область": (53.2436, 34.3642),
    "Владимирская область": (56.1289, 40.4076),
    "Волгоградская область": (48.7194, 44.5018),
    "Вологодская область": (59.2167, 39.9017),
    "Воронежская область": (51.6717, 39.2103),
    "Ивановская область": (57.0003, 40.9739),
    "Иркутская область": (52.2978, 104.2964),
    "Калининградская область": (54.7104, 20.4522),
    "Калужская область": (54.5133, 36.2614),
    "Кемеровская область": (55.3542, 86.0878),
    "Кировская область": (58.6036, 49.6681),
    "Костромская область": (57.7675, 40.9269),
    "Курганская область": (55.4413, 65.3413),
    "Курская область": (51.7303, 36.1928),
    "Липецкая область": (52.6047, 39.5703),
    "Магаданская область": (59.5631, 150.7864),
    "Мурманская область": (68.9585, 33.0827),
    "Нижегородская область": (56.3269, 44.0059),
    "Новгородская область": (58.5219, 31.2694),
    "Новосибирская область": (54.9924, 82.8963),
    "Омская область": (54.9924, 73.3686),
    "Оренбургская область": (51.7727, 55.0988),
    "Орловская область": (52.9686, 36.0694),
    "Пензенская область": (53.1953, 45.0169),
    "Псковская область": (57.8194, 28.3314),
    "Ростовская область": (47.2357, 39.7015),
    "Рязанская область": (54.6297, 39.7408),
    "Самарская область": (53.1959, 50.1467),
    "Саратовская область": (51.5328, 46.0342),
    "Сахалинская область": (46.9641, 142.7285),
    "Свердловская область": (56.8389, 60.6057),
    "Смоленская область": (54.7826, 32.0453),
    "Тамбовская область": (52.7319, 41.4433),
    "Тверская область": (56.8587, 35.9176),
    "Томская область": (56.4977, 84.9744),
    "Тульская область": (54.1931, 37.6178),
    "Тюменская область": (57.1522, 68.0089),
    "Ульяновская область": (54.3167, 48.3736),
    "Челябинская область": (55.1644, 61.4368),
    "Ярославская область": (57.6261, 39.8845),
    "Еврейская автономная область": (48.7897, 132.9208),
    "Ненецкий автономный округ": (67.6389, 53.0069),
    "Ханты-Мансийский автономный округ": (61.0042, 69.0019),
    "Ханты-Мансийский автономный округ - Югра": (61.0042, 69.0019),
    "Чукотский автономный округ": (64.7351, 177.5105),
    "Ямало-Ненецкий автономный округ": (66.5308, 66.6139),
    "Севастополь": (44.6167, 33.5254),
    "Республика Северная Осетия - Алания": (43.0205, 44.6819),
}

# Большой встроенный словарь координат городов России


# ── Нормализация названий ─────────────────────────────────────────────────────

# Расширенный список префиксов для нормализации
_PREFIXES = (
    "г ", "г. ", "гп ", "гп. ", "с ", "с. ", "д ", "д. ",
    "п ", "п. ", "пгт ", "пгт. ", "рп ", "рп. ", "пос ",
    "пос. ", "село ", "деревня ", "поселок ", "посёлок ",
    "станица ", "ст-ца ", "аул ", "хутор ", "х ", "х. ",
    "слобода ", "высел ", "тер ", "мкр ", "мкр. ",
    "город ", "городской поселок ", "рабочий поселок ",
)

def _normalize_town(name: str) -> str:
    """Нормализует название населённого пункта — убирает типовые префиксы."""
    if not name:
        return ""
    name = name.strip()
    lower = name.lower()
    for prefix in _PREFIXES:
        if lower.startswith(prefix):
            return name[len(prefix):].strip()
    return name


def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    try:
        temp_file = CACHE_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        try:
            os.replace(temp_file, CACHE_FILE)
        except OSError:
            # Fallback на случай блокировки файла (особенно на Windows)
            import shutil
            shutil.copyfile(temp_file, CACHE_FILE)
            try:
                os.remove(temp_file)
            except OSError:
                pass
    except Exception as e:
        logger.error(f"Ошибка сохранения кэша координат: {e}")


_cache: dict = _load_cache()
_cache_lock = threading.Lock()
_cache_file_lock = threading.Lock()


def _persist_cache() -> None:
    """Атомарно сохраняет согласованный снимок кэша без удержания основного lock."""
    with _cache_lock:
        snapshot = dict(_cache)
    with _cache_file_lock:
        _save_cache(snapshot)

# ── Состояние фонового геокодирования ─────────────────────────────────────────
_bg_status = {
    "running": False,
    "total": 0,
    "done": 0,
    "found": 0,
    "failed": 0,
}
_bg_lock = threading.Lock()


def get_geocode_status() -> dict:
    """Возвращает текущий статус фонового геокодирования."""
    with _bg_lock:
        return dict(_bg_status)


_geolocators = None

def _get_geolocators():
    global _geolocators
    if _geolocators is None:
        _geolocators = []
        try:
            from geopy.geocoders import ArcGIS, Nominatim, Photon
            _geolocators.append(Nominatim(user_agent="logistics_ai_map_v2", timeout=10))
            _geolocators.append(Photon(timeout=10))
            _geolocators.append(ArcGIS(timeout=10))
        except ImportError:
            logger.warning("geopy не установлен — только встроенный словарь и кэш")
    return _geolocators


def _clean_town_name(name: str) -> str:
    """Нормализует название города для поиска."""
    return name.strip() if name else ""


def geocode_town(town_name: str, region: str = "", offline_only: bool = True, force_recalc: bool = False) -> tuple[float, float] | None:
    """
    Возвращает (lat, lon) или None.
    Поиск: встроенный словарь → кэш → Nominatim (если offline_only=False) → центр региона.

    По умолчанию offline_only=True — не вызывает Nominatim, мгновенно.
    """
    if not town_name:
        return None

    town_clean = _clean_town_name(town_name)
    normalized = _normalize_town(town_clean)

    # 1. Кэш
    cache_key = f"{town_clean}::{region}"
    normalized_cache_key = f"{normalized}::{region}" if normalized else None
    
    if not force_recalc:
        with _cache_lock:
            if cache_key in _cache:
                coords = _cache[cache_key]
                if coords is None:
                    if region and region in REGION_CENTERS:
                        return REGION_CENTERS[region]
                    return None
                return tuple(coords)
            if normalized_cache_key and normalized_cache_key != cache_key and normalized_cache_key in _cache:
                coords = _cache[normalized_cache_key]
                if coords is None:
                    if region and region in REGION_CENTERS:
                        return REGION_CENTERS[region]
                    return None
                return tuple(coords)

    # 2. Nominatim/Photon/ArcGIS — только если явно запрошено и не в offline режиме
    if not offline_only:
        geocoders = _get_geolocators()
        if geocoders:
            import random
            geocoder = random.choice(geocoders)
            # Попробуем несколько вариантов поиска
            search_variants = []
            if region:
                search_variants.append(f"{normalized or town_clean}, {region}, Россия")
                search_variants.append(f"{town_clean}, {region}, Россия")
            else:
                search_variants.append(f"{normalized or town_clean}, Россия")
                search_variants.append(f"{town_clean}, Россия")

            for search_query in search_variants:
                try:
                    time.sleep(1.1)
                    if geocoder.__class__.__name__ == 'Nominatim':
                        location = geocoder.geocode(search_query, language="ru")
                    elif geocoder.__class__.__name__ == 'Photon':
                        location = geocoder.geocode(search_query, language="default")
                    else:
                        location = geocoder.geocode(search_query)
                        
                    if location:
                        coords = [location.latitude, location.longitude]
                        with _cache_lock:
                            _cache[cache_key] = coords
                        _persist_cache()
                        return tuple(coords)
                except Exception as e:
                    logger.warning(f"Геокодирование '{search_query}' не удалось: {e}")

            # Не найден через Nominatim — кэшируем как None
            with _cache_lock:
                _cache[cache_key] = None
            _persist_cache()

    # 4. Fallback — координаты центра региона
    if region and region in REGION_CENTERS:
        return REGION_CENTERS[region]

    return None


def geocode_batch(towns: list[tuple[str, str]], offline_only: bool = True) -> dict[str, tuple[float, float] | None]:
    """
    Геокодирует список (town_name, region).
    Возвращает {town_name::region: (lat, lon) or None}.

    offline_only=True (по умолчанию) — только кэш и словарь, без сети.
    """
    result = {}
    for town, region in towns:
        coords = geocode_town(town, region, offline_only=offline_only)
        result[f"{town}::{region}"] = coords

    return result


def geocode_all_towns_background(towns: list[tuple[str, str]]) -> None:
    """
    Фоновое геокодирование через Nominatim для городов которых нет в кэше/словаре.
    Вызывать в отдельном потоке.
    """
    global _bg_status

    # Определяем, какие города нужно геокодировать
    missing = []
    for town, region in towns:
        town_clean = _clean_town_name(town)
        normalized = _normalize_town(town_clean)

        found = False
        cache_key = f"{town_clean}::{region}"
        normalized_cache_key = f"{normalized}::{region}" if normalized else None
        
        with _cache_lock:
            if cache_key in _cache or (normalized_cache_key and normalized_cache_key != cache_key and normalized_cache_key in _cache):
                found = True

        if not found:
            missing.append((town, region))

    if not missing:
        logger.info("Все города уже в кэше или встроенном словаре")
        with _bg_lock:
            _bg_status = {"running": False, "total": 0, "done": 0, "found": 0, "failed": 0}
        return

    with _bg_lock:
        _bg_status = {"running": True, "total": len(missing), "done": 0, "found": 0, "failed": 0}

    logger.info(f"🌍 Фоновое геокодирование: {len(missing)} городов через мультипровайдер...")

    geocoded = 0
    failed = 0
    geocoders = _get_geolocators()

    import concurrent.futures
    import itertools

    if not geocoders:
        with _bg_lock:
            _bg_status["running"] = False
        return

    geocoder_cycle = itertools.cycle(geocoders)

    def _process_town(item):
        town, region, geocoder = item
        town_clean = _clean_town_name(town)
        normalized = _normalize_town(town_clean)
        cache_key = f"{town_clean}::{region}"

        search_variants = []
        if region:
            search_variants.append(f"{normalized or town_clean}, {region}, Россия")
            search_variants.append(f"{town_clean}, {region}, Россия")
        else:
            search_variants.append(f"{normalized or town_clean}, Россия")
            search_variants.append(f"{town_clean}, Россия")

        coords = None
        for search_query in search_variants:
            try:
                time.sleep(1.1) # Защита от спама (пауза в каждом потоке)
                if geocoder.__class__.__name__ == 'Nominatim':
                    location = geocoder.geocode(search_query, language="ru")
                elif geocoder.__class__.__name__ == 'Photon':
                    location = geocoder.geocode(search_query, language="default")
                else:
                    location = geocoder.geocode(search_query)

                if location:
                    coords = [location.latitude, location.longitude]
                    break
            except Exception as e:
                logger.warning(f"Ошибка {geocoder.__class__.__name__} для '{search_query}': {e}")

        with _cache_lock:
            _cache[cache_key] = coords

        return (region, coords)

    tasks_args = [(t, r, next(geocoder_cycle)) for t, r in missing]

    # Запускаем пул потоков (3 потока, так как 3 провайдера)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(geocoders)) as executor:
        for i, result in enumerate(executor.map(_process_town, tasks_args)):
            region, coords = result
            if coords:
                if region in REGION_CENTERS and coords == REGION_CENTERS[region]:
                    failed += 1
                else:
                    geocoded += 1
            else:
                failed += 1

            with _bg_lock:
                _bg_status["done"] = i + 1
                _bg_status["found"] = geocoded
                _bg_status["failed"] = failed

            if (i + 1) % 25 == 0:
                _persist_cache()

            if (i + 1) % 50 == 0:
                logger.info(
                    f"  Геокодирование: {i + 1}/{len(missing)} "
                    f"(найдено: {geocoded}, не найдено: {failed})"
                )

    _persist_cache()

    with _bg_lock:
        _bg_status["running"] = False

    logger.info(
        f"✅ Фоновое геокодирование завершено: "
        f"{geocoded}/{len(missing)} найдено, {failed} не найдено"
    )
