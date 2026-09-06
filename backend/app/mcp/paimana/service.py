"""PAIMANA MCP (Phase 12): read-only access to structured project data
(`projects`, `project_monthly_observations`, `project_milestones`,
`project_events`) - wraps `app.repositories.project_repository` exactly,
adding no new computation of its own.
"""

from __future__ import annotations

from datetime import date

from mcp.server.fastmcp import FastMCP

from app.mcp._shared import session_scope
from app.mcp.paimana.schemas import (
    EventItem,
    EventsResponse,
    MilestoneItem,
    MilestonesResponse,
    ObservationItem,
    ObservationsResponse,
    ProjectResponse,
)
from app.repositories import project_repository

mcp = FastMCP(
    "paimana",
    instructions="Read-only access to PAIMANA structured project data: project master "
    "records, monthly observations, milestones, and derived events.",
)


def _project_response(project, project_id: str) -> ProjectResponse:  # noqa: ANN001
    if project is None:
        return ProjectResponse(status="NOT_FOUND", project_id=project_id)
    return ProjectResponse(
        status="OK",
        project_id=project.project_id,
        project_name=project.project_name,
        agency=project.agency,
        agency_code=project.agency_code,
        ministry=project.ministry,
        sector=project.sector,
        state=project.state,
        original_cost_crore=project.original_cost_crore,
        revised_cost_crore=project.revised_cost_crore,
        date_of_approval=project.date_of_approval,
        start_date=project.start_date,
        original_completion_date=project.original_completion_date,
        revised_completion_date=project.revised_completion_date,
        current_status=project.current_status,
        first_observation_month=project.first_observation_month,
        latest_observation_month=project.latest_observation_month,
        observation_count=project.observation_count,
    )


@mcp.tool()
def get_project(project_id: str) -> ProjectResponse:
    """Fetch a project's master record (name, agency, ministry, sector,
    cost, dates, current status). Returns status="NOT_FOUND" if the
    project_id is not known."""
    with session_scope() as session:
        project = project_repository.get_project(session, project_id)
        return _project_response(project, project_id)


@mcp.tool()
def get_monthly_observations(
    project_id: str, start_date: date | None = None, end_date: date | None = None
) -> ObservationsResponse:
    """Chronological monthly Flash Report observations for a project,
    optionally restricted to [start_date, end_date] (inclusive, by
    observation month). Returns status="NOT_FOUND" if the project doesn't
    exist; status="OK" with an empty list if it exists but has none in
    range."""
    with session_scope() as session:
        project = project_repository.get_project(session, project_id)
        if project is None:
            return ObservationsResponse(status="NOT_FOUND", project_id=project_id, count=0, observations=[])

        observations = project_repository.get_chronological_observations(session, project_id)
        if start_date is not None:
            observations = [o for o in observations if o.observation_month >= start_date]
        if end_date is not None:
            observations = [o for o in observations if o.observation_month <= end_date]

        items = [
            ObservationItem(
                observation_month=o.observation_month,
                report_label=o.report_label,
                record_type=o.record_type,
                date_of_approval=o.date_of_approval,
                start_date=o.start_date,
                target_completion_date=o.target_completion_date,
                revised_completion_date=o.revised_completion_date,
                original_cost_crore=o.original_cost_crore,
                revised_cost_crore=o.revised_cost_crore,
                cumulative_expenditure_crore=o.cumulative_expenditure_crore,
                physical_progress_percent=o.physical_progress_percent,
                notes=o.notes,
                source_file=o.source_file,
                source_row=o.source_row,
            )
            for o in observations
        ]
        return ObservationsResponse(status="OK", project_id=project_id, count=len(items), observations=items)


@mcp.tool()
def get_milestones(project_id: str) -> MilestonesResponse:
    """Milestones for a project. The real Flash Report source data has no
    milestone fields (Phase 1/4's own finding) - `unavailable=True` and an
    empty list is the honest, expected result for essentially every real
    project, never fabricated."""
    with session_scope() as session:
        project = project_repository.get_project(session, project_id)
        if project is None:
            return MilestonesResponse(
                status="NOT_FOUND", project_id=project_id, count=0, unavailable=True, milestones=[]
            )

        milestones = project_repository.get_milestones(session, project_id)
        items = [
            MilestoneItem(
                milestone_name=m.milestone_name,
                planned_date=m.planned_date,
                actual_date=m.actual_date,
                status=m.status,
            )
            for m in milestones
        ]
        return MilestonesResponse(
            status="OK", project_id=project_id, count=len(items), unavailable=len(items) == 0, milestones=items
        )


@mcp.tool()
def get_project_events(project_id: str, event_type: str | None = None) -> EventsResponse:
    """Deterministically-derived timeline events for a project (e.g. a
    revised cost or completion date first appearing), optionally filtered
    to an exact `event_type` match."""
    with session_scope() as session:
        project = project_repository.get_project(session, project_id)
        if project is None:
            return EventsResponse(status="NOT_FOUND", project_id=project_id, count=0, events=[])

        events = project_repository.get_project_events(session, project_id)
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]

        items = [
            EventItem(
                event_month=e.event_month,
                event_type=e.event_type,
                description=e.description,
                previous_value=e.previous_value,
                new_value=e.new_value,
            )
            for e in events
        ]
        return EventsResponse(status="OK", project_id=project_id, count=len(items), events=items)
