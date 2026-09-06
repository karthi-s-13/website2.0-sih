import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base
from app.services.ingestion.pipeline import ingest_directory

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
RAW_DIR = REPO_ROOT / "data" / "raw" / "flash_reports"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_cohort import (  # noqa: E402
    _generate_project_report,
    _render_markdown,
    _render_portfolio_summary,
)

from app.services.validation_cohort import INITIAL_VALIDATION_COHORT  # noqa: E402

FORBIDDEN_PHRASES = [
    "will definitely not overrun",
    "will definitely overrun",
    "will not overrun",
    "definitely will overrun",
]
REQUIRED_INTERPRETATION_SUBSTRING = "No revised cost is currently recorded as of the selected observation date."


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def ingested_session(session: Session) -> Session:
    ingest_directory(session, RAW_DIR)
    return session


def test_reports_generated_for_all_five_projects(ingested_session: Session) -> None:
    for i, project_id in enumerate(INITIAL_VALIDATION_COHORT, start=1):
        report = _generate_project_report(ingested_session, project_id, project_number=i)

        # Required per-project fields (Phase 5 spec).
        assert report.project_id == project_id
        assert report.project_name
        assert report.as_of_date
        assert report.original_cost_crore is not None
        assert report.cumulative_expenditure_crore is not None
        assert report.cost_utilisation is not None
        assert report.physical_progress is not None
        assert report.schedule_utilisation is not None
        assert report.progress_gap is not None
        assert report.ml_probability is not None
        assert 0.0 <= report.ml_probability <= 1.0
        assert report.ml_risk_level in {"LOW", "MODERATE", "ELEVATED", "HIGH", "CRITICAL"}
        assert report.data_quality is not None


def test_critical_interpretation_language(ingested_session: Session) -> None:
    """None of these 5 projects have an actual revised cost divergence, so every
    report must use the required non-committal phrasing and never a definite claim."""
    for i, project_id in enumerate(INITIAL_VALIDATION_COHORT, start=1):
        report = _generate_project_report(ingested_session, project_id, project_number=i)
        assert REQUIRED_INTERPRETATION_SUBSTRING in report.revised_cost_interpretation

        rendered = _render_markdown(report)
        lowered = rendered.lower()
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in lowered, f"project {project_id} report contains forbidden phrase: {phrase!r}"


def test_portfolio_summary_critical_interpretation(ingested_session: Session) -> None:
    reports = [
        _generate_project_report(ingested_session, pid, project_number=i)
        for i, pid in enumerate(INITIAL_VALIDATION_COHORT, start=1)
    ]
    portfolio_md, portfolio_json = _render_portfolio_summary(reports)

    # The portfolio summary legitimately *quotes* the forbidden phrases inside
    # its "must not say" warning - that's correct, self-documenting behavior,
    # not a violation. Only the rest of the document (outside that guidance)
    # must never assert them as fact.
    body_without_warning = portfolio_md.split("## Dashboard", 1)[-1]
    lowered = body_without_warning.lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in lowered, f"portfolio summary body asserts forbidden phrase: {phrase!r}"

    assert 'must **not** say' in portfolio_md.lower()  # the warning itself is present
    assert portfolio_json["cohort_size"] == 5
    assert len(portfolio_json["projects"]) == 5


def test_analysis_is_stable_and_reproducible(ingested_session: Session) -> None:
    """Exit criterion: the five-project baseline analysis is stable and reproducible.

    Re-generating from the same ingested data must yield identical analytical
    values (timestamps naturally differ between runs and are excluded)."""

    def snapshot(report):
        return (
            report.project_id,
            report.overall_health,
            report.cost_utilisation,
            report.schedule_utilisation,
            report.physical_progress,
            report.expected_progress,
            report.progress_gap,
            report.expenditure_progress_divergence,
            report.ml_probability,
            report.ml_risk_level,
            report.ml_model_version,
            report.data_quality.total_issues,
            report.historical_trend.observation_count,
        )

    first_pass = [
        snapshot(_generate_project_report(ingested_session, pid, i))
        for i, pid in enumerate(INITIAL_VALIDATION_COHORT, start=1)
    ]
    second_pass = [
        snapshot(_generate_project_report(ingested_session, pid, i))
        for i, pid in enumerate(INITIAL_VALIDATION_COHORT, start=1)
    ]

    assert first_pass == second_pass
    assert len(first_pass) == 5
