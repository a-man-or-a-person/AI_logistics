import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from scipy.spatial import ConvexHull

def cluster_points(points: list[dict], min_k: int = 2, max_k: int = 10, k: int | str = "auto") -> dict:
    """
    Кластеризует переданные точки.
    points: список словарей, каждый должен содержать lat, lon, rub_per_km, bid_count
    Возвращает структуру с данными по кластерам и их центроидам/полигонам.
    """
    if not points:
        return {"clusters": [], "k": 0}

    # Оставляем только те точки, у которых есть координаты
    valid_points = [p for p in points if p.get("lat") is not None and p.get("lon") is not None]
    if not valid_points:
        return {"clusters": [], "k": 0}

    # Если уникальных точек (по координатам) меньше, чем min_k, уменьшаем min_k/max_k
    unique_coords = {(p["lat"], p["lon"]) for p in valid_points}
    if len(unique_coords) < 3:
        # Недостаточно точек для кластеризации и полигонов
        return _fallback_single_cluster(valid_points)

    actual_max_k = min(max_k, len(unique_coords) - 1)
    actual_min_k = min(min_k, actual_max_k)
    
    if actual_max_k < 2:
         return _fallback_single_cluster(valid_points)

    # Подготовка данных
    # Фичи: lat, lon, rub_per_km
    X_raw = []
    weights = []
    for p in valid_points:
        X_raw.append([p["lat"], p["lon"], p.get("rub_per_km", 0)])
        weights.append(p.get("bid_count", 1) or 1)
        
    X_raw = np.array(X_raw)
    weights = np.array(weights)
    
    # Нормализация
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)
    
    # Увеличим вес координат, чтобы кластеры были более географически компактными
    # Индексы: 0=lat, 1=lon, 2=rub_per_km
    X_scaled[:, 0] *= 2.0
    X_scaled[:, 1] *= 2.0

    best_k = 2
    best_labels = None
    best_kmeans = None

    if str(k).lower() == "auto":
        best_score = -1
        # Перебор K
        for test_k in range(actual_min_k, actual_max_k + 1):
            kmeans = KMeans(n_clusters=test_k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X_scaled, sample_weight=weights)
            
            # Считаем силуэт (без учета весов для стабильности метрики)
            try:
                score = silhouette_score(X_scaled, labels)
                if score > best_score:
                    best_score = score
                    best_k = test_k
                    best_labels = labels
                    best_kmeans = kmeans
            except ValueError:
                pass
                
        if best_labels is None:
             # Fallback если силуэт не посчитался
             best_k = actual_min_k
             best_kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
             best_labels = best_kmeans.fit_predict(X_scaled, sample_weight=weights)
    else:
        best_k = min(int(k), actual_max_k)
        if best_k < 2:
            return _fallback_single_cluster(valid_points)
        best_kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        best_labels = best_kmeans.fit_predict(X_scaled, sample_weight=weights)

    # Формирование ответа
    clusters_data = {}
    for i in range(best_k):
        clusters_data[i] = {
            "points": [],
            "total_bids": 0,
            "sum_price_weighted": 0.0,
        }
        
    for i, p in enumerate(valid_points):
        c_id = best_labels[i]
        clusters_data[c_id]["points"].append(p)
        bids = p.get("bid_count", 1) or 1
        clusters_data[c_id]["total_bids"] += bids
        
        clusters_data[c_id]["sum_price_weighted"] += p.get("rub_per_km", 0) * bids

    result_clusters = []
    for c_id, c_data in clusters_data.items():
        if not c_data["points"]:
            continue
            
        pts = c_data["points"]
        total_bids = c_data["total_bids"]
        avg_rub_km = c_data["sum_price_weighted"] / total_bids if total_bids > 0 else 0
        
        # Считаем полигон (ConvexHull)
        coords = np.array([[p["lat"], p["lon"]] for p in pts])
        hull_polygon = []
        
        unique_coords_in_cluster = len(set((c[0], c[1]) for c in coords))
        
        if unique_coords_in_cluster >= 3:
            # Чтобы не падало если все точки на одной прямой
            try:
                hull = ConvexHull(coords)
                # hull.vertices содержит индексы точек, образующих границу в порядке обхода
                hull_polygon = [[coords[v][0], coords[v][1]] for v in hull.vertices]
            except Exception:
                hull_polygon = _make_bounding_box(coords)
        elif unique_coords_in_cluster == 2:
            hull_polygon = _make_bounding_box(coords)
        else:
            # 1 точка
            p_coord = coords[0]
            hull_polygon = [
                [p_coord[0]-0.05, p_coord[1]-0.05], [p_coord[0]-0.05, p_coord[1]+0.05], 
                [p_coord[0]+0.05, p_coord[1]+0.05], [p_coord[0]+0.05, p_coord[1]-0.05]
            ]

        # Вычисляем центроид полигона для размещения таблички с ценой
        center_lat = sum(p[0] for p in coords) / len(coords)
        center_lon = sum(p[1] for p in coords) / len(coords)

        result_clusters.append({
            "id": int(c_id),
            "points": pts,
            "avg_rub_km": round(avg_rub_km, 1),
            "total_bids": int(total_bids),
            "points_count": len(pts),
            "polygon": hull_polygon,
            "center": [center_lat, center_lon]
        })
        
    return {"clusters": result_clusters, "k": best_k}


def _make_bounding_box(coords):
    """Делает прямоугольник из списка точек (например, если их 2)"""
    min_lat = min(c[0] for c in coords)
    max_lat = max(c[0] for c in coords)
    min_lon = min(c[1] for c in coords)
    max_lon = max(c[1] for c in coords)
    
    # Добавляем небольшой padding
    pad_lat = max((max_lat - min_lat) * 0.2, 0.05)
    pad_lon = max((max_lon - min_lon) * 0.2, 0.05)
    
    return [
        [min_lat - pad_lat, min_lon - pad_lon],
        [min_lat - pad_lat, max_lon + pad_lon],
        [max_lat + pad_lat, max_lon + pad_lon],
        [max_lat + pad_lat, min_lon - pad_lon]
    ]

def _fallback_single_cluster(points):
    if not points:
        return {"clusters": [], "k": 0}
        
    total_bids = 0
    sum_price = 0
    coords = []
    for p in points:
        bids = p.get("bid_count", 1) or 1
        total_bids += bids
        sum_price += p.get("rub_per_km", 0) * bids
        coords.append([p["lat"], p["lon"]])
        
    avg_rub_km = sum_price / total_bids if total_bids > 0 else 0
    center_lat = sum(p[0] for p in coords) / len(coords)
    center_lon = sum(p[1] for p in coords) / len(coords)
    
    polygon = _make_bounding_box(coords) if len(set((c[0], c[1]) for c in coords)) > 1 else [
        [center_lat-0.05, center_lon-0.05], [center_lat-0.05, center_lon+0.05], 
        [center_lat+0.05, center_lon+0.05], [center_lat+0.05, center_lon-0.05]
    ]
    
    return {
        "clusters": [{
            "id": 0,
            "points": points,
            "avg_rub_km": round(avg_rub_km, 1),
            "total_bids": total_bids,
            "points_count": len(points),
            "polygon": polygon,
            "center": [center_lat, center_lon]
        }],
        "k": 1
    }
