from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiError(BaseModel):
    error_code: str
    message: str


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope (SRS section 13)."""

    status: str = "success"
    data: T | None = None
    trace_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    errors: list[ApiError] = Field(default_factory=list)


def success(data: Any = None, trace_id: str | None = None) -> ApiResponse:
    return ApiResponse(status="success", data=data, trace_id=trace_id)


def failure(error_code: str, message: str, trace_id: str | None = None) -> ApiResponse:
    return ApiResponse(
        status="FAILED",
        data=None,
        trace_id=trace_id,
        errors=[ApiError(error_code=error_code, message=message)],
    )
