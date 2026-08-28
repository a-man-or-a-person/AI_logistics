"""Flask Blueprint for Clustering Product v1."""

from __future__ import annotations

import logging
import threading
from typing import Any

from flask import Blueprint, jsonify, request

from ml.clustering.service import (
    ClusteringRequest,
    ProductClusteringError,
    ProductClusteringService,
)

logger = logging.getLogger(__name__)
clustering_blueprint = Blueprint("clustering_product", __name__, url_prefix="/api/clustering")

_service: ProductClusteringService | None = None
_service_lock = threading.Lock()


def get_clustering_service() -> ProductClusteringService:
    global _service
    with _service_lock:
        if _service is None:
            _service = ProductClusteringService()
        return _service


def set_clustering_service(service: ProductClusteringService | None) -> None:
    """Inject or reset the lazy service in tests and controlled deployments."""
    global _service
    with _service_lock:
        _service = service


def _error(error: ProductClusteringError):
    return jsonify({"ok": False, "code": error.code, "error": str(error)}), error.status


@clustering_blueprint.get("/options")
def clustering_options():
    try:
        origin_fias = request.args.get("origin_fias") or None
        destination_region = request.args.get("destination_region") or None
        if destination_region and not origin_fias:
            raise ProductClusteringError(
                "INVALID_REQUEST",
                "destination_region требует origin_fias.",
                400,
            )
        result = get_clustering_service().options(origin_fias, destination_region)
        return jsonify({"ok": True, **result})
    except ProductClusteringError as error:
        return _error(error)
    except Exception:
        logger.exception("Ошибка в /api/clustering/options")
        return jsonify(
            {"ok": False, "code": "INTERNAL_ERROR", "error": "Внутренняя ошибка сервера"}
        ), 500


def _json_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ProductClusteringError("INVALID_REQUEST", "Ожидается JSON-объект.", 400)
    return payload


@clustering_blueprint.post("/run")
def run_clustering():
    try:
        product_request = ClusteringRequest.from_payload(_json_payload())
        result = get_clustering_service().run(product_request)
        return jsonify({"ok": True, **result})
    except ProductClusteringError as error:
        return _error(error)
    except Exception:
        logger.exception("Ошибка в /api/clustering/run")
        return jsonify(
            {"ok": False, "code": "INTERNAL_ERROR", "error": "Внутренняя ошибка сервера"}
        ), 500


@clustering_blueprint.post("/compare")
def compare_clustering():
    try:
        payload = _json_payload()
        payload.setdefault("mode", "geography")
        payload["parameters"] = {}
        product_request = ClusteringRequest.from_payload(payload)
        result = get_clustering_service().compare(product_request)
        return jsonify({"ok": True, **result})
    except ProductClusteringError as error:
        return _error(error)
    except Exception:
        logger.exception("Ошибка в /api/clustering/compare")
        return jsonify(
            {"ok": False, "code": "INTERNAL_ERROR", "error": "Внутренняя ошибка сервера"}
        ), 500
