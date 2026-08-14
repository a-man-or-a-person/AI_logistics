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

import os
import sys
import logging
import threading

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Добавляем директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.data_processor import get_map_points, get_regions, get_stats, load_data, get_raw_records
from backend.geocoder import geocode_batch, geocode_all_towns_background, get_geocode_status, geocode_town

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
CORS(app)  # Разрешаем CORS для разработки

_bg_geocode_started = False


def _start_background_geocoding():
    """Запускает фоновое геокодирование всех городов при первом запросе."""
    global _bg_geocode_started
    if _bg_geocode_started:
        return
    _bg_geocode_started = True

    data = load_data()
    all_towns = set()
    for k, v in data["shipment_towns"].items():
        all_towns.add((v["town"], v["region"]))
    for k, v in data["delivery_towns"].items():
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
    except Exception as e:
        logger.exception("Ошибка в /api/regions")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/stats")
def api_stats():
    """Возвращает общую статистику по данным."""
    try:
        stats = get_stats()
        return jsonify({"ok": True, **stats})
    except Exception as e:
        logger.exception("Ошибка в /api/stats")
        return jsonify({"ok": False, "error": str(e)}), 500


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
        from_regions_str  = request.args.get("from_regions", "")
        to_regions_str    = request.args.get("to_regions", "")
        period_types_str  = request.args.get("period_types", "")
        price_types_str   = request.args.get("price_types", "")

        from_regions = [r.strip() for r in from_regions_str.split(",") if r.strip()]
        to_regions   = [r.strip() for r in to_regions_str.split(",") if r.strip()]
        period_types = [p.strip() for p in period_types_str.split(",") if p.strip()]
        price_types  = [p.strip() for p in price_types_str.split(",") if p.strip()]

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

    except Exception as e:
        logger.exception("Ошибка в /api/points")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/records", methods=["GET"])
def get_records():
    """Возвращает список сырых записей для конкретного города."""
    try:
        town = request.args.get("town", "")
        region = request.args.get("region", "")
        town_type = request.args.get("type", "")
        from_regions_str  = request.args.get("from_regions", "")
        to_regions_str    = request.args.get("to_regions", "")
        period_types_str  = request.args.get("period_types", "")
        price_types_str   = request.args.get("price_types", "")

        from_regions = [r.strip() for r in from_regions_str.split(",") if r.strip()]
        to_regions   = [r.strip() for r in to_regions_str.split(",") if r.strip()]
        period_types = [p.strip() for p in period_types_str.split(",") if p.strip()]
        price_types  = [p.strip() for p in price_types_str.split(",") if p.strip()]

        if not town or not region or town_type not in ["shipment", "delivery"]:
            return jsonify({"ok": False, "error": "Неверные параметры town, region или type"}), 400

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
    except Exception as e:
        logger.exception("Ошибка в /api/records")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/regeocode", methods=["POST"])
def api_regeocode():
    """Принудительно пересчитывает координаты города."""
    try:
        data = request.json or {}
        town = data.get("town", "")
        region = data.get("region", "")
        
        if not town:
            return jsonify({"ok": False, "error": "Не указан town"}), 400

        coords = geocode_town(town, region, offline_only=False, force_recalc=True)
        if coords:
            return jsonify({"ok": True, "lat": coords[0], "lon": coords[1]})
        else:
            return jsonify({"ok": False, "error": "Не удалось определить координаты"}), 404
    except Exception as e:
        logger.exception("Ошибка в /api/regeocode")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/geocode-status")
def api_geocode_status():
    """Возвращает статус фонового геокодирования."""
    try:
        status = get_geocode_status()
        return jsonify({"ok": True, **status})
    except Exception as e:
        logger.exception("Ошибка в /api/geocode-status")
        return jsonify({"ok": False, "error": str(e)}), 500


# ─── Запуск ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
