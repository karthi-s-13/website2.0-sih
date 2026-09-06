from fastapi import APIRouter, Request

from app.schemas.common import ApiResponse, success
from app.schemas.prediction import ModelInfoResponse
from app.services.prediction.model_loader import FEATURE_ENGINEERING_VERSION, load_model_bundle

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=ApiResponse)
def get_model_info(request: Request) -> ApiResponse:
    bundle = load_model_bundle()
    info = ModelInfoResponse(
        model_type=bundle.model_type,
        model_version=bundle.model_version,
        feature_version=FEATURE_ENGINEERING_VERSION,
        raw_feature_cols=bundle.raw_feature_cols,
        optimal_threshold=bundle.optimal_threshold,
        oof_metrics=bundle.oof_metrics,
        trained_at=bundle.trained_at,
        n_training_rows=bundle.n_training_rows,
    )
    return success(data=info.model_dump(mode="json"), trace_id=getattr(request.state, "trace_id", None))
