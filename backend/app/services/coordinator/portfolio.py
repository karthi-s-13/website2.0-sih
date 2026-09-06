"""Portfolio Mode (spec section 7.4 / section 34): batch screening across
every ingested project, ranked by risk, with an *optional* deep dive
reserved for the top-N highest-risk projects only - cost-aware routing
(spec section 53): "This prevents expensive agentic processing for every
project when a portfolio-level screening is sufficient."
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.repositories.project_repository import list_all_projects
from app.services.diagnosis.service import diagnose_project
from app.services.health.service import get_project_health
from app.services.prediction.service import predict_cost_overrun

DEFAULT_TOP_N = 3

# Fallback ranking score (0-100) when the ML model is unavailable for a
# project - derived from the deterministic health tier only, never a
# fabricated probability.
HEALTH_TIER_SCORE = {"NORMAL": 0.0, "WATCH": 25.0, "ELEVATED": 50.0, "HIGH": 75.0, "CRITICAL": 100.0}


@dataclass(frozen=True)
class DiagnosisSummary:
    overall_risk: str
    top_driver: str | None


@dataclass(frozen=True)
class RankedProject:
    rank: int
    project_id: str
    project_name: str
    risk_score: float
    overall_health: str | None
    ml_risk_level: str | None
    ml_probability: float | None
    data_available: bool
    diagnosis_summary: DiagnosisSummary | None


@dataclass(frozen=True)
class PortfolioResult:
    as_of_date: date | None
    ranked: list[RankedProject]
    top_risk_project_ids: list[str]


def _score_project(session: Session, project_id: str, as_of: date) -> tuple[float, dict]:
    health = None
    prediction = None
    try:
        health = get_project_health(session, project_id, as_of)
    except AppError:
        pass
    try:
        prediction = predict_cost_overrun(session, project_id, as_of)
    except AppError:
        pass

    if prediction is not None:
        score = prediction.probability * 100
    elif health is not None:
        score = HEALTH_TIER_SCORE.get(health.overall_health, 0.0)
    else:
        score = 0.0

    return score, {
        "overall_health": health.overall_health if health else None,
        "ml_risk_level": prediction.risk_level if prediction else None,
        "ml_probability": prediction.probability if prediction else None,
        "data_available": health is not None or prediction is not None,
    }


def rank_portfolio(
    session: Session,
    as_of: date | None = None,
    top_n: int = DEFAULT_TOP_N,
    deep_dive_web: bool = False,
) -> PortfolioResult:
    projects = list_all_projects(session)

    scored = []
    for project in projects:
        project_as_of = as_of or project.latest_observation_month
        if project_as_of is None:
            continue
        score, info = _score_project(session, project.project_id, project_as_of)
        scored.append((score, project, project_as_of, info))

    scored.sort(key=lambda item: item[0], reverse=True)

    ranked: list[RankedProject] = []
    for i, (score, project, project_as_of, info) in enumerate(scored):
        diagnosis_summary = None
        if i < top_n:
            try:
                diagnosis = diagnose_project(session, project.project_id, project_as_of, include_web=deep_dive_web)
                top_driver = diagnosis.drivers[0].driver if diagnosis.drivers else None
                diagnosis_summary = DiagnosisSummary(overall_risk=diagnosis.overall_risk, top_driver=top_driver)
            except AppError:
                pass

        ranked.append(
            RankedProject(
                rank=i + 1,
                project_id=project.project_id,
                project_name=project.project_name,
                risk_score=round(score, 2),
                overall_health=info["overall_health"],
                ml_risk_level=info["ml_risk_level"],
                ml_probability=info["ml_probability"],
                data_available=info["data_available"],
                diagnosis_summary=diagnosis_summary,
            )
        )

    return PortfolioResult(
        as_of_date=as_of,
        ranked=ranked,
        top_risk_project_ids=[r.project_id for r in ranked[:top_n]],
    )
