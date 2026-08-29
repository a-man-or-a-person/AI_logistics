"""Thin Flask handlers for the canonical clustering API."""

from __future__ import annotations

import logging
import threading
from typing import Any

from flask import Blueprint, jsonify, request

from backend.services.clustering_service import (
    ClusteringRequest,
    ClusteringService,
    ProductClusteringError,
)

logger = logging.getLogger(__name__)
clustering_blueprint = Blueprint("clustering_product", __name__, url_prefix="/api/clustering")

_service: ClusteringService | None = None
_service_lock = threading.Lock()


def get_clustering_service() -> ClusteringService:
    global _service
    with _service_lock:
        if _service is None:
            _service = ClusteringService()
        return _service


def set_clustering_service(service: ClusteringService | None) -> None:
    """Inject or reset the lazy service in tests and controlled deployments."""
    global _service
    with _service_lock:
        _service = service


def _error(error: ProductClusteringError):
    return jsonify({"ok": False, "code": error.code, "error": str(error)}), error.status


def _internal_error(endpoint: str):
    logger.exception("Ошибка в %s", endpoint)
    return jsonify(
        {"ok": False, "code": "INTERNAL_ERROR", "error": "Внутренняя ошибка сервера"}
    ), 500


def _json_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ProductClusteringError("INVALID_REQUEST", "Ожидается JSON-объект.", 400)
    return payload


@clustering_blueprint.get("/options")
def clustering_options():
    try:
        origin_fias = request.args.get("origin_fias") or None
        return jsonify({"ok": True, **get_clustering_service().options(origin_fias)})
    except ProductClusteringError as error:
        return _error(error)
    except Exception:
        return _internal_error("/api/clustering/options")


@clustering_blueprint.get("/origins")
def clustering_origins():
    try:
        query = request.args.get("q", "").strip()
        raw_limit = request.args.get("limit", "20")
        try:
            limit = int(raw_limit)
        except ValueError as error:
            raise ProductClusteringError(
                "INVALID_REQUEST", "limit должен быть целым числом.", 400
            ) from error
        if not 1 <= limit <= 100:
            raise ProductClusteringError(
                "INVALID_REQUEST", "limit должен быть от 1 до 100.", 400
            )
        return jsonify(get_clustering_service().origins(query, limit))
    except ProductClusteringError as error:
        return _error(error)
    except Exception:
        return _internal_error("/api/clustering/origins")


@clustering_blueprint.post("/preview")
def preview_clustering():
    try:
        product_request = ClusteringRequest.from_payload(_json_payload())
        return jsonify({"ok": True, **get_clustering_service().preview(product_request)})
    except ProductClusteringError as error:
        return _error(error)
    except Exception:
        return _internal_error("/api/clustering/preview")


@clustering_blueprint.post("/run")
def run_clustering():
    try:
        product_request = ClusteringRequest.from_payload(_json_payload())
        return jsonify({"ok": True, **get_clustering_service().run(product_request)})
    except ProductClusteringError as error:
        return _error(error)
    except Exception:
        return _internal_error("/api/clustering/run")
