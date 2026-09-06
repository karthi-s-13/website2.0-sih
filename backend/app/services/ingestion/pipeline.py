"""Orchestrates Flash Report ingestion: raw preservation -> normalization ->
data-quality validation -> clean table upsert -> event derivation.

Safe to re-run: raw rows, projects, and observations are upserted by natural
key; derived events are recomputed from scratch per project on each run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.data_quality import DataQualityIssue, RawObservation
from app.models.project import Project, ProjectEvent, ProjectMonthlyObservation
from app.services.ingestion.events import derive_events
from app.services.ingestion.quality import (
    check_monotonic_sequences,
    deduplicate_project_month,
    validate_ranges,
)
from app.services.ingestion.schema import NormalizedObservation, RowIssue, normalize_row, read_raw_rows


@dataclass
class IngestionSummary:
    files_processed: int = 0
    raw_rows_seen: int = 0
    raw_rows_newly_stored: int = 0
    projects_upserted: int = 0
    observations_upserted: int = 0
    observations_quarantined: int = 0
    events_created: int = 0
    issues_by_severity: dict[str, int] = field(default_factory=lambda: {"ERROR": 0, "WARNING": 0, "INFO": 0})


def _record_id_for(obs: NormalizedObservation) -> str:
    if obs.project_id and obs.observation_month:
        return f"{obs.project_id}:{obs.observation_month.isoformat()}"
    if obs.project_id:
        return obs.project_id
    return f"row:{obs.source_file}:{obs.source_row}"


def _store_issue(session: Session, summary: IngestionSummary, obs: NormalizedObservation, issue: RowIssue) -> None:
    session.add(
        DataQualityIssue(
            issue_type=issue.issue_type,
            severity=issue.severity,
            table_name="project_monthly_observations",
            record_id=_record_id_for(obs),
            field=issue.field,
            original_value=issue.original_value,
            corrected_value=None,
            action="FLAGGED_NOT_CORRECTED",
            source_file=obs.source_file,
            source_row=obs.source_row,
        )
    )
    summary.issues_by_severity[issue.severity] = summary.issues_by_severity.get(issue.severity, 0) + 1


def _store_raw_row(session: Session, summary: IngestionSummary, obs: NormalizedObservation) -> None:
    summary.raw_rows_seen += 1
    exists = (
        session.query(RawObservation.id)
        .filter_by(source_file=obs.source_file, source_row=obs.source_row)
        .first()
    )
    if exists:
        return
    session.add(
        RawObservation(
            source_file=obs.source_file,
            source_row=obs.source_row,
            raw_json=json.dumps(obs.raw_row, ensure_ascii=False),
        )
    )
    summary.raw_rows_newly_stored += 1


def _upsert_project(session: Session, project_id: str, kept: list[NormalizedObservation]) -> None:
    earliest, latest = kept[0], kept[-1]
    project = session.get(Project, project_id)
    if project is None:
        project = Project(project_id=project_id)
        session.add(project)

    project.project_name = latest.project_name or earliest.project_name
    project.agency = latest.agency or earliest.agency
    project.agency_code = latest.agency_code or earliest.agency_code
    project.state = latest.state or earliest.state

    project.original_cost_crore = earliest.original_cost_crore
    project.revised_cost_crore = latest.revised_cost_crore

    project.date_of_approval = earliest.date_of_approval
    project.start_date = earliest.start_date
    project.original_completion_date = earliest.target_completion_date
    project.revised_completion_date = latest.revised_completion_date

    project.current_status = latest.record_type

    project.first_observation_month = earliest.observation_month
    project.latest_observation_month = latest.observation_month
    project.observation_count = len(kept)

    source_files = sorted({obs.source_file for obs in kept})
    project.source_files = ", ".join(source_files)


def _upsert_observation(session: Session, obs: NormalizedObservation) -> None:
    existing = (
        session.query(ProjectMonthlyObservation)
        .filter_by(project_id=obs.project_id, observation_month=obs.observation_month)
        .first()
    )
    row = existing or ProjectMonthlyObservation(
        project_id=obs.project_id, observation_month=obs.observation_month
    )
    row.report_label = obs.report_label
    row.record_type = obs.record_type
    row.date_of_approval = obs.date_of_approval
    row.start_date = obs.start_date
    row.target_completion_date = obs.target_completion_date
    row.revised_completion_date = obs.revised_completion_date
    row.original_cost_crore = obs.original_cost_crore
    row.revised_cost_crore = obs.revised_cost_crore
    row.cumulative_expenditure_crore = obs.cumulative_expenditure_crore
    row.physical_progress_percent = obs.physical_progress_percent
    row.notes = obs.notes
    row.source_file = obs.source_file
    row.source_row = obs.source_row
    if existing is None:
        session.add(row)


def ingest_files(session: Session, file_paths: list[Path]) -> IngestionSummary:
    summary = IngestionSummary()
    all_observations: list[NormalizedObservation] = []

    # Quality issues are fully re-derived from these files on every run; clear
    # any previously recorded issues for them first so re-running ingestion
    # (e.g. a repeated monthly pipeline run) does not pile up duplicates.
    file_names = [path.name for path in file_paths]
    if file_names:
        session.query(DataQualityIssue).filter(DataQualityIssue.source_file.in_(file_names)).delete(
            synchronize_session=False
        )

    for path in file_paths:
        summary.files_processed += 1
        for i, raw_row in enumerate(read_raw_rows(path), start=1):
            obs = normalize_row(raw_row, source_file=path.name, source_row=i)
            obs.issues.extend(validate_ranges(obs))
            _store_raw_row(session, summary, obs)
            all_observations.append(obs)

    by_project: dict[str, list[NormalizedObservation]] = {}
    for obs in all_observations:
        if obs.project_id is None or obs.observation_month is None:
            summary.observations_quarantined += 1
            for issue in obs.issues:
                _store_issue(session, summary, obs, issue)
            continue
        by_project.setdefault(obs.project_id, []).append(obs)

    for project_id, observations in by_project.items():
        for obs in observations:
            for issue in obs.issues:
                _store_issue(session, summary, obs, issue)

        kept, dropped = deduplicate_project_month(observations)
        for obs, issue in dropped:
            summary.observations_quarantined += 1
            _store_issue(session, summary, obs, issue)

        kept.sort(key=lambda o: o.observation_month)

        for obs, issue in check_monotonic_sequences(kept):
            _store_issue(session, summary, obs, issue)

        _upsert_project(session, project_id, kept)
        summary.projects_upserted += 1

        for obs in kept:
            _upsert_observation(session, obs)
            summary.observations_upserted += 1

        session.query(ProjectEvent).filter_by(project_id=project_id).delete()
        for derived in derive_events(kept):
            session.add(
                ProjectEvent(
                    project_id=project_id,
                    event_month=derived.event_month,
                    event_type=derived.event_type,
                    description=derived.description,
                    previous_value=derived.previous_value,
                    new_value=derived.new_value,
                )
            )
            summary.events_created += 1

    session.commit()
    return summary


def ingest_directory(session: Session, directory: Path, pattern: str = "*.csv") -> IngestionSummary:
    return ingest_files(session, sorted(directory.glob(pattern)))
