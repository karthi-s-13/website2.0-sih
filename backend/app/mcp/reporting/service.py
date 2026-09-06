"""Reporting MCP (Phase 12): decision-ready report generation, reusing
`reporting/builder.py` and `reporting/narrative.py` exactly as the
Coordinator does (via `orchestration.build_full_report` - see that
module's docstring for the one gap it closes without touching
coordinator/). Markdown/PDF rendering are new, pure-deterministic (no LLM)
additions; JSON is the `Report` dataclass as-is.
"""

from __future__ import annotations

import base64
import dataclasses
from datetime import date

from mcp.server.fastmcp import FastMCP

from app.core.config import get_settings
from app.core.errors import AppError
from app.mcp._shared import session_scope
from app.mcp.reporting.markdown import render_markdown
from app.mcp.reporting.orchestration import build_full_report
from app.mcp.reporting.pdf import render_pdf
from app.mcp.reporting.schemas import (
    ExecutiveSummaryResponse,
    JsonReportResponse,
    MarkdownReportResponse,
    PdfReportResponse,
)
from app.repositories.project_repository import get_project
from app.services.health.service import get_project_health
from app.services.prediction.service import predict_cost_overrun
from app.services.reporting.narrative import summarize_report

mcp = FastMCP(
    "reporting",
    instructions="Decision-ready report generation (JSON/Markdown/PDF/executive summary), "
    "reusing the same builder/narrative logic the Coordinator uses.",
)


def _json_safe(value):  # noqa: ANN001, ANN202
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


@mcp.tool()
def generate_json_report(project_id: str, as_of_date: date | None = None) -> JsonReportResponse:
    """Full structured Report (current health, cost-overrun risk, key
    changes, ranked risk drivers, evidence, recommended monitoring actions,
    confidence/data-quality, model versions, human-review flag) as JSON."""
    with session_scope() as session:
        try:
            report = build_full_report(session, project_id, as_of_date)
        except AppError as exc:
            status = "NOT_FOUND" if exc.error_code == "NOT_FOUND" else "ERROR"
            return JsonReportResponse(status=status, project_id=project_id, message=exc.message)

        report_dict = _json_safe(dataclasses.asdict(report))
        return JsonReportResponse(status="OK", project_id=project_id, report=report_dict)


@mcp.tool()
def generate_markdown_report(project_id: str, as_of_date: date | None = None) -> MarkdownReportResponse:
    """The same report as generate_json_report, rendered as Markdown (pure
    deterministic templating, no LLM)."""
    with session_scope() as session:
        try:
            report = build_full_report(session, project_id, as_of_date)
        except AppError as exc:
            status = "NOT_FOUND" if exc.error_code == "NOT_FOUND" else "ERROR"
            return MarkdownReportResponse(status=status, project_id=project_id, message=exc.message)

        return MarkdownReportResponse(status="OK", project_id=project_id, markdown=render_markdown(report))


@mcp.tool()
def generate_pdf_report(project_id: str, as_of_date: date | None = None) -> PdfReportResponse:
    """The same report as generate_json_report, rendered as a PDF (PyMuPDF,
    A4, manual paginated layout) and returned base64-encoded (portable
    across stdio/streamable-http transports)."""
    with session_scope() as session:
        try:
            report = build_full_report(session, project_id, as_of_date)
        except AppError as exc:
            status = "NOT_FOUND" if exc.error_code == "NOT_FOUND" else "ERROR"
            return PdfReportResponse(status=status, project_id=project_id, message=exc.message)

        pdf_bytes = render_pdf(report)
        import fitz

        page_count = fitz.open(stream=pdf_bytes, filetype="pdf").page_count
        return PdfReportResponse(
            status="OK", project_id=project_id, pdf_base64=base64.b64encode(pdf_bytes).decode("ascii"),
            page_count=page_count,
        )


@mcp.tool()
def generate_executive_summary(
    project_id: str,
    as_of_date: date | None = None,
    include_diagnosis: bool = False,
    include_intervention: bool = False,
    include_history: bool = False,
) -> ExecutiveSummaryResponse:
    """A standalone, lightweight executive-summary paragraph - always runs
    Health + best-effort ML prediction; only runs the expensive
    Diagnosis/Intervention/Review+Web pipeline or the History LLM call when
    explicitly requested via the include_* flags. Unlike generate_json_report,
    does not build a full Report."""
    with session_scope() as session:
        project = get_project(session, project_id)
        if project is None:
            return ExecutiveSummaryResponse(status="NOT_FOUND", project_id=project_id)

        as_of = as_of_date or project.latest_observation_month
        if as_of is None:
            return ExecutiveSummaryResponse(status="NOT_FOUND", project_id=project_id, message="no observations")

        health = get_project_health(session, project_id, as_of)

        prediction = None
        try:
            prediction = predict_cost_overrun(session, project_id, as_of)
        except AppError:
            pass

        history = diagnosis = intervention = None
        if include_intervention:
            from app.services.intervention.service import recommend_interventions

            intervention = recommend_interventions(session, project_id, as_of_date=as_of)
            diagnosis = intervention.diagnosis
        elif include_diagnosis:
            from app.services.diagnosis.service import diagnose_project

            diagnosis = diagnose_project(session, project_id, as_of_date=as_of)
        if include_history:
            from app.services.history.service import get_project_history

            history = get_project_history(session, project_id, as_of_date=as_of)

        settings = get_settings()
        narrative = summarize_report(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            project_name=project.project_name,
            health=health,
            prediction=prediction,
            history=history,
            diagnosis=diagnosis,
            intervention=intervention,
        )
        return ExecutiveSummaryResponse(
            status="OK", project_id=project_id, text=narrative.text, source=narrative.source, model=narrative.model
        )
