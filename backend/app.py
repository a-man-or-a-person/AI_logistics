"""Flask API server for the logistics data map and territorial analysis."""

from __future__ import annotations

import logging
import os
import threading

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from backend.clustering_api import clustering_blueprint
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


@app.get("/api/ml-cluster")
def api_ml_cluster():
    """Compatibility endpoint retained for legacy clients; Product v1 never calls it."""
    try:
        region = request.args.get("region", "").strip()
        town_type = request.args.get("town_type", "").strip()
        raw_k = request.args.get("k", "auto")
        period_types = _parse_csv_arg("period_types")
        price_types = _parse_csv_arg("price_types")
        if not region or town_type not in {"shipment", "delivery"}:
            return jsonify(
                {"ok": False, "error": "town_type должен быть shipment или delivery"}
            ), 400
        validation_error = _filter_validation_error(period_types, price_types)
        if validation_error:
            return jsonify({"ok": False, "error": validation_error}), 400
        try:
            requested_k = 5 if raw_k == "auto" else int(raw_k)
        except ValueError:
            return jsonify({"ok": False, "error": "k должен быть auto или целым числом"}), 400
        if not 2 <= requested_k <= 10:
            return jsonify({"ok": False, "error": "k должен быть от 2 до 10"}), 400

        data = load_data()
        towns = data["shipment_towns" if town_type == "shipment" else "delivery_towns"]
        rows = []
        for town in towns.values():
            if town["region"] != region:
                continue
            records = [
                record for record in town["records"]
                if (not period_types or record["period_type"] in period_types)
                and (not price_types or record["price_type"] in price_types)
            ]
            coordinates = geocode_town(town["town"], region, offline_only=True)
            if not coordinates:
                continue
            rows.append(
                {
                    "town": town["town"], "lat": coordinates[0], "lon": coordinates[1],
                    "rub_per_km": round(calculate_rub_per_km(records), 2),
                    "bid_count": sum(record["bid_count"] for record in records),
                }
            )
        if len(rows) < 2:
            return jsonify({"ok": False, "error": "Недостаточно точек"}), 422
        from ml.clustering.base import ClusterPoint
        from ml.clustering.kmeans import KMeansClusterer
        from ml.spatial.projection import LocalProjection

        projection = LocalProjection.from_coordinates([(row["lat"], row["lon"]) for row in rows])
        points = []
        for index, row in enumerate(rows):
            x, y = projection.project(row["lat"], row["lon"])
            points.append(ClusterPoint(str(index), row["town"], region, x, y, row["bid_count"]))
        selected_k = min(requested_k, len(points))
        result = KMeansClusterer().fit(points, {"n_clusters": selected_k, "weight_mode": "none", "random_state": 42})
        assignments = result.point_assignments
        return jsonify(
            {
                "ok": True, "algorithm": "kmeans", "k": selected_k,
                "points": [{**row, "cluster_id": assignments[str(index)]} for index, row in enumerate(rows)],
                "clusters": [
                    {"cluster_id": cluster.cluster_id, "point_count": cluster.point_count, "trip_count": cluster.trip_count}
                    for cluster in result.clusters
                ],
            }
        )
    except Exception:
        logger.exception("Ошибка в /api/ml-cluster")
        return _internal_error()


if __name__ == "__main__":
    app.run(
        debug=os.environ.get("LOGISTICS_DEBUG") == "1",
        port=int(os.environ.get("LOGISTICS_PORT", "5000")),
        host=os.environ.get("LOGISTICS_HOST", "127.0.0.1"),
    )
