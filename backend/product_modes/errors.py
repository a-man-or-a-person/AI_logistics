"""Stable Product clustering errors shared by mode adapters and the facade."""


class ProductClusteringError(ValueError):
    def __init__(self, code: str, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
