"""Deterministic Markdown rendering of a Report (Phase 12 Reporting MCP's
generate_markdown_report). No LLM here - pure templating off already-built
fields, mirroring the section order/headings `pdf.py` also uses so the two
outputs stay consistent."""

from __future__ import annotations

from app.services.reporting.builder import Report

NOT_COMPUTED = "_Not computed for this report._"


def _bullet_list(lines: list[str]) -> str:
    return "\n".join(f"- {line}" for line in lines) if lines else NOT_COMPUTED


def _health_section(health: dict | None) -> str:
    if health is None:
        return NOT_COMPUTED
    return _bullet_list(
        [
            f"**Overall health:** {health['overall_health']}",
            f"**Cost utilisation:** {health['cost_utilisation']}",
            f"**Schedule utilisation:** {health['schedule_utilisation']}",
            f"**Physical progress:** {health['physical_progress']}",
            f"**Expected progress:** {health['expected_progress']}",
            f"**Progress gap:** {health['progress_gap']}",
            f"**Expenditure/progress divergence:** {health['expenditure_progress_divergence']}",
            f"**Recent trend:** {health['recent_trend']}",
        ]
    )


def _cost_risk_section(cost_overrun_risk: dict | None) -> str:
    if cost_overrun_risk is None:
        return NOT_COMPUTED
    return _bullet_list(
        [
            f"**Probability:** {cost_overrun_risk['probability']}",
            f"**Risk level:** {cost_overrun_risk['risk_level']}",
            f"**Model version:** {cost_overrun_risk['model_version']}",
        ]
    )


def _time_risk_section(time_overrun_risk: dict | None) -> str:
    if time_overrun_risk is None:
        return NOT_COMPUTED
    return f"**Status:** {time_overrun_risk['status']} - {time_overrun_risk['reason']}"


def _drivers_table(drivers: list[dict]) -> str:
    if not drivers:
        return "_No drivers identified._"
    rows = ["| Rank | Driver | Severity | Evidence Count |", "|---|---|---|---|"]
    rows += [f"| {d['rank']} | {d['driver']} | {d['severity']} | {d['evidence_count']} |" for d in drivers]
    return "\n".join(rows)


def _evidence_table(evidence: list[dict]) -> str:
    if not evidence:
        return "_No evidence recorded._"
    rows = ["| Category | Source | Description | Confidence |", "|---|---|---|---|"]
    for e in evidence:
        description = e["description"][:200].replace("\n", " ").replace("|", "/")
        rows.append(f"| {e['category']} | {e['source']} | {description} | {e['confidence']} |")
    return "\n".join(rows)


def _actions_table(actions: list[dict]) -> str:
    if not actions:
        return "_No recommended actions._"
    rows = ["| Priority | Action Type | Action |", "|---|---|---|"]
    rows += [f"| {a['priority']} | {a['action_type']} | {a['action']} |" for a in actions]
    return "\n".join(rows)


def render_markdown(report: Report) -> str:
    lines = [
        f"# Project Report: {report.project_name} ({report.project_id})",
        f"_Generated {report.as_of_date.isoformat()} - trace {report.trace_id}, "
        f"analysis {report.analysis_id}_",
        "",
        "## Executive Summary",
        report.executive_summary,
        "",
        "## Current Health",
        _health_section(report.current_health),
        "",
        "## Cost-Overrun Risk",
        _cost_risk_section(report.cost_overrun_risk),
        "",
        "## Time-Overrun Risk",
        _time_risk_section(report.time_overrun_risk),
        "",
        "## Key Changes",
        _bullet_list(report.key_changes),
        "",
        "## Top Risk Drivers",
        _drivers_table(report.top_risk_drivers),
        "",
        "## Evidence",
        _evidence_table(report.evidence),
        "",
        "## Recommended Monitoring Actions",
        _actions_table(report.recommended_monitoring_actions),
        "",
        "## Confidence & Data Quality",
        _bullet_list([f"**{k}:** {v}" for k, v in {**report.confidence, **report.data_quality}.items()]),
        "",
        "## Model Versions",
        _bullet_list([f"**{k}:** {v}" for k, v in report.model_versions.items()]),
        "",
        "## Human Review",
        f"**Required:** {report.human_review_required}  \n**Reason:** {report.human_review_reason or 'N/A'}",
    ]
    return "\n".join(lines)
