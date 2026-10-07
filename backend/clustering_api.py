"""Thin Flask handlers for the canonical clustering API."""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any

from flask import Blueprint, g, jsonify, request

from backend.services.clustering_service import (
    ClusteringRequest,
    ClusteringService,
    ProductClusteringError,
)

logger = logging.getLogger(__name__)
clustering_blueprint = Blueprint("clustering_product", __name__, url_prefix="/api/clustering")

_service: ClusteringService | None = None
_service_lock = threading.Lock()


@clustering_blueprint.before_request
def _attach_request_id() -> None:
    supplied = request.headers.get("X-Request-ID", "").strip()
    g.clustering_request_id = supplied[:64] if supplied else uuid.uuid4().hex


@clustering_blueprint.after_request
def _return_request_id(response):
    response.headers["X-Request-ID"] = g.clustering_request_id
    return response


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
    logger.warning(
        "product_clustering_error request_id=%s endpoint=%s code=%s status=%s",
        g.clustering_request_id,
        request.path,
        error.code,
        error.status,
    )
    return jsonify({"ok": False, "code": error.code, "error": str(error)}), error.status


def _internal_error(endpoint: str):
    logger.exception(
        "product_clustering_internal_error request_id=%s endpoint=%s",
        g.clustering_request_id,
        endpoint,
    )
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
        destination_region = request.args.get("destination_region") or None
        return jsonify(
            {
                "ok": True,
                **get_clustering_service().options(origin_fias, destination_region),
            }
        )
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
        service = get_clustering_service()
        product_request = ClusteringRequest.from_payload(
            _json_payload(), product_mode_catalog=service.product_mode_catalog
        )
        return jsonify(
            {
                "ok": True,
                **service.preview(product_request, request_id=g.clustering_request_id),
            }
        )
    except ProductClusteringError as error:
        return _error(error)
    except Exception:
        return _internal_error("/api/clustering/preview")


@clustering_blueprint.post("/run")
def run_clustering():
    try:
        service = get_clustering_service()
        product_request = ClusteringRequest.from_payload(
            _json_payload(), product_mode_catalog=service.product_mode_catalog
        )
        return jsonify(
            {
                "ok": True,
                **service.run(product_request, request_id=g.clustering_request_id),
            }
        )
    except ProductClusteringError as error:
        return _error(error)
    except Exception:
        return _internal_error("/api/clustering/run")


@clustering_blueprint.post("/compare")
def compare_clustering():
    try:
        return jsonify(
            {
                "ok": True,
                **get_clustering_service().compare(
                    _json_payload(), request_id=g.clustering_request_id
                ),
            }
        )
    except ProductClusteringError as error:
        return _error(error)
    except Exception:
        return _internal_error("/api/clustering/compare")


@clustering_blueprint.post("/point-rows")
def clustering_point_rows():
    try:
        return jsonify(
            {
                "ok": True,
                **get_clustering_service().point_rows(
                    _json_payload(), request_id=g.clustering_request_id
                ),
            }
        )
    except ProductClusteringError as error:
        return _error(error)
    except Exception:
        return _internal_error("/api/clustering/point-rows")
