from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.data_quality import DataQualityIssue
from app.models.project import Project, ProjectEvent, ProjectMilestone, ProjectMonthlyObservation


def get_project(session: Session, project_id: str) -> Project | None:
    return session.get(Project, project_id)


def get_milestones(session: Session, project_id: str) -> list[ProjectMilestone]:
    stmt = (
        select(ProjectMilestone)
        .where(ProjectMilestone.project_id == project_id)
        .order_by(ProjectMilestone.planned_date.is_(None), ProjectMilestone.planned_date)
    )
    return list(session.execute(stmt).scalars().all())


def get_chronological_observations(session: Session, project_id: str) -> list[ProjectMonthlyObservation]:
    stmt = (
        select(ProjectMonthlyObservation)
        .where(ProjectMonthlyObservation.project_id == project_id)
        .order_by(ProjectMonthlyObservation.observation_month)
    )
    return list(session.execute(stmt).scalars().all())


def get_project_events(session: Session, project_id: str) -> list[ProjectEvent]:
    stmt = (
        select(ProjectEvent)
        .where(ProjectEvent.project_id == project_id)
        .order_by(ProjectEvent.event_month)
    )
    return list(session.execute(stmt).scalars().all())


def get_data_quality_issues_for_project(session: Session, project_id: str) -> list[DataQualityIssue]:
    stmt = select(DataQualityIssue).where(DataQualityIssue.record_id.startswith(f"{project_id}:"))
    return list(session.execute(stmt).scalars().all())


def list_all_projects(session: Session) -> list[Project]:
    return list(session.execute(select(Project).order_by(Project.project_id)).scalars().all())
