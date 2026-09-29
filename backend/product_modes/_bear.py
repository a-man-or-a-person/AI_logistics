"""Small shared parsing mechanics for Bear-mode adapters."""

from __future__ import annotations

from backend.product_modes.catalog import ModeParameterValue
from backend.product_modes.errors import ProductClusteringError

DEFAULT_THRESHOLD = 0.35
SINGLETON_THRESHOLD = 0.7
THRESHOLD_CHOICES = (0.2, 0.25, 0.3, 0.35, 0.4, 0.5)


def number(value: ModeParameterValue, message: str) -> float:
    if isinstance(value, bool):
        raise ProductClusteringError("INVALID_MODE_PARAMETERS", message, 400)
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ProductClusteringError("INVALID_MODE_PARAMETERS", message, 400) from error


def fixed_singleton(value: ModeParameterValue) -> float:
    normalized = number(value, "Порог одиночной точки должен быть числом.")
    if abs(normalized - SINGLETON_THRESHOLD) > 1e-9:
        raise ProductClusteringError(
            "INVALID_MODE_PARAMETERS",
            "Порог одиночной точки фиксирован на уровне +70%.",
            400,
        )
    return normalized
