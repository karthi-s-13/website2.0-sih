"""Web Intelligence Agent (Phase 8) orchestration - the full spec section 20
workflow:

    Project Context -> Risk Context -> Query Planner -> Search ->
    Source Filtering -> Source Fetch -> Claim Extraction ->
    Date Verification -> Project Relevance -> Evidence Store

"Source Fetch" is Tavily's own `search_depth="advanced"` server-side content
extraction (see search_client.py) rather than a separate fetch step - the
`content` field on each SearchResult already is the fetched source text.

Graceful degradation (PRD section 65): if the search provider is
unavailable for one topic, that topic is skipped (with a warning) and the
rest of the run continues - the agent never blocks on, or fabricates
evidence for, a single failed topic.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.models.project import Project
from app.models.web_evidence import WebEvidence
from app.repositories.project_repository import get_data_quality_issues_for_project
from app.repositories.web_evidence_repository import store_evidence
from app.services.health.service import get_project_health
from app.services.prediction.service import predict_cost_overrun
from app.services.web import query_planner, trust
from app.services.web.claim_extraction import extract_claims
from app.services.web.date_verification import verify_date
from app.services.web.query_planner import PlannedQuery
from app.services.web.search_client import SearchResult, WebSearchUnavailableError, search_web
from app.services.web.trigger import TriggerDecision, should_trigger

DQ_RISK_ISSUE_TYPES = {"NON_MONOTONIC_CUMULATIVE_EXPENDITURE", "NON_MONOTONIC_PHYSICAL_PROGRESS"}
CONCERNING_HEALTH_LEVELS = {"WATCH", "ELEVATED", "HIGH", "CRITICAL"}
MAX_RESULTS_PER_QUERY = 5


@dataclass(frozen=True)
class WebEvidenceItem:
    evidence_id: str
    topic: str
    source: str
    url: str
    title: str | None
    publication_date: date | None
    date_confidence: str
    finding: str
    project_relevance: float
    trust_tier: str
    source_quality: str


@dataclass(frozen=True)
class WebIntelligenceResult:
    project_id: str
    project_name: str
    triggered: bool
    trigger_reason: str
    topics_searched: list[str]
    evidence: list[WebEvidenceItem]
    warnings: list[str]
    searched_at: str


def _driver_categories(
    overall_health: str | None,
    progress_gap: float | None,
    expenditure_progress_divergence: float | None,
    recent_trend_label: str | None,
    ml_risk_level: str | None,
    dq_issue_types: set[str],
) -> list[str]:
    categories: list[str] = []
    if ml_risk_level in {"HIGH", "CRITICAL"}:
        categories.append("HIGH_ML_RISK")
    if overall_health in CONCERNING_HEALTH_LEVELS and progress_gap is not None and progress_gap < 0:
        categories.append("SCHEDULE_BEHIND")
    if (
        overall_health in CONCERNING_HEALTH_LEVELS
        and expenditure_progress_divergence is not None
        and expenditure_progress_divergence > 0
    ):
        categories.append("EXPENDITURE_AHEAD")
    if dq_issue_types & DQ_RISK_ISSUE_TYPES:
        categories.append("DATA_QUALITY_CONCERN")
    if recent_trend_label == "STAGNANT":
        categories.append("STAGNANT_TREND")
    return categories


def evidence_id(project_id: str, url: str, topic: str) -> str:
    """Content-addressed evidence id (public: also reused by Knowledge MCP's
    store_evidence tool, backend/app/mcp/knowledge/service.py, so the same
    project_id:topic:url triple always resolves to the same row via
    session.merge - re-running a search or a manual store updates rather
    than duplicates)."""
    digest = hashlib.sha256(f"{project_id}:{topic}:{url}".encode()).hexdigest()[:16]
    return f"ev-{digest}"


def _run_query(
    session: Session,
    project: Project,
    planned: PlannedQuery,
    as_of: date,
    settings,
) -> tuple[list[WebEvidence], list[str]]:
    try:
        results: list[SearchResult] = search_web(
            planned.query_text, api_key=settings.tavily_api_key, max_results=MAX_RESULTS_PER_QUERY
        )
    except WebSearchUnavailableError as exc:
        return [], [f'topic "{planned.topic}": {exc}']

    if not results:
        return [], []

    claims = extract_claims(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        project_name=project.project_name,
        agency=project.agency,
        state=project.state,
        topic=planned.topic,
        results=results,
    )

    rows: list[WebEvidence] = []
    for claim in claims:
        result = claim.result
        trust_tier, source_quality = trust.classify_source(result.url, project.agency_code)
        published_date, date_confidence = verify_date(result.published_date_raw)
        domain = trust.extract_domain(result.url) or result.url
        rows.append(
            WebEvidence(
                evidence_id=evidence_id(project.project_id, result.url, planned.topic),
                project_id=project.project_id,
                source_type="WEB",
                topic=planned.topic,
                query_used=planned.query_text,
                source=domain,
                url=result.url,
                title=result.title,
                published_date=published_date,
                date_confidence=date_confidence,
                finding=claim.finding,
                project_relevance=claim.project_relevance,
                trust_tier=trust_tier,
                source_quality=source_quality,
            )
        )
    return rows, []


def get_web_intelligence(
    session: Session,
    project_id: str,
    as_of_date: date | None = None,
    force: bool = False,
    for_diagnosis: bool = False,
) -> WebIntelligenceResult:
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError(f"project {project_id} not found")
    if project.latest_observation_month is None:
        raise NotFoundError(f"project {project_id} has no observations")

    as_of = as_of_date or project.latest_observation_month
    searched_at = datetime.now(UTC).isoformat()

    health = get_project_health(session, project_id, as_of)

    ml_risk_level = None
    try:
        prediction = predict_cost_overrun(session, project_id, as_of)
        ml_risk_level = prediction.risk_level
    except AppError:
        pass  # ML unavailable must not block the web intelligence agent

    decision: TriggerDecision = should_trigger(
        overall_health=health.overall_health,
        ml_risk_level=ml_risk_level,
        force=force,
        for_diagnosis=for_diagnosis,
    )
    if not decision.triggered:
        return WebIntelligenceResult(
            project_id=project_id,
            project_name=project.project_name,
            triggered=False,
            trigger_reason=decision.reason,
            topics_searched=[],
            evidence=[],
            warnings=[],
            searched_at=searched_at,
        )

    dq_issues = get_data_quality_issues_for_project(session, project_id)
    driver_categories = _driver_categories(
        overall_health=health.overall_health,
        progress_gap=health.progress_gap,
        expenditure_progress_divergence=health.expenditure_progress_divergence,
        recent_trend_label=health.recent_trend.label,
        ml_risk_level=ml_risk_level,
        dq_issue_types={issue.issue_type for issue in dq_issues},
    )

    settings = get_settings()
    planned_queries = query_planner.plan_queries(
        project_name=project.project_name,
        agency=project.agency,
        state=project.state,
        driver_categories=driver_categories,
    )

    all_rows: list[WebEvidence] = []
    seen_urls: set[str] = set()
    warnings: list[str] = []

    for planned in planned_queries:
        rows, query_warnings = _run_query(session, project, planned, as_of, settings)
        warnings.extend(query_warnings)
        for row in rows:
            if row.url in seen_urls:  # Source Filtering: dedupe across topics
                continue
            seen_urls.add(row.url)
            all_rows.append(row)

    if all_rows:
        store_evidence(session, all_rows)

    evidence = [
        WebEvidenceItem(
            evidence_id=row.evidence_id,
            topic=row.topic,
            source=row.source,
            url=row.url,
            title=row.title,
            publication_date=row.published_date,
            date_confidence=row.date_confidence,
            finding=row.finding,
            project_relevance=row.project_relevance,
            trust_tier=row.trust_tier,
            source_quality=row.source_quality,
        )
        for row in all_rows
    ]

    return WebIntelligenceResult(
        project_id=project_id,
        project_name=project.project_name,
        triggered=True,
        trigger_reason=decision.reason,
        topics_searched=[p.topic for p in planned_queries],
        evidence=evidence,
        warnings=warnings,
        searched_at=searched_at,
    )
