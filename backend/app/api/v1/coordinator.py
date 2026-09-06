from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.common import ApiResponse, success
from app.schemas.coordinator import AnalysisResponse, AnalyzeRequest, PortfolioResponse
from app.services.coordinator.portfolio import DEFAULT_TOP_N, rank_portfolio
from app.services.coordinator.service import run_analysis
from app.services.coordinator.state import AnalysisState

router = APIRouter(tags=["coordinator"])


def _to_analysis_response(state: AnalysisState) -> AnalysisResponse:
    report = None
    if state.report is not None:
        report = {
            **state.report.__dict__,
        }
    return AnalysisResponse(
        trace_id=state.trace_id,
        analysis_id=state.analysis_id,
        intent=state.intent,
        intent_source=state.intent_source,
        resolution_status=state.resolution_status,
        project_id=state.project_id,
        project_name=state.project_name,
        as_of_date=state.as_of_date,
        plan=state.plan,
        expanded=state.expanded,
        stage_results=[sr.__dict__ for sr in state.stage_results],
        report=report,
        candidates=[c.__dict__ for c in state.candidates],
        errors=state.errors,
        warnings=state.warnings,
    )


@router.post("/analyze", response_model=ApiResponse)
def analyze(body: AnalyzeRequest, request: Request, db: Session = Depends(get_db)) -> ApiResponse:
    state = run_analysis(db, body.query, project_id=body.project_id, as_of_date=body.as_of)
    response = _to_analysis_response(state)
    return success(
        data=response.model_dump(mode="json"), trace_id=getattr(request.state, "trace_id", None)
    )


@router.get("/portfolio", response_model=ApiResponse)
def portfolio(
    request: Request,
    as_of: date | None = Query(default=None),
    top_n: int = Query(default=DEFAULT_TOP_N, ge=0, le=50),
    deep_dive_web: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = rank_portfolio(db, as_of=as_of, top_n=top_n, deep_dive_web=deep_dive_web)
    response = PortfolioResponse(
        as_of_date=result.as_of_date,
        ranked=[
            {**r.__dict__, "diagnosis_summary": r.diagnosis_summary.__dict__ if r.diagnosis_summary else None}
            for r in result.ranked
        ],
        top_risk_project_ids=result.top_risk_project_ids,
    )
    return success(
        data=response.model_dump(mode="json"), trace_id=getattr(request.state, "trace_id", None)
    )
