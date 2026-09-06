#!/usr/bin/env python
"""Phase 5 CLI: Five-Project Validation — baseline analysis reports.

Generates a per-project validation report and a portfolio summary for each
of the 5 forward-looking early-warning projects. Proves that the core
predictive pipeline (Phases 1–4) works end-to-end before agents are added.

Usage (from repo root, with the backend venv active):

    python scripts/validate_cohort.py

Outputs:
    data/validation/project_01/  …  data/validation/project_05/
        report.md       Human-readable validation report
        report.json     Machine-readable validation data
    data/validation/portfolio_summary.md
    data/validation/portfolio_summary.json
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.repositories.project_repository import (  # noqa: E402
    get_chronological_observations,
    get_data_quality_issues_for_project,
    get_project,
    get_project_events,
)
from app.services.health.service import get_project_health  # noqa: E402
from app.services.prediction.service import predict_cost_overrun  # noqa: E402
from app.services.validation_cohort import INITIAL_VALIDATION_COHORT  # noqa: E402

import app.models  # noqa: E402, F401  (registers models on Base.metadata)

VALIDATION_DIR = REPO_ROOT / "data" / "validation"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ObservationSummary:
    month: str
    cumulative_expenditure_crore: float | None
    physical_progress_percent: float | None
    notes: str | None


@dataclass
class HistoricalTrend:
    observation_count: int
    first_observation: str | None
    latest_observation: str | None
    observations: list[ObservationSummary]
    events: list[dict[str, Any]]


@dataclass
class DataQualitySummary:
    total_issues: int
    issues_by_severity: dict[str, int]
    issues: list[dict[str, Any]]


@dataclass
class ProjectValidationReport:
    # Metadata
    report_generated_at: str
    report_version: str

    # Project profile
    project_id: str
    project_name: str
    project_number: int  # 1-5 ordering
    agency: str | None
    state: str | None
    original_cost_crore: float | None
    revised_cost_crore: float | None
    cumulative_expenditure_crore: float | None
    as_of_date: str

    # Health metrics
    overall_health: str
    cost_utilisation: float | None
    schedule_utilisation: float | None
    physical_progress: float | None
    expected_progress: float | None
    progress_gap: float | None
    expenditure_progress_divergence: float | None

    # Trend
    recent_trend_label: str
    monthly_progress_change: float | None
    progress_slope: float | None
    consecutive_stagnant_months: int

    # ML prediction
    ml_probability: float | None
    ml_risk_level: str | None
    ml_model_version: str | None
    ml_feature_version: str | None
    ml_leakage_check: str | None

    # Revised cost interpretation
    revised_cost_interpretation: str

    # Data quality
    data_quality: DataQualitySummary

    # Historical trend
    historical_trend: HistoricalTrend

    # Prediction timestamp
    prediction_timestamp: str | None


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _fmt(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _generate_project_report(
    session, project_id: str, project_number: int
) -> ProjectValidationReport:
    """Collect all Phase 1–4 data for a single project and return a report."""

    project = get_project(session, project_id)
    if project is None:
        raise RuntimeError(f"project {project_id} not ingested — run ingest_flash_reports.py first")
    if project.latest_observation_month is None:
        raise RuntimeError(f"project {project_id} has no observations")

    as_of = project.latest_observation_month
    now_utc = datetime.now(timezone.utc)

    # --- Health ---
    health = get_project_health(session, project_id, as_of)

    # --- ML prediction ---
    ml_probability = None
    ml_risk_level = None
    ml_model_version = None
    ml_feature_version = None
    ml_leakage_check = None
    prediction_timestamp = None

    try:
        result = predict_cost_overrun(session, project_id, as_of)
        ml_probability = result.probability
        ml_risk_level = result.risk_level
        ml_model_version = result.model_version
        ml_feature_version = result.feature_version
        ml_leakage_check = result.leakage_check
        prediction_timestamp = now_utc.isoformat()
    except Exception as exc:  # noqa: BLE001
        ml_risk_level = f"ERROR: {exc}"

    # --- Historical observations ---
    observations = get_chronological_observations(session, project_id)
    obs_summaries = [
        ObservationSummary(
            month=obs.observation_month.isoformat(),
            cumulative_expenditure_crore=obs.cumulative_expenditure_crore,
            physical_progress_percent=obs.physical_progress_percent,
            notes=obs.notes,
        )
        for obs in observations
    ]

    # --- Events ---
    events = get_project_events(session, project_id)
    events_data = [
        {
            "month": ev.event_month.isoformat(),
            "type": ev.event_type,
            "description": ev.description,
            "previous_value": ev.previous_value,
            "new_value": ev.new_value,
        }
        for ev in events
    ]

    # --- Data quality ---
    dq_issues = get_data_quality_issues_for_project(session, project_id)
    severity_counts: dict[str, int] = {}
    dq_issue_dicts: list[dict[str, Any]] = []
    for issue in dq_issues:
        severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
        dq_issue_dicts.append({
            "type": issue.issue_type,
            "severity": issue.severity,
            "field": issue.field,
            "original_value": issue.original_value,
            "action": issue.action,
        })

    cumulative_expenditure_at_as_of = observations[-1].cumulative_expenditure_crore if observations else None

    # --- Revised cost interpretation ---
    if project.revised_cost_crore is None or (
        project.original_cost_crore is not None
        and project.revised_cost_crore == project.original_cost_crore
    ):
        revised_cost_interpretation = (
            "No revised cost is currently recorded as of the selected observation date. "
            "The ML probability is a forward-looking risk estimate, not a confirmed outcome."
        )
    else:
        revised_cost_interpretation = (
            f"A revised cost of ₹{project.revised_cost_crore:.2f} Cr is recorded. "
            "This may or may not indicate a cost overrun relative to the original cost. "
            "The ML probability remains a forward-looking risk estimate."
        )

    return ProjectValidationReport(
        report_generated_at=now_utc.isoformat(),
        report_version="phase-5-v1",
        project_id=project_id,
        project_name=project.project_name,
        project_number=project_number,
        agency=project.agency,
        state=project.state,
        original_cost_crore=project.original_cost_crore,
        revised_cost_crore=project.revised_cost_crore,
        cumulative_expenditure_crore=cumulative_expenditure_at_as_of,
        as_of_date=as_of.isoformat(),
        overall_health=health.overall_health,
        cost_utilisation=health.cost_utilisation,
        schedule_utilisation=health.schedule_utilisation,
        physical_progress=health.physical_progress,
        expected_progress=health.expected_progress,
        progress_gap=health.progress_gap,
        expenditure_progress_divergence=health.expenditure_progress_divergence,
        recent_trend_label=health.recent_trend.label,
        monthly_progress_change=health.recent_trend.monthly_progress_change,
        progress_slope=health.recent_trend.progress_slope,
        consecutive_stagnant_months=health.recent_trend.consecutive_stagnant_months,
        ml_probability=ml_probability,
        ml_risk_level=ml_risk_level,
        ml_model_version=ml_model_version,
        ml_feature_version=ml_feature_version,
        ml_leakage_check=ml_leakage_check,
        revised_cost_interpretation=revised_cost_interpretation,
        data_quality=DataQualitySummary(
            total_issues=len(dq_issues),
            issues_by_severity=severity_counts,
            issues=dq_issue_dicts,
        ),
        historical_trend=HistoricalTrend(
            observation_count=len(observations),
            first_observation=observations[0].observation_month.isoformat() if observations else None,
            latest_observation=observations[-1].observation_month.isoformat() if observations else None,
            observations=obs_summaries,
            events=events_data,
        ),
        prediction_timestamp=prediction_timestamp,
    )


def _render_markdown(report: ProjectValidationReport) -> str:
    """Render a human-readable markdown report for one project."""
    lines: list[str] = []
    a = lines.append

    a(f"# Validation Report — Project {report.project_number:02d}")
    a("")
    a(f"**Report Generated:** {report.report_generated_at}  ")
    a(f"**Report Version:** {report.report_version}")
    a("")

    # --- Project Profile ---
    a("## 1. Project Profile")
    a("")
    a("| Field | Value |")
    a("|---|---|")
    a(f"| Project ID | `{report.project_id}` |")
    a(f"| Project Name | {report.project_name} |")
    a(f"| Agency | {report.agency or '—'} |")
    a(f"| State | {report.state or '—'} |")
    a(f"| Original Cost | ₹{_fmt(report.original_cost_crore)} Cr |")
    a(f"| Revised Cost | {'₹' + _fmt(report.revised_cost_crore) + ' Cr' if report.revised_cost_crore is not None else '—'} |")
    a(f"| Cumulative Expenditure (as of {report.as_of_date}) | ₹{_fmt(report.cumulative_expenditure_crore)} Cr |")
    a(f"| As-of Date | {report.as_of_date} |")
    a("")

    # --- Current Health ---
    a("## 2. Current Health")
    a("")
    a("| Metric | Value |")
    a("|---|---|")
    a(f"| **Overall Health** | **{report.overall_health}** |")
    a(f"| Cost Utilisation | {_fmt(report.cost_utilisation, 1)}% |")
    a(f"| Schedule Utilisation | {_fmt(report.schedule_utilisation, 1)}% |")
    a(f"| Physical Progress | {_fmt(report.physical_progress, 1)}% |")
    a(f"| Expected Progress | {_fmt(report.expected_progress, 1)}% |")
    a(f"| Progress Gap | {_fmt(report.progress_gap, 1)} pts |")
    a(f"| Expenditure–Progress Divergence | {_fmt(report.expenditure_progress_divergence, 1)} pts |")
    a("")

    # --- ML Cost Risk ---
    a("## 3. ML Cost-Overrun Risk")
    a("")
    if report.ml_probability is not None:
        a("| Metric | Value |")
        a("|---|---|")
        a(f"| **Risk Level** | **{report.ml_risk_level}** |")
        a(f"| Probability | {report.ml_probability * 100:.1f}% |")
        a(f"| Model Version | `{report.ml_model_version}` |")
        a(f"| Feature Version | `{report.ml_feature_version}` |")
        a(f"| Leakage Check | {report.ml_leakage_check} |")
        a(f"| Prediction Timestamp | {report.prediction_timestamp} |")
    else:
        a(f"**Prediction Error:** {report.ml_risk_level}")
    a("")

    # --- Revised Cost Interpretation ---
    a("## 4. Revised Cost Interpretation")
    a("")
    a(f"> {report.revised_cost_interpretation}")
    a("")

    # --- Historical Trend ---
    a("## 5. Historical Trend")
    a("")
    a("| Metric | Value |")
    a("|---|---|")
    a(f"| Observations | {report.historical_trend.observation_count} |")
    a(f"| First Observation | {report.historical_trend.first_observation or '—'} |")
    a(f"| Latest Observation | {report.historical_trend.latest_observation or '—'} |")
    a(f"| Recent Trend | {report.recent_trend_label} |")
    a(f"| Monthly Progress Change | {_fmt(report.monthly_progress_change, 2)} pts |")
    a(f"| Progress Slope (3-mo avg) | {_fmt(report.progress_slope, 2)} pts/mo |")
    a(f"| Consecutive Stagnant Months | {report.consecutive_stagnant_months} |")
    a("")

    if report.historical_trend.observations:
        a("### Observation Timeline")
        a("")
        a("| Month | Cumulative Expenditure (₹ Cr) | Physical Progress (%) |")
        a("|---|---|---|")
        for obs in report.historical_trend.observations:
            a(f"| {obs.month} | {_fmt(obs.cumulative_expenditure_crore)} | {_fmt(obs.physical_progress_percent, 1)} |")
        a("")

    if report.historical_trend.events:
        a("### Derived Events")
        a("")
        a("| Month | Type | Description |")
        a("|---|---|---|")
        for ev in report.historical_trend.events:
            a(f"| {ev['month']} | {ev['type']} | {ev['description']} |")
        a("")

    # --- Data Quality ---
    a("## 6. Data Quality")
    a("")
    if report.data_quality.total_issues == 0:
        a("No data-quality issues recorded for this project.")
    else:
        a(f"**Total Issues:** {report.data_quality.total_issues}")
        a("")
        if report.data_quality.issues_by_severity:
            a("| Severity | Count |")
            a("|---|---|")
            for sev, count in sorted(report.data_quality.issues_by_severity.items()):
                a(f"| {sev} | {count} |")
            a("")

        if report.data_quality.issues:
            a("| Type | Severity | Field | Original Value | Action |")
            a("|---|---|---|---|---|")
            for iss in report.data_quality.issues:
                a(f"| {iss['type']} | {iss['severity']} | {iss.get('field') or '—'} | {iss.get('original_value') or '—'} | {iss['action']} |")
            a("")
    a("")

    a("---")
    a("")
    a("*This report was generated deterministically from the ingested data using the Phase 1–4 ")
    a("pipeline. It is reproducible by re-running `python scripts/validate_cohort.py`.*")

    return "\n".join(lines) + "\n"


def _render_portfolio_summary(reports: list[ProjectValidationReport]) -> tuple[str, dict]:
    """Render a portfolio-level markdown summary and JSON data."""
    now_utc = datetime.now(timezone.utc)

    rows = []
    for r in reports:
        rows.append({
            "project_number": r.project_number,
            "project_id": r.project_id,
            "project_name": r.project_name,
            "as_of_date": r.as_of_date,
            "original_cost_crore": r.original_cost_crore,
            "cumulative_expenditure_crore": r.cumulative_expenditure_crore,
            "overall_health": r.overall_health,
            "ml_risk_level": r.ml_risk_level,
            "ml_probability": r.ml_probability,
            "cost_utilisation": r.cost_utilisation,
            "physical_progress": r.physical_progress,
            "expected_progress": r.expected_progress,
            "progress_gap": r.progress_gap,
            "recent_trend": r.recent_trend_label,
            "revised_cost_interpretation": r.revised_cost_interpretation,
        })

    summary_json = {
        "report_generated_at": now_utc.isoformat(),
        "report_version": "phase-5-v1",
        "cohort_size": len(reports),
        "projects": rows,
    }

    lines: list[str] = []
    a = lines.append

    a("# Phase 5 — Five-Project Validation Cohort — Portfolio Summary")
    a("")
    a(f"**Report Generated:** {now_utc.isoformat()}  ")
    a(f"**Cohort Size:** {len(reports)}")
    a("")

    a("## Critical Interpretation")
    a("")
    a("> These five projects currently have **no revised cost** recorded as of their respective")
    a("> observation dates. They are forward-looking early-warning test cases, not confirmed")
    a("> cost-overrun labels. The ML predictions below are **risk estimates**, not outcomes.")
    a(">")
    a("> The system must **not** say: *\"This project will definitely not overrun.\"*  ")
    a("> The system must **not** say: *\"This project will definitely overrun.\"*")
    a("")

    a("## Dashboard")
    a("")
    a("| # | Project | State | Health | ML Risk | Prob. | Progress | Expected | Gap | Trend |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for r in reports:
        prob_str = f"{r.ml_probability * 100:.1f}%" if r.ml_probability is not None else "ERR"
        a(
            f"| {r.project_number:02d} | {r.project_name[:50]} | {r.state or '—'} "
            f"| **{r.overall_health}** | **{r.ml_risk_level}** | {prob_str} "
            f"| {_fmt(r.physical_progress, 1)}% | {_fmt(r.expected_progress, 1)}% "
            f"| {_fmt(r.progress_gap, 1)} | {r.recent_trend_label} |"
        )
    a("")

    a("## Per-Project Reports")
    a("")
    for r in reports:
        folder = f"project_{r.project_number:02d}"
        a(f"- **Project {r.project_number:02d}** — `{r.project_id}` — [{r.project_name}]({folder}/report.md)")
    a("")

    a("---")
    a("")
    a("*Generated by `python scripts/validate_cohort.py`. Reproducible: re-running produces")
    a("identical results for the same ingested data.*")

    return "\n".join(lines) + "\n", summary_json


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    configure_logging()
    log = get_logger("validate_cohort")

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        project_ids = list(INITIAL_VALIDATION_COHORT.keys())
        reports: list[ProjectValidationReport] = []

        for i, project_id in enumerate(project_ids, start=1):
            log.info("generating_report", project_id=project_id, project_number=i)
            report = _generate_project_report(session, project_id, project_number=i)
            reports.append(report)

            # Write per-project output
            project_dir = VALIDATION_DIR / f"project_{i:02d}"
            project_dir.mkdir(parents=True, exist_ok=True)

            # Markdown report
            md = _render_markdown(report)
            (project_dir / "report.md").write_text(md, encoding="utf-8")

            # JSON report (machine-readable)
            report_dict = asdict(report)
            (project_dir / "report.json").write_text(
                json.dumps(report_dict, indent=2, default=str, ensure_ascii=False),
                encoding="utf-8",
            )

            log.info(
                "report_written",
                project_id=project_id,
                project_number=i,
                overall_health=report.overall_health,
                ml_risk_level=report.ml_risk_level,
                ml_probability=round(report.ml_probability, 4) if report.ml_probability else None,
                output_dir=str(project_dir),
            )

        # Portfolio summary
        portfolio_md, portfolio_json = _render_portfolio_summary(reports)
        (VALIDATION_DIR / "portfolio_summary.md").write_text(portfolio_md, encoding="utf-8")
        (VALIDATION_DIR / "portfolio_summary.json").write_text(
            json.dumps(portfolio_json, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )

        log.info(
            "validation_complete",
            cohort_size=len(reports),
            output_dir=str(VALIDATION_DIR),
        )

    finally:
        session.close()


if __name__ == "__main__":
    main()
