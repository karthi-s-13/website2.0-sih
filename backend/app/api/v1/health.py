from fastapi import APIRouter, Request

from app.core.db import database_is_reachable
from app.schemas.common import ApiResponse, success

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse)
def health(request: Request) -> ApiResponse:
    """Liveness probe: process is up. Does not check downstream dependencies."""
    return success(data={"status": "ok"}, trace_id=getattr(request.state, "trace_id", None))


@router.get("/ready", response_model=ApiResponse)
def ready(request: Request) -> ApiResponse:
    """Readiness probe: process is up AND required dependencies are reachable."""
    checks = {"database": database_is_reachable()}
    all_ready = all(checks.values())
    return success(
        data={"ready": all_ready, "checks": checks},
        trace_id=getattr(request.state, "trace_id", None),
    )
