import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger("http")


class TraceContextMiddleware(BaseHTTPMiddleware):
    """Attaches a trace_id/request_id to every request (OBS-001) and logs latency."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
        request_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        request.state.request_id = request_id

        start = time.perf_counter()
        structlog.contextvars.bind_contextvars(trace_id=trace_id, request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                latency_ms=round(latency_ms, 2),
            )
            structlog.contextvars.clear_contextvars()

        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Request-Id"] = request_id
        return response
