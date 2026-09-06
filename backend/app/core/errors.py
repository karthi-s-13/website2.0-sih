"""Shared error types that carry a stable `error_code` (see SRS section 23,
"Error Handling": `{"status": "FAILED", "error_code": "...", ...}`).
"""

from __future__ import annotations


class AppError(Exception):
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DataLeakageError(AppError):
    """Raised when a feature/prediction computation would use data with a
    timestamp after the snapshot/prediction timestamp (SRS section 1, DR-005,
    FR-012). Must block the computation, never just warn.
    """

    error_code = "DATA_LEAKAGE_DETECTED"


class ModelUnavailableError(AppError):
    """Raised when the ML model artifact cannot be loaded (SRS section 23)."""

    error_code = "ML_MODEL_UNAVAILABLE"


class DataQualityFailureError(AppError):
    """Raised when a prediction cannot be produced because required
    point-in-time data is missing (SRS section 71: a mandatory condition
    failing must yield NOT_AVAILABLE / DATA_QUALITY_FAILURE, never a
    fabricated prediction)."""

    error_code = "DATA_QUALITY_FAILURE"


class NotFoundError(AppError):
    error_code = "NOT_FOUND"
