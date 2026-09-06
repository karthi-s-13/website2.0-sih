"""Stage execution - one function per distinct service call (see
`planning.py`'s module docstring for why this is fewer than the spec's 12
named stages). Every stage catches its own exceptions and records
SUCCESS/FAILED on `state.stage_results` rather than raising (spec sections
46/47: graceful degradation - a failed `WEB` call must never block
`HISTORY` or the rest of the report; PRD section 65: never fabricate the
unavailable information, just say so).
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.project import Project
from app.services.anomaly.service import get_project_anomalies
from app.services.coordinator.state import FAILED, SKIPPED, SUCCESS, AnalysisState, StageResult
from app.services.diagnosis.service import diagnose_project
from app.services.health.service import get_project_health
from app.services.history.service import get_project_history
from app.services.intervention.service import recommend_interventions
from app.services.prediction.service import predict_cost_overrun
from app.services.rag.service import search_review_evidence
from app.services.web.service import get_web_intelligence


@contextmanager
def _timed_stage(state: AnalysisState, name: str):
    start = time.monotonic()
    try:
        yield
    except Exception as exc:  # noqa: BLE001 - a stage failure must degrade gracefully, never raise
        duration_ms = (time.monotonic() - start) * 1000
        state.stage_results.append(StageResult(stage=name, status=FAILED, error=str(exc), duration_ms=duration_ms))
        state.errors.append(f"{name}: {exc}")
    else:
        duration_ms = (time.monotonic() - start) * 1000
        state.stage_results.append(StageResult(stage=name, status=SUCCESS, error=None, duration_ms=duration_ms))


def record_skipped(state: AnalysisState, name: str, reason: str) -> None:
    state.stage_results.append(StageResult(stage=name, status=SKIPPED, error=None, duration_ms=0.0))
    state.warnings.append(f"{name} skipped: {reason}")


def resolve_as_of(session: Session, project_id: str, as_of_date: date | None) -> date | None:
    if as_of_date is not None:
        return as_of_date
    project = session.get(Project, project_id)
    return project.latest_observation_month if project is not None else None


def run_history(session: Session, state: AnalysisState) -> None:
    with _timed_stage(state, "HISTORY"):
        state.history = get_project_history(session, state.project_id, as_of_date=state.as_of_date)


def run_health(session: Session, state: AnalysisState) -> None:
    with _timed_stage(state, "HEALTH"):
        as_of = resolve_as_of(session, state.project_id, state.as_of_date)
        state.health = get_project_health(session, state.project_id, as_of)


def run_prediction(session: Session, state: AnalysisState) -> None:
    with _timed_stage(state, "PREDICTION"):
        try:
            as_of = resolve_as_of(session, state.project_id, state.as_of_date)
            state.prediction = predict_cost_overrun(session, state.project_id, as_of)
        except AppError as exc:
            state.prediction_error = True
            state.warnings.append(f"PREDICTION unavailable: {exc.message}")


def run_anomaly(session: Session, state: AnalysisState) -> None:
    with _timed_stage(state, "ANOMALY"):
        as_of = resolve_as_of(session, state.project_id, state.as_of_date)
        state.anomalies = get_project_anomalies(session, state.project_id, as_of)


def run_review(session: Session, state: AnalysisState) -> None:
    with _timed_stage(state, "REVIEW"):
        state.review = search_review_evidence(session, state.project_id, question=state.query)


def run_web(session: Session, state: AnalysisState) -> None:
    with _timed_stage(state, "WEB"):
        state.web = get_web_intelligence(session, state.project_id, as_of_date=state.as_of_date, force=True)


def run_diagnosis(session: Session, state: AnalysisState) -> None:
    with _timed_stage(state, "DIAGNOSIS"):
        state.diagnosis = diagnose_project(
            session, state.project_id, as_of_date=state.as_of_date, question=state.query
        )
        # DIAGNOSIS always computes health internally for the same as_of_date
        # (needed for evidence fusion/drivers) - reuse it rather than leaving
        # the report's health section empty just because a standalone HEALTH
        # stage wasn't in this intent's plan.
        if state.health is None:
            state.health = state.diagnosis.health
        if state.prediction is None:
            state.prediction = state.diagnosis.prediction


def run_intervention(session: Session, state: AnalysisState) -> None:
    with _timed_stage(state, "INTERVENTION"):
        state.intervention = recommend_interventions(
            session, state.project_id, as_of_date=state.as_of_date, question=state.query
        )
        state.diagnosis = state.intervention.diagnosis
        if state.health is None:
            state.health = state.diagnosis.health
        if state.prediction is None:
            state.prediction = state.diagnosis.prediction
