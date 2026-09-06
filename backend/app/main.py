from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import health
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError, DataQualityFailureError, ModelUnavailableError, NotFoundError
from app.core.logging import configure_logging
from app.core.middleware import TraceContextMiddleware
from app.schemas.common import failure

configure_logging()
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(TraceContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ERROR_STATUS_CODES = {
    NotFoundError: 404,
    DataQualityFailureError: 422,
    ModelUnavailableError: 503,
}


@app.exception_handler(AppError)
def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    status_code = next(
        (code for error_type, code in _ERROR_STATUS_CODES.items() if isinstance(exc, error_type)), 422
    )
    trace_id = getattr(request.state, "trace_id", None)
    body = failure(error_code=exc.error_code, message=exc.message, trace_id=trace_id)
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


# Versioned API surface
app.include_router(api_router, prefix=settings.api_v1_prefix)

# Unversioned infrastructure health checks (load balancer / k8s probes)
app.include_router(health.router, prefix="/api")
