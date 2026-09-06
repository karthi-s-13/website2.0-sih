from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Status = Literal["OK", "NOT_FOUND", "ERROR"]


class JsonReportResponse(BaseModel):
    status: Status
    project_id: str
    report: dict | None = None
    message: str | None = None


class MarkdownReportResponse(BaseModel):
    status: Status
    project_id: str
    markdown: str | None = None
    message: str | None = None


class PdfReportResponse(BaseModel):
    status: Status
    project_id: str
    pdf_base64: str | None = None
    page_count: int | None = None
    message: str | None = None


class ExecutiveSummaryResponse(BaseModel):
    status: Status
    project_id: str
    text: str | None = None
    source: Literal["LLM", "DETERMINISTIC_FALLBACK"] | None = None
    model: str | None = None
    message: str | None = None
