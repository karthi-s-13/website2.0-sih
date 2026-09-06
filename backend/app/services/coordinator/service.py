"""Coordinator Agent orchestration (spec section 5): the root agent - it
owns the workflow, not the underlying computation. Classifies intent,
resolves the project, plans the required calls, executes them (in parallel
where genuinely independent), applies risk-triggered expansion, and hands
everything to the Reporting Agent for final synthesis.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models.project import Project
from app.services.coordinator import planning, stages
from app.services.coordinator.budget import Budget, BudgetTracker
from app.services.coordinator.intent import PORTFOLIO_ANALYSIS, classify_intent
from app.services.coordinator.portfolio import DEFAULT_TOP_N, rank_portfolio
from app.services.coordinator.resolution import AMBIGUOUS, NOT_FOUND, resolve_project
from app.services.coordinator.state import AnalysisState
from app.services.reporting.builder import build_report
from app.services.reporting.narrative import summarize_report


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _execute_plan(session: Session, state: AnalysisState, tracker: BudgetTracker, parallel: bool = True) -> None:
    plan = state.plan
    runs = {
        planning.HISTORY: stages.run_history,
        planning.HEALTH: stages.run_health,
        planning.PREDICTION: stages.run_prediction,
        planning.ANOMALY: stages.run_anomaly,
        planning.REVIEW: stages.run_review,
        planning.WEB: stages.run_web,
        planning.DIAGNOSIS: stages.run_diagnosis,
        planning.INTERVENTION_CALL: stages.run_intervention,
    }

    already_run = {sr.stage for sr in state.stage_results}
    remaining = [s for s in plan if s != planning.PROJECT and s not in already_run]

    # The one genuine parallelization opportunity given this design's
    # collapsed call set (spec section 69): HISTORY is independent of, and
    # much faster than, DIAGNOSIS/INTERVENTION (which themselves make
    # several sequential Review/Web calls). Each thread gets its own
    # Session - SQLAlchemy sessions aren't safe to share across threads.
    #
    # `parallel=False` (used by the test suite) runs the same two calls
    # sequentially on the caller's own session instead: a single shared,
    # low-level sqlite3 connection (as used by the in-memory test fixtures)
    # is not safe under genuine concurrent cursor use from multiple threads,
    # which is a test-infrastructure limitation, not a correctness question
    # for the plan/state logic these tests exercise. True concurrent
    # execution is exercised live against real Postgres in
    # `scripts/run_coordinator.py`.
    heavy = planning.INTERVENTION_CALL if planning.INTERVENTION_CALL in remaining else (
        planning.DIAGNOSIS if planning.DIAGNOSIS in remaining else None
    )
    if planning.HISTORY in remaining and heavy is not None and not tracker.is_exceeded() and not parallel:
        remaining = [s for s in remaining if s not in {planning.HISTORY, heavy}]
        stages.run_history(session, state)
        runs[heavy](session, state)
        tracker.record_stage()
        tracker.record_stage()
    elif planning.HISTORY in remaining and heavy is not None and not tracker.is_exceeded():
        remaining = [s for s in remaining if s not in {planning.HISTORY, heavy}]

        # Each thread gets its own Session bound to the *same engine* as the
        # caller's session (SQLAlchemy sessions aren't safe to share across
        # threads) - deriving it from `session.get_bind()` rather than the
        # global SessionLocal so this works against whatever database the
        # caller is actually using (production Postgres, or an in-memory
        # sqlite test fixture).
        bind = session.get_bind()

        def _run_history_isolated() -> AnalysisState:
            sub_state = AnalysisState(trace_id=state.trace_id, analysis_id=state.analysis_id, query=state.query)
            sub_state.project_id, sub_state.as_of_date = state.project_id, state.as_of_date
            with Session(bind=bind) as sub_session:
                stages.run_history(sub_session, sub_state)
            return sub_state

        def _run_heavy_isolated() -> AnalysisState:
            sub_state = AnalysisState(trace_id=state.trace_id, analysis_id=state.analysis_id, query=state.query)
            sub_state.project_id, sub_state.as_of_date = state.project_id, state.as_of_date
            with Session(bind=bind) as sub_session:
                runs[heavy](sub_session, sub_state)
            return sub_state

        with ThreadPoolExecutor(max_workers=2) as executor:
            history_future = executor.submit(_run_history_isolated)
            heavy_future = executor.submit(_run_heavy_isolated)
            history_result = history_future.result()
            heavy_result = heavy_future.result()

        state.history = history_result.history
        state.stage_results.extend(history_result.stage_results)
        state.errors.extend(history_result.errors)
        state.warnings.extend(history_result.warnings)

        if heavy == planning.INTERVENTION_CALL:
            state.intervention = heavy_result.intervention
            state.diagnosis = heavy_result.diagnosis
        else:
            state.diagnosis = heavy_result.diagnosis
        if state.health is None:
            state.health = heavy_result.health
        if state.prediction is None:
            state.prediction = heavy_result.prediction
        state.stage_results.extend(heavy_result.stage_results)
        state.errors.extend(heavy_result.errors)
        state.warnings.extend(heavy_result.warnings)
        tracker.record_stage()
        tracker.record_stage()

    for stage_name in remaining:
        if tracker.is_exceeded():
            stages.record_skipped(state, stage_name, "execution budget exceeded")
            continue
        runs[stage_name](session, state)
        tracker.record_stage()


def _finalize_report(session: Session, state: AnalysisState) -> None:
    settings = get_settings()
    narrative = summarize_report(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        project_name=state.project_name or "",
        health=state.health,
        prediction=state.prediction,
        history=state.history,
        diagnosis=state.diagnosis,
        intervention=state.intervention,
        question=state.query,
    )
    state.report = build_report(
        trace_id=state.trace_id,
        analysis_id=state.analysis_id,
        project_id=state.project_id,
        project_name=state.project_name or "",
        as_of_date=state.as_of_date or date.today(),
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


def run_analysis(
    session: Session,
    query: str,
    project_id: str | None = None,
    as_of_date: date | None = None,
    budget: Budget | None = None,
    parallel: bool = True,
) -> AnalysisState:
    state = AnalysisState(trace_id=_new_id("trace"), analysis_id=_new_id("analysis"), query=query)
    tracker = BudgetTracker(budget=budget or Budget())
    settings = get_settings()

    intent_result = classify_intent(query, api_key=settings.groq_api_key, model=settings.groq_model)
    state.intent = intent_result.intent
    state.intent_source = intent_result.source

    if intent_result.intent == PORTFOLIO_ANALYSIS:
        state.portfolio = rank_portfolio(session, as_of=as_of_date, top_n=DEFAULT_TOP_N)
        return state

    resolution = resolve_project(session, query, explicit_project_id=project_id)
    state.resolution_status = resolution.status
    if resolution.status == AMBIGUOUS:
        state.candidates = resolution.candidates
        return state
    if resolution.status == NOT_FOUND:
        raise NotFoundError(f"could not resolve a project from: {query!r}")

    state.project_id = resolution.project_id
    project = session.get(Project, state.project_id)
    if project is None:
        raise NotFoundError(f"project {state.project_id} not found")
    state.project_name = project.project_name
    state.as_of_date = as_of_date or project.latest_observation_month

    state.plan = planning.plan_for_intent(state.intent)
    _execute_plan(session, state, tracker, parallel=parallel)

    if (
        planning.DIAGNOSIS not in state.plan
        and planning.INTERVENTION_CALL not in state.plan
        and planning.should_expand(
            health_overall=state.health.overall_health if state.health else None,
            ml_risk_level=state.prediction.risk_level if state.prediction else None,
        )
        and not tracker.is_exceeded()
    ):
        state.expanded = True
        expanded_plan = planning.expand_plan(state.plan)
        state.plan = expanded_plan
        _execute_plan(session, state, tracker, parallel=parallel)

    _finalize_report(session, state)
    return state
