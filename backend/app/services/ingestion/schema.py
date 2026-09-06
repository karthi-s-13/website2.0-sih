"""Normalizes raw Flash Report CSV rows (in whichever of the two observed
column layouts) into a single canonical `NormalizedObservation`.

Two layouts have been observed in the real data:

  - "report_month" layout: report_month,project_name,agency,project_code,state,
    date_of_approval,start_date,original_target_doc,revised_doc,
    original_cost_crore,revised_cost_crore,cumulative_expenditure_crore,
    physical_progress_percent,<notes|record_status>

  - "edition" layout: edition,record_type,project_name,agency,project_code,state,
    date_of_approval,start_date,original_target_doc,revised_doc,
    original_cost_crore,revised_cost_crore,cumulative_expenditure_crore,
    physical_progress_percent,notes

Do not assume either layout — detect it from the actual header of each file.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from app.services.ingestion.parsing import (
    clean_str,
    extract_agency_code,
    parse_edition_month,
    parse_month_year,
    parse_numeric,
    parse_report_month,
)

NOTES_COLUMN_ALIASES = ("notes", "record_status")


@dataclass
class RowIssue:
    issue_type: str
    severity: str  # INFO | WARNING | ERROR
    field: str | None
    original_value: str | None
    message: str


@dataclass
class NormalizedObservation:
    source_file: str
    source_row: int
    raw_row: dict[str, str]

    report_label: str | None = None
    record_type: str | None = None
    observation_month: date | None = None

    project_id: str | None = None
    project_name: str | None = None
    agency: str | None = None
    agency_code: str | None = None
    state: str | None = None

    date_of_approval: date | None = None
    start_date: date | None = None
    target_completion_date: date | None = None
    revised_completion_date: date | None = None

    original_cost_crore: float | None = None
    revised_cost_crore: float | None = None
    cumulative_expenditure_crore: float | None = None
    physical_progress_percent: float | None = None

    notes: str | None = None

    issues: list[RowIssue] = field(default_factory=list)


def read_raw_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [row for row in reader if any((v or "").strip() for v in row.values())]


def _parse_optional_date(
    obs: NormalizedObservation, raw: dict[str, str], raw_key: str, target_attr: str, field_label: str
) -> None:
    raw_value = raw.get(raw_key)
    try:
        parsed = parse_month_year(raw_value)
    except ValueError as exc:
        obs.issues.append(
            RowIssue("UNPARSEABLE_DATE", "WARNING", field_label, raw_value, str(exc))
        )
        return
    setattr(obs, target_attr, parsed)


def _parse_optional_numeric(
    obs: NormalizedObservation, raw: dict[str, str], raw_key: str, target_attr: str, field_label: str
) -> None:
    raw_value = raw.get(raw_key)
    try:
        parsed = parse_numeric(raw_value)
    except ValueError as exc:
        obs.issues.append(
            RowIssue("UNPARSEABLE_NUMERIC", "WARNING", field_label, raw_value, str(exc))
        )
        return
    setattr(obs, target_attr, parsed)


def normalize_row(raw: dict[str, str], source_file: str, source_row: int) -> NormalizedObservation:
    obs = NormalizedObservation(source_file=source_file, source_row=source_row, raw_row=dict(raw))

    if "report_month" in raw:
        obs.report_label = clean_str(raw.get("report_month"))
        try:
            obs.observation_month = parse_report_month(raw.get("report_month"))
        except ValueError as exc:
            obs.issues.append(
                RowIssue("INVALID_DATE", "ERROR", "report_month", raw.get("report_month"), str(exc))
            )
    elif "edition" in raw:
        obs.report_label = clean_str(raw.get("edition"))
        obs.record_type = clean_str(raw.get("record_type"))
        try:
            obs.observation_month = parse_edition_month(raw.get("edition"))
        except ValueError as exc:
            obs.issues.append(
                RowIssue("INVALID_DATE", "ERROR", "edition", raw.get("edition"), str(exc))
            )
    else:
        obs.issues.append(
            RowIssue(
                "MISSING_REQUIRED_FIELD",
                "ERROR",
                "observation_month",
                None,
                "row has neither a report_month nor an edition column",
            )
        )

    obs.project_id = clean_str(raw.get("project_code"))
    obs.project_name = clean_str(raw.get("project_name"))
    obs.agency = clean_str(raw.get("agency"))
    obs.agency_code = extract_agency_code(obs.agency)
    obs.state = clean_str(raw.get("state"))

    _parse_optional_date(obs, raw, "date_of_approval", "date_of_approval", "date_of_approval")
    _parse_optional_date(obs, raw, "start_date", "start_date", "start_date")
    _parse_optional_date(obs, raw, "original_target_doc", "target_completion_date", "original_target_doc")
    _parse_optional_date(obs, raw, "revised_doc", "revised_completion_date", "revised_doc")

    _parse_optional_numeric(obs, raw, "original_cost_crore", "original_cost_crore", "original_cost_crore")
    _parse_optional_numeric(obs, raw, "revised_cost_crore", "revised_cost_crore", "revised_cost_crore")
    _parse_optional_numeric(
        obs, raw, "cumulative_expenditure_crore", "cumulative_expenditure_crore", "cumulative_expenditure_crore"
    )
    _parse_optional_numeric(
        obs, raw, "physical_progress_percent", "physical_progress_percent", "physical_progress_percent"
    )

    for notes_key in NOTES_COLUMN_ALIASES:
        if notes_key in raw:
            obs.notes = clean_str(raw.get(notes_key))
            break

    if obs.project_id is None:
        obs.issues.append(
            RowIssue("MISSING_REQUIRED_FIELD", "ERROR", "project_code", raw.get("project_code"), "project_id is null")
        )
    if obs.project_name is None:
        obs.issues.append(
            RowIssue("MISSING_REQUIRED_FIELD", "ERROR", "project_name", raw.get("project_name"), "project_name is null")
        )

    return obs
