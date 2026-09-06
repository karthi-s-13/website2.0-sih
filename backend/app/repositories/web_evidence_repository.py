from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.web_evidence import WebEvidence


def store_evidence(session: Session, items: list[WebEvidence]) -> None:
    for item in items:
        session.merge(item)
    session.commit()


def get_evidence_for_project(session: Session, project_id: str) -> list[WebEvidence]:
    stmt = (
        select(WebEvidence)
        .where(WebEvidence.project_id == project_id)
        .order_by(WebEvidence.retrieved_at.desc())
    )
    return list(session.execute(stmt).scalars().all())
