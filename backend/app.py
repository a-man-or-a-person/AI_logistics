"""
Flask API сервер для карты логистики.

Эндпоинты:
  GET /                          → frontend/index.html
  GET /api/regions               → списки регионов
  GET /api/stats                 → общая статистика
  GET /api/points                → точки на карту (с фильтрами)
  GET /api/geocode               → геокодирование списка городов
  GET /api/geocode-status        → статус фонового геокодирования
"""

import logging
import os
import sys
import threading

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Добавляем директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.data_processor import (
    calculate_rub_per_km,
    get_map_points,
    get_raw_records,
    get_regions,
    get_stats,
    load_data,
)
from backend.geocoder import (
    geocode_all_towns_background,
    geocode_batch,
    geocode_town,
    get_geocode_status,
)

# ─── Настройка логирования ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Flask приложение ─────────────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,
    static_url_path="/static",
)
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("LOGISTICS_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if CORS_ORIGINS:
    CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}})

_bg_geocode_started = False
_bg_geocode_start_lock = threading.Lock()

ALLOWED_PERIOD_TYPES = {"retro", "current", "forecast"}
ALLOWED_PRICE_TYPES = {"spot", "tender"}
ALLOWED_TOWN_TYPES = {"shipment", "delivery"}


def _parse_csv_arg(name: str) -> list[str]:
    return [value.strip() for value in request.args.get(name, "").split(",") if value.strip()]


def _filter_validation_error(period_types: list[str], price_types: list[str]) -> str | None:
    invalid_periods = sorted(set(period_types) - ALLOWED_PERIOD_TYPES)
    if invalid_periods:
        return f"Неизвестные period_types: {', '.join(invalid_periods)}"
    invalid_prices = sorted(set(price_types) - ALLOWED_PRICE_TYPES)
    if invalid_prices:
        return f"Неизвестные price_types: {', '.join(invalid_prices)}"
    return None


def _internal_error():
    return jsonify({"ok": False, "error": "Внутренняя ошибка сервера"}), 500


def _start_background_geocoding():
    """Запускает фоновое геокодирование всех городов при первом запросе."""
    global _bg_geocode_started
    with _bg_geocode_start_lock:
        if _bg_geocode_started:
            return
        _bg_geocode_started = True

    data = load_data()
    all_towns = set()
    for v in data["shipment_towns"].values():
        all_towns.add((v["town"], v["region"]))
    for v in data["delivery_towns"].values():
        all_towns.add((v["town"], v["region"]))

    logger.info(f"🌍 Запускаем фоновое геокодирование {len(all_towns)} городов...")
    thread = threading.Thread(
        target=geocode_all_towns_background,
        args=(list(all_towns),),
        daemon=True,
    )
    thread.start()


# ─── Главная страница ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/css/<path:filename>")
def css_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), filename)


@app.route("/js/<path:filename>")
def js_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), filename)


# ─── API эндпоинты ────────────────────────────────────────────────────────────

@app.route("/api/regions")
def api_regions():
    """Возвращает списки регионов отгрузки и доставки."""
    try:
        regions = get_regions()
        return jsonify({"ok": True, **regions})
    except Exception:
        logger.exception("Ошибка в /api/regions")
        return _internal_error()


@app.route("/api/stats")
def api_stats():
    """Возвращает общую статистику по данным."""
    try:
        stats = get_stats()
        return jsonify({"ok": True, **stats})
    except Exception:
        logger.exception("Ошибка в /api/stats")
        return _internal_error()


@app.route("/api/points")
def api_points():
    """
    Возвращает точки для карты.

    Query params:
      from_regions  — через запятую (напр.: "Московская область,Самарская область")
      to_regions    — через запятую
      period_types  — через запятую: retro,current,forecast
      price_types   — через запятую: spot,tender
    """
    try:
        from_regions = _parse_csv_arg("from_regions")
        to_regions = _parse_csv_arg("to_regions")
        period_types = _parse_csv_arg("period_types")
        price_types = _parse_csv_arg("price_types")
        validation_error = _filter_validation_error(period_types, price_types)
        if validation_error:
            return jsonify({"ok": False, "error": validation_error}), 400

        result = get_map_points(
            from_regions=from_regions or None,
            to_regions=to_regions or None,
            period_types=period_types or None,
            price_types=price_types or None,
        )

        # Геокодируем города в полученных точках
        all_towns = set()
        for pt in result["shipment_points"]:
            all_towns.add((pt["town"], pt["region"]))
        for pt in result["delivery_points"]:
            all_towns.add((pt["town"], pt["region"]))

        logger.info(f"Геокодируем {len(all_towns)} городов...")
        coords_map = geocode_batch(list(all_towns), offline_only=True)

        # Запускаем фоновое геокодирование если ещё не запущено
        _start_background_geocoding()

        # Добавляем координаты к точкам
        ship_with_coords = []
        for pt in result["shipment_points"]:
            coords = coords_map.get(f"{pt['town']}::{pt['region']}")
            if coords:
                ship_with_coords.append({**pt, "lat": coords[0], "lon": coords[1]})

        del_with_coords = []
        for pt in result["delivery_points"]:
            coords = coords_map.get(f"{pt['town']}::{pt['region']}")
            if coords:
                del_with_coords.append({**pt, "lat": coords[0], "lon": coords[1]})

        geocoded_count = sum(1 for c in coords_map.values() if c is not None)
        logger.info(
            f"Точки с координатами: отгрузка={len(ship_with_coords)}/{result['total_ship']}, "
            f"доставка={len(del_with_coords)}/{result['total_del']}, "
            f"геокодировано {geocoded_count}/{len(all_towns)}"
        )

        return jsonify({
            "ok": True,
            "shipment_points": ship_with_coords,
            "delivery_points": del_with_coords,
            "total_ship": len(ship_with_coords),
            "total_del": len(del_with_coords),
            "geocoded": geocoded_count,
            "towns_total": len(all_towns),
        })

    except Exception:
        logger.exception("Ошибка в /api/points")
        return _internal_error()


@app.route("/api/records", methods=["GET"])
def get_records():
    """Возвращает список сырых записей для конкретного города."""
    try:
        town = request.args.get("town", "")
        region = request.args.get("region", "")
        town_type = request.args.get("type", "")
        from_regions = _parse_csv_arg("from_regions")
        to_regions = _parse_csv_arg("to_regions")
        period_types = _parse_csv_arg("period_types")
        price_types = _parse_csv_arg("price_types")

        if not town or not region or town_type not in ["shipment", "delivery"]:
            return jsonify({"ok": False, "error": "Неверные параметры town, region или type"}), 400
        validation_error = _filter_validation_error(period_types, price_types)
        if validation_error:
            return jsonify({"ok": False, "error": validation_error}), 400

        records = get_raw_records(
            town=town,
            region=region,
            town_type=town_type,
            from_regions=from_regions or None,
            to_regions=to_regions or None,
            period_types=period_types or None,
            price_types=price_types or None,
        )

        return jsonify({
            "ok": True,
            "count": len(records),
            "records": records,
        })
    except Exception:
        logger.exception("Ошибка в /api/records")
        return _internal_error()


@app.route("/api/regeocode", methods=["POST"])
def api_regeocode():
    """Принудительно пересчитывает координаты города."""
    try:
        data = request.get_json(silent=True) or {}
        town = data.get("town", "")
        region = data.get("region", "")

        if not isinstance(town, str) or not isinstance(region, str):
            return jsonify({"ok": False, "error": "town и region должны быть строками"}), 400
        town = town.strip()
        region = region.strip()
        if not town:
            return jsonify({"ok": False, "error": "Не указан town"}), 400
        if len(town) > 200 or len(region) > 200:
            return jsonify({"ok": False, "error": "Слишком длинное название города или региона"}), 400

        coords = geocode_town(town, region, offline_only=False, force_recalc=True)
        if coords:
            return jsonify({"ok": True, "lat": coords[0], "lon": coords[1]})
        else:
            return jsonify({"ok": False, "error": "Не удалось определить координаты"}), 404
    except Exception:
        logger.exception("Ошибка в /api/regeocode")
        return _internal_error()


@app.route("/api/geocode-status")
def api_geocode_status():
    """Возвращает статус фонового геокодирования."""
    try:
        status = get_geocode_status()
        return jsonify({"ok": True, **status})
    except Exception:
        logger.exception("Ошибка в /api/geocode-status")
        return _internal_error()


@app.route("/api/ml-cluster")
def api_ml_cluster():
    """
    ML Кластеризация для конкретного региона.
    Query params:
      region
      town_type (shipment/delivery)
      k (число кластеров или "auto")
      period_types, price_types

    Включает ВСЕ геокодированные города региона, а не только те,
    у которых есть ценовые данные по текущему фильтру.
    """
    try:
        region = request.args.get("region", "")
        town_type = request.args.get("town_type", "")
        k_val = request.args.get("k", "auto")
        period_types = _parse_csv_arg("period_types")
        price_types = _parse_csv_arg("price_types")

        if not region or town_type not in ALLOWED_TOWN_TYPES:
            return jsonify({"ok": False, "error": "town_type должен быть shipment или delivery"}), 400
        validation_error = _filter_validation_error(period_types, price_types)
        if validation_error:
            return jsonify({"ok": False, "error": validation_error}), 400
        if str(k_val).lower() != "auto":
            try:
                parsed_k = int(k_val)
            except (TypeError, ValueError):
                return jsonify({"ok": False, "error": "k должен быть auto или целым числом"}), 400
            if not 2 <= parsed_k <= 10:
                return jsonify({"ok": False, "error": "k должен быть от 2 до 10"}), 400
            k_val = parsed_k

        from backend.ml_clustering import cluster_points
        data = load_data()
        towns_dict = data["shipment_towns"] if town_type == "shipment" else data["delivery_towns"]

        points_to_cluster = []
        region_total_bids = 0

        for town_data in towns_dict.values():
            if town_data["region"] != region:
                continue

            records = town_data["records"]

            # Сначала пробуем данные по текущему фильтру
            filtered = [
                r for r in records
                if (not period_types or r["period_type"] in period_types)
                and (not price_types or r["price_type"] in price_types)
            ]

            rub_per_km = calculate_rub_per_km(filtered)
            bids = sum(r["bid_count"] for r in filtered)
            region_total_bids += bids
            has_data = rub_per_km > 0
            cluster_rub_per_km = rub_per_km

            # Итог региона включает все записи, даже если город нельзя показать.
            coords = geocode_town(town_data["town"], region, offline_only=True)
            if not coords:
                continue

            if not has_data:
                # Город остаётся на карте, но данные других периодов используются
                # только как нейтральный ML-признак, а не как фактические заявки.
                cluster_rub_per_km = calculate_rub_per_km(records)

            points_to_cluster.append({
                "town":       town_data["town"],
                "lat":        coords[0],
                "lon":        coords[1],
                "rub_per_km": round(rub_per_km, 2),
                "cluster_rub_per_km": round(cluster_rub_per_km, 2),
                "bid_count":  bids,
                "cluster_weight": max(bids, 1),
                "has_data":   has_data,
            })

        logger.info(
            f"ML: регион={region}, тип={town_type}, точек={len(points_to_cluster)}, k={k_val}"
        )

        result = cluster_points(points_to_cluster, min_k=2, max_k=10, k=k_val)
        return jsonify({"ok": True, "region_total_bids": region_total_bids, **result})
    except Exception:
        logger.exception("Ошибка в /api/ml-cluster")
        return _internal_error()


# ─── Запуск ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(
        debug=os.environ.get("LOGISTICS_DEBUG") == "1",
        port=int(os.environ.get("LOGISTICS_PORT", "5000")),
        host=os.environ.get("LOGISTICS_HOST", "127.0.0.1"),
    )
