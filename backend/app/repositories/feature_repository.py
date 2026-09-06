from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feature import ProjectMonthlyFeature


def get_feature_history(
    session: Session, project_id: str, feature_version: str
) -> list[ProjectMonthlyFeature]:
    stmt = (
        select(ProjectMonthlyFeature)
        .where(
            ProjectMonthlyFeature.project_id == project_id,
            ProjectMonthlyFeature.feature_version == feature_version,
        )
        .order_by(ProjectMonthlyFeature.snapshot_month)
    )
    return list(session.execute(stmt).scalars().all())


def get_feature_row(
    session: Session, project_id: str, snapshot_month: date, feature_version: str
) -> ProjectMonthlyFeature | None:
    stmt = select(ProjectMonthlyFeature).where(
        ProjectMonthlyFeature.project_id == project_id,
        ProjectMonthlyFeature.snapshot_month == snapshot_month,
        ProjectMonthlyFeature.feature_version == feature_version,
    )
    return session.execute(stmt).scalars().first()
