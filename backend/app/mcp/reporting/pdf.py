"""Deterministic PDF rendering of a Report (Phase 12 Reporting MCP's
generate_pdf_report), via PyMuPDF (`fitz`) - already a Phase 7 dependency
(PDF text extraction), reused here for PDF authoring instead of adding a
new PDF library (reportlab/fpdf2/weasyprint).

Manual line-by-line layout with a running y cursor (not `insert_textbox`)
for fully deterministic, unit-testable pagination: a section can split
mid-paragraph cleanly across pages rather than being silently truncated by
a fixed textbox rect. Tables (drivers/evidence/actions) are fixed-width
plain-text rows - no PDF table-flowable library needed.
"""

from __future__ import annotations

import textwrap

import fitz

from app.services.reporting.builder import Report

PAGE_WIDTH, PAGE_HEIGHT = fitz.paper_size("a4")
MARGIN = 50
USABLE_WIDTH = PAGE_WIDTH - 2 * MARGIN
LINE_HEIGHT = 14
TITLE_SIZE = 16
HEADING_SIZE = 13
BODY_SIZE = 10
WRAP_WIDTH = 95


class _Writer:
    def __init__(self, doc: fitz.Document) -> None:
        self.doc = doc
        self.page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        self.y = MARGIN

    def _ensure_room(self) -> None:
        if self.y + LINE_HEIGHT > PAGE_HEIGHT - MARGIN:
            self.page = self.doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            self.y = MARGIN

    def line(self, text: str, *, size: float = BODY_SIZE, font: str = "helv") -> None:
        self._ensure_room()
        self.page.insert_text((MARGIN, self.y), text, fontsize=size, fontname=font)
        self.y += LINE_HEIGHT

    def title(self, text: str) -> None:
        self.line(text, size=TITLE_SIZE, font="hebo")

    def heading(self, text: str) -> None:
        self.y += 4
        self.line(text, size=HEADING_SIZE, font="hebo")

    def paragraph(self, text: str) -> None:
        if not text:
            self.line("(none)")
            return
        for raw_line in text.splitlines() or [""]:
            wrapped = textwrap.wrap(raw_line, width=WRAP_WIDTH) or [""]
            for wrapped_line in wrapped:
                self.line(wrapped_line)

    def bullets(self, items: list[str]) -> None:
        if not items:
            self.line("(none)")
            return
        for item in items:
            for i, wrapped_line in enumerate(textwrap.wrap(item, width=WRAP_WIDTH - 2) or [""]):
                self.line(("- " if i == 0 else "  ") + wrapped_line)

    def table(self, header: str, rows: list[str]) -> None:
        self.line(header, font="hebo")
        if not rows:
            self.line("(none)")
            return
        for row in rows:
            self.line(row)


def render_pdf(report: Report) -> bytes:
    doc = fitz.open()
    w = _Writer(doc)

    w.title(f"Project Report: {report.project_name} ({report.project_id})")
    w.line(f"Generated {report.as_of_date.isoformat()} - trace {report.trace_id}")

    w.heading("Executive Summary")
    w.paragraph(report.executive_summary)

    w.heading("Current Health")
    if report.current_health is None:
        w.line("Not computed for this report.")
    else:
        w.bullets([f"{k}: {v}" for k, v in report.current_health.items()])

    w.heading("Cost-Overrun Risk")
    if report.cost_overrun_risk is None:
        w.line("Not computed for this report.")
    else:
        w.bullets([f"{k}: {v}" for k, v in report.cost_overrun_risk.items()])

    w.heading("Time-Overrun Risk")
    if report.time_overrun_risk is None:
        w.line("Not computed for this report.")
    else:
        w.line(f"{report.time_overrun_risk['status']} - {report.time_overrun_risk['reason']}")

    w.heading("Key Changes")
    w.bullets(report.key_changes)

    w.heading("Top Risk Drivers")
    w.table(
        f"{'Rank':<5}{'Driver':<42}{'Severity':<10}Evidence",
        [
            f"{d['rank']:<5}{d['driver'][:40]:<42}{d['severity']:<10}{d['evidence_count']}"
            for d in report.top_risk_drivers
        ],
    )

    w.heading("Evidence")
    w.table(
        f"{'Category':<26}{'Source':<20}Description",
        [
            f"{e['category'][:24]:<26}{e['source'][:18]:<20}{e['description'][:60].replace(chr(10), ' ')}"
            for e in report.evidence
        ],
    )

    w.heading("Recommended Monitoring Actions")
    w.table(
        f"{'Priority':<10}{'Type':<24}Action",
        [
            f"{a['priority']:<10}{a['action_type'][:22]:<24}{a['action'][:70]}"
            for a in report.recommended_monitoring_actions
        ],
    )

    w.heading("Confidence & Data Quality")
    w.bullets([f"{k}: {v}" for k, v in {**report.confidence, **report.data_quality}.items()])

    w.heading("Model Versions")
    w.bullets([f"{k}: {v}" for k, v in report.model_versions.items()])

    w.heading("Human Review")
    w.line(f"Required: {report.human_review_required}")
    w.line(f"Reason: {report.human_review_reason or 'N/A'}")

    return doc.tobytes()
