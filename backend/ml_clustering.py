"""
ml_clustering.py — ML кластеризация точек для логистической карты.

Ключевые особенности:
  1. Координаты конвертируются в Web Mercator (метры) — корректные расстояния
     на высоких широтах России.
  2. Границы кластеров — Voronoi-тесселяция: k центроидов KMeans делят
     всю территорию на k непересекающихся зон без пробелов. Это позволяет
     каждой точке принадлежать ровно одной зоне и вся карта покрыта.
  3. Центроид кластера взвешен по bid_count — маркер ставится там, где
     физически больше заявок.
  4. silhouette_score с sample_size для защиты от O(N²) при больших данных.
  5. Вырожденные кластеры (0 точек) фильтруются из ответа.
"""

import logging
import math

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


# ── Географические утилиты ────────────────────────────────────────────────────

def latlon_to_mercator(lat: float, lon: float) -> tuple[float, float]:
    """
    Конвертирует (lat, lon) в Web Mercator (EPSG:3857), единицы — метры.
    Тот же алгоритм, что использует OpenLayers.
    """
    x = lon * 20037508.34 / 180.0
    lat_rad = max(-1.4835, min(1.4835, math.radians(lat)))
    y = math.log(math.tan(math.pi / 4 + lat_rad / 2)) * 20037508.34 / math.pi
    return x, y


def mercator_to_latlon(x: float, y: float) -> tuple[float, float]:
    """Обратная конвертация из Web Mercator в (lat, lon)."""
    lon = x * 180.0 / 20037508.34
    lat = math.degrees(2 * math.atan(math.exp(y * math.pi / 20037508.34)) - math.pi / 2)
    return lat, lon


# ── Voronoi-тесселяция территории ─────────────────────────────────────────────

def build_voronoi_polygons(
    centroids_xy: np.ndarray,
    all_xy: np.ndarray,
    padding_fraction: float = 0.25,
) -> list[list[list[float]] | None]:
    """
    Строит Voronoi-полигоны для k центроидов, обрезанные по bbox всех точек.

    Алгоритм:
      1. Расширяем bbox на padding_fraction, чтобы граничные зоны выглядели разумно.
      2. Добавляем 4 "зеркальных" точки далеко за пределами bbox — это закрывает
         бесконечные рёбра Voronoi.
      3. Строим Voronoi-диаграмму.
      4. Для каждого исходного центроида извлекаем его регион и обрезаем по bbox.
      5. Конвертируем обратно в (lat, lon).

    Returns:
        Список длиной k. Каждый элемент — список [[lat, lon], ...] или None.
    """
    try:
        from scipy.spatial import Voronoi
        from shapely.geometry import Polygon, box

        k = len(centroids_xy)

        # Bounding box всех точек + паддинг
        min_x = all_xy[:, 0].min()
        max_x = all_xy[:, 0].max()
        min_y = all_xy[:, 1].min()
        max_y = all_xy[:, 1].max()

        dx = max((max_x - min_x) * padding_fraction, 50_000)   # минимум 50 км паддинг
        dy = max((max_y - min_y) * padding_fraction, 50_000)

        clip = box(min_x - dx, min_y - dy, max_x + dx, max_y + dy)

        # Зеркальные точки для закрытия бесконечных рёбер
        far = max(dx, dy) * 8
        cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2
        mirrors = np.array([
            [cx - far, cy - far],
            [cx + far, cy - far],
            [cx + far, cy + far],
            [cx - far, cy + far],
        ])

        pts = np.vstack([centroids_xy, mirrors])
        vor = Voronoi(pts)

        polygons: list[list[list[float]] | None] = []
        for i in range(k):
            region_idx = vor.point_region[i]
            region = vor.regions[region_idx]

            if not region or -1 in region:
                # Бесконечный регион — используем весь bbox
                clipped = clip
            else:
                verts = [vor.vertices[v] for v in region]
                poly = Polygon(verts)
                clipped = poly.intersection(clip)

            if clipped.is_empty:
                polygons.append(None)
                continue

            # Берём внешний контур (игнорируем дыры)
            if clipped.geom_type == "MultiPolygon":
                clipped = max(clipped.geoms, key=lambda g: g.area)

            coords_latlon = []
            for x, y in clipped.exterior.coords:
                lat, lon = mercator_to_latlon(x, y)
                coords_latlon.append([lat, lon])

            polygons.append(coords_latlon if len(coords_latlon) >= 3 else None)

        return polygons

    except Exception as e:
        logger.warning(f"Voronoi failed: {e}")
        return [None] * len(centroids_xy)


# ── Вспомогательные геометрии (fallback) ──────────────────────────────────────

def _bounding_box(coords_latlon: list[list[float]]) -> list[list[float]]:
    arr = np.array(coords_latlon)
    min_lat, min_lon = arr.min(axis=0)
    max_lat, max_lon = arr.max(axis=0)
    pad_lat = max((max_lat - min_lat) * 0.2, 0.05)
    pad_lon = max((max_lon - min_lon) * 0.2, 0.05)
    return [
        [min_lat - pad_lat, min_lon - pad_lon],
        [min_lat - pad_lat, max_lon + pad_lon],
        [max_lat + pad_lat, max_lon + pad_lon],
        [max_lat + pad_lat, min_lon - pad_lon],
    ]


def _point_circle(lat: float, lon: float, radius_deg: float = 0.08) -> list[list[float]]:
    n = 16
    return [
        [lat + radius_deg * math.cos(2 * math.pi * i / n),
         lon + radius_deg * math.sin(2 * math.pi * i / n)]
        for i in range(n)
    ]


# ── Основная функция ──────────────────────────────────────────────────────────

def cluster_points(
    points: list[dict],
    min_k: int = 2,
    max_k: int = 10,
    k: int | str = "auto",
) -> dict:
    """
    Кластеризует переданные точки.

    Args:
        points:  Список словарей с ключами: lat, lon, rub_per_km, bid_count, town
        min_k:   Минимальное число кластеров при auto-режиме
        max_k:   Максимальное число кластеров при auto-режиме
        k:       Конкретное число кластеров (int) или "auto"

    Returns:
        {
          "clusters": [...],
          "k": int,
        }
    """
    if not points:
        return {"clusters": [], "k": 0}

    # ── 1. Фильтрация: только точки с координатами ───────────────────────────
    # Работаем с копиями: кластеризация не должна менять данные вызывающей стороны.
    valid = [dict(p) for p in points if p.get("lat") is not None and p.get("lon") is not None]
    if not valid:
        return {"clusters": [], "k": 0}

    # Слегка "раздвигаем" точки с абсолютно одинаковыми координатами (джиттер).
    # Это спасает KMeans и Voronoi от схлопывания уникальных точек (например,
    # если 50 деревень не были геокодированы и упали в центр региона).
    seen_coords = {}
    jittered_coordinates: list[tuple[float, float]] = []
    for p in valid:
        coord = (p["lat"], p["lon"])
        if coord in seen_coords:
            count = seen_coords[coord]
            seen_coords[coord] += 1
            # Спиральное смещение: шаг около 5 км (0.05 градуса)
            # чтобы они визуально не слипались на мелком масштабе
            radius = 0.05 * math.sqrt(count)
            angle = count * 2.4
            jittered_coordinates.append((
                p["lat"] + radius * math.cos(angle),
                p["lon"] + radius * math.sin(angle),
            ))
        else:
            seen_coords[coord] = 1
            jittered_coordinates.append(coord)

    unique_coords = set(jittered_coordinates)
    n_unique = len(unique_coords)

    if n_unique < 3:
        return _fallback_single_cluster(valid)

    # ── 2. Конвертация в Web Mercator (метры) ────────────────────────────────
    xy_mercator = np.array([latlon_to_mercator(lat, lon) for lat, lon in jittered_coordinates])
    rub_per_km = np.array([
        p.get("cluster_rub_per_km", p.get("rub_per_km", 0)) or 0
        for p in valid
    ])
    bid_counts = np.array([max(float(p.get("bid_count", 0) or 0), 0) for p in valid])
    cluster_weights = np.array([
        max(float(p.get("cluster_weight", bid_counts[i] or 1) or 1), 1)
        for i, p in enumerate(valid)
    ])

    # ── 3. Нормализация признаков ────────────────────────────────────────────
    X_raw = np.column_stack([xy_mercator, rub_per_km])
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    # ── 4. Определение числа кластеров ───────────────────────────────────────
    # Для ручного режима KMeans может сделать до n_unique кластеров
    actual_max_k = min(max_k, n_unique)
    actual_min_k = min(min_k, actual_max_k)

    if actual_max_k < 2:
        return _fallback_single_cluster(valid)

    best_k      = actual_min_k
    best_labels = None
    best_score  = -1.0
    best_km     = None

    if str(k).lower() == "auto":
        silhouette_sample = min(300, len(valid))
        # Для silhouette_score нужно как минимум 2 кластера, и максимум n_unique - 1
        actual_max_k_auto = min(max_k, n_unique - 1)

        if actual_max_k_auto < 2:
            # Невозможно подобрать через силуэт, используем минимум
            best_k = actual_min_k
            best_km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
            best_labels = best_km.fit_predict(X_scaled, sample_weight=cluster_weights)
        else:
            for test_k in range(actual_min_k, actual_max_k_auto + 1):
                km = KMeans(n_clusters=test_k, random_state=42, n_init=10)
                labels = km.fit_predict(X_scaled, sample_weight=cluster_weights)

                try:
                    score = silhouette_score(
                        X_scaled, labels,
                        sample_size=silhouette_sample,
                        random_state=42,
                    )
                    logger.debug(f"k={test_k}: silhouette={score:.4f}")
                    if score > best_score:
                        best_score  = score
                        best_k      = test_k
                        best_labels = labels
                        best_km     = km
                except ValueError as e:
                    logger.debug(f"silhouette_score failed for k={test_k}: {e}")

            if best_labels is None:
                best_k = actual_min_k
                best_km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
                best_labels = best_km.fit_predict(X_scaled, sample_weight=cluster_weights)

    else:
        # Ручной режим: уважаем запрошенное k (ограничиваем сверху actual_max_k)
        best_k = min(int(k), actual_max_k)
        if best_k < 2:
            return _fallback_single_cluster(valid)
        best_km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        best_labels = best_km.fit_predict(X_scaled, sample_weight=cluster_weights)

    # ── 5. Агрегация данных по кластерам ─────────────────────────────────────
    clusters_raw: dict[int, dict] = {
        i: {
            "points": [],
            "total_bids": 0.0,
            "sum_price_weighted": 0.0,
            "sum_lat_weighted": 0.0,
            "sum_lon_weighted": 0.0,
            "center_weight": 0.0,
        }
        for i in range(best_k)
    }

    for i, p in enumerate(valid):
        cid  = int(best_labels[i])
        bids = bid_counts[i]
        center_weight = cluster_weights[i]
        clusters_raw[cid]["points"].append(p)
        clusters_raw[cid]["total_bids"]         += bids
        clusters_raw[cid]["sum_price_weighted"] += (p.get("rub_per_km", 0) or 0) * bids
        clusters_raw[cid]["sum_lat_weighted"]   += p["lat"] * center_weight
        clusters_raw[cid]["sum_lon_weighted"]   += p["lon"] * center_weight
        clusters_raw[cid]["center_weight"]      += center_weight

    # ── 6. Voronoi-полигоны из центроидов KMeans ─────────────────────────────
    # Центроиды в пространстве Mercator (берём из модели KMeans, обратно через scaler)
    centroids_scaled = best_km.cluster_centers_
    # Обратное преобразование scaler только для x_merc, y_merc (первые 2 признака)
    centroids_raw = scaler.inverse_transform(centroids_scaled)
    centroids_xy  = centroids_raw[:, :2]   # x_merc, y_merc

    voronoi_polygons = build_voronoi_polygons(centroids_xy, xy_mercator)

    # ── 7. Формирование ответа ────────────────────────────────────────────────
    result_clusters = []

    for cid in range(best_k):
        cdata = clusters_raw[cid]
        pts   = cdata["points"]

        # Пустые кластеры (KMeans иногда даёт) — пропускаем
        if not pts:
            continue

        total_bids = cdata["total_bids"]
        avg_rub_km = (
            cdata["sum_price_weighted"] / total_bids
            if total_bids > 0 else 0
        )

        # Взвешенный центроид (центр масс по bid_count)
        center_weight = cdata["center_weight"]
        center_lat = cdata["sum_lat_weighted"] / center_weight
        center_lon = cdata["sum_lon_weighted"] / center_weight

        # Voronoi-полигон; если не построился — fallback на bbox точек кластера
        polygon = voronoi_polygons[cid]
        if polygon is None:
            coords_latlon = [[p["lat"], p["lon"]] for p in pts]
            polygon = (
                _bounding_box(coords_latlon)
                if len({(c[0], c[1]) for c in coords_latlon}) > 1
                else _point_circle(coords_latlon[0][0], coords_latlon[0][1])
            )

        result_clusters.append({
            "id":           cid,
            "points":       pts,
            "avg_rub_km":   round(avg_rub_km, 1),
            "total_bids":   int(total_bids),
            "points_count": len(pts),
            "polygon":      polygon,
            "center":       [center_lat, center_lon],
        })

    logger.info(
        f"Результат: k={best_k}, непустых={len(result_clusters)}, "
        f"silhouette={best_score:.3f}"
    )

    return {"clusters": result_clusters, "k": best_k}


# ── Fallback ──────────────────────────────────────────────────────────────────

def _fallback_single_cluster(points: list[dict]) -> dict:
    """Один кластер на все точки (n_unique < 3)."""
    if not points:
        return {"clusters": [], "k": 0}

    total_bids = 0.0
    sum_price = 0.0
    sum_lat = 0.0
    sum_lon = 0.0
    center_weight_total = 0.0
    coords_latlon = []

    for p in points:
        bids = max(float(p.get("bid_count", 0) or 0), 0)
        center_weight = max(float(p.get("cluster_weight", bids or 1) or 1), 1)
        total_bids += bids
        sum_price  += (p.get("rub_per_km", 0) or 0) * bids
        sum_lat    += p["lat"] * center_weight
        sum_lon    += p["lon"] * center_weight
        center_weight_total += center_weight
        coords_latlon.append([p["lat"], p["lon"]])

    avg_rub_km = sum_price / total_bids if total_bids > 0 else 0
    center_lat = sum_lat / center_weight_total
    center_lon = sum_lon / center_weight_total

    unique = {(c[0], c[1]) for c in coords_latlon}
    polygon = (
        _bounding_box(coords_latlon)
        if len(unique) > 1
        else _point_circle(coords_latlon[0][0], coords_latlon[0][1])
    )

    return {
        "clusters": [{
            "id":           0,
            "points":       points,
            "avg_rub_km":   round(avg_rub_km, 1),
            "total_bids":   int(total_bids),
            "points_count": len(points),
            "polygon":      polygon,
            "center":       [center_lat, center_lon],
        }],
        "k": 1,
    }
