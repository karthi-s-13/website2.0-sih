"""Builds a full `Report` (backend/app/services/reporting/builder.py) for
Reporting MCP, reusing the Coordinator's own building blocks
(coordinator/stages.py's public stage functions, reporting/builder.py,
reporting/narrative.py) without touching coordinator/stages.py itself.

Gap this closes: the Coordinator's own FULL_PLAN (PROJECT, HISTORY,
INTERVENTION_CALL - coordinator/planning.py) never separately populates
state.health/state.prediction; only run_intervention runs, and it sets
state.intervention/state.diagnosis, not state.health/state.prediction. A
Reporting-MCP-generated report calling only run_intervention would
therefore have current_health=None and cost_overrun_risk=None even though
diagnosis internally computed both. This orchestration explicitly also
calls run_health/run_prediction first - additive, no coordinator/ changes.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.repositories.project_repository import get_project
from app.services.coordinator import stages
from app.services.coordinator.state import AnalysisState
from app.services.reporting.builder import Report, build_report
from app.services.reporting.narrative import summarize_report


def build_full_report(session: Session, project_id: str, as_of_date: date | None = None) -> Report:
    project = get_project(session, project_id)
    if project is None:
        raise NotFoundError(f"project {project_id} not found")

    state = AnalysisState(
        trace_id=uuid.uuid4().hex,
        analysis_id=uuid.uuid4().hex,
        query="MCP generate_report",
        project_id=project_id,
        project_name=project.project_name,
        as_of_date=as_of_date,
    )

    stages.run_health(session, state)
    stages.run_prediction(session, state)
    stages.run_history(session, state)
    stages.run_intervention(session, state)

    settings = get_settings()
    narrative = summarize_report(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        project_name=state.project_name,
        health=state.health,
        prediction=state.prediction,
        history=state.history,
        diagnosis=state.diagnosis,
        intervention=state.intervention,
    )

    resolved_as_of = as_of_date or project.latest_observation_month

    return build_report(
        trace_id=state.trace_id,
        analysis_id=state.analysis_id,
        project_id=project_id,
        project_name=state.project_name,
        as_of_date=resolved_as_of,
        executive_summary=narrative.text,
        history=state.history,
        health=state.health,
        prediction=state.prediction,
        prediction_error=state.prediction_error,
        review=state.review,
        web=state.web,
        diagnosis=state.diagnosis,
        intervention=state.intervention,
    )
