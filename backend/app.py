"""Flask API server for the logistics data map and territorial analysis."""

from __future__ import annotations

import logging
import os
import threading

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from backend.clustering_api import clustering_blueprint
from backend.data_processor import (
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/static")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("LOGISTICS_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if CORS_ORIGINS:
    CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}})
app.register_blueprint(clustering_blueprint)

_bg_geocode_started = False
_bg_geocode_start_lock = threading.Lock()

ALLOWED_PERIOD_TYPES = {"retro", "current", "forecast"}
ALLOWED_PRICE_TYPES = {"spot", "tender"}


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


def _start_background_geocoding() -> None:
    """Start the legacy Data Map geocoder once; clustering never calls it."""
    global _bg_geocode_started
    with _bg_geocode_start_lock:
        if _bg_geocode_started:
            return
        _bg_geocode_started = True

    data = load_data()
    all_towns = {
        (value["town"], value["region"])
        for group in (data["shipment_towns"], data["delivery_towns"])
        for value in group.values()
    }
    thread = threading.Thread(
        target=geocode_all_towns_background,
        args=(list(all_towns),),
        daemon=True,
    )
    thread.start()


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/css/<path:filename>")
def css_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), filename)


@app.get("/js/<path:filename>")
def js_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), filename)


@app.get("/api/regions")
def api_regions():
    try:
        return jsonify({"ok": True, **get_regions()})
    except Exception:
        logger.exception("Ошибка в /api/regions")
        return _internal_error()


@app.get("/api/stats")
def api_stats():
    try:
        return jsonify({"ok": True, **get_stats()})
    except Exception:
        logger.exception("Ошибка в /api/stats")
        return _internal_error()


@app.get("/api/points")
def api_points():
    """Return legacy Data Map points without changing its public contract."""
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
        all_towns = {
            (point["town"], point["region"])
            for point in result["shipment_points"] + result["delivery_points"]
        }
        coordinates = geocode_batch(list(all_towns), offline_only=True)
        _start_background_geocoding()

        shipment_points = [
            {**point, "lat": coords[0], "lon": coords[1]}
            for point in result["shipment_points"]
            if (coords := coordinates.get(f"{point['town']}::{point['region']}"))
        ]
        delivery_points = [
            {**point, "lat": coords[0], "lon": coords[1]}
            for point in result["delivery_points"]
            if (coords := coordinates.get(f"{point['town']}::{point['region']}"))
        ]
        return jsonify(
            {
                "ok": True,
                "shipment_points": shipment_points,
                "delivery_points": delivery_points,
                "total_ship": len(shipment_points),
                "total_del": len(delivery_points),
                "geocoded": sum(value is not None for value in coordinates.values()),
                "towns_total": len(all_towns),
            }
        )
    except Exception:
        logger.exception("Ошибка в /api/points")
        return _internal_error()


@app.get("/api/records")
def get_records():
    try:
        town = request.args.get("town", "")
        region = request.args.get("region", "")
        town_type = request.args.get("type", "")
        from_regions = _parse_csv_arg("from_regions")
        to_regions = _parse_csv_arg("to_regions")
        period_types = _parse_csv_arg("period_types")
        price_types = _parse_csv_arg("price_types")

        if not town or not region or town_type not in {"shipment", "delivery"}:
            return jsonify({"ok": False, "error": "Неверные town, region или type"}), 400
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
        return jsonify({"ok": True, "count": len(records), "records": records})
    except Exception:
        logger.exception("Ошибка в /api/records")
        return _internal_error()


@app.post("/api/regeocode")
def api_regeocode():
    """Legacy Data Map diagnostic; absent from the clustering workflow."""
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
            return jsonify({"ok": False, "error": "Слишком длинное название"}), 400
        coordinates = geocode_town(town, region, offline_only=False, force_recalc=True)
        if not coordinates:
            return jsonify({"ok": False, "error": "Координаты не найдены"}), 404
        return jsonify({"ok": True, "lat": coordinates[0], "lon": coordinates[1]})
    except Exception:
        logger.exception("Ошибка в /api/regeocode")
        return _internal_error()


@app.get("/api/geocode-status")
def api_geocode_status():
    try:
        return jsonify({"ok": True, **get_geocode_status()})
    except Exception:
        logger.exception("Ошибка в /api/geocode-status")
        return _internal_error()


if __name__ == "__main__":
    app.run(
        debug=os.environ.get("LOGISTICS_DEBUG") == "1",
        port=int(os.environ.get("LOGISTICS_PORT", "5000")),
        host=os.environ.get("LOGISTICS_HOST", "127.0.0.1"),
    )
