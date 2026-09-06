"""Seeds the `validation_cohort` table with the initial 5 forward-looking
early-warning projects (see docs/development_phases.md and SRS section 3).

These are curated by name/project_id, not auto-detected, because cohort
membership is an analyst decision, not a data property.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.validation_cohort import ValidationCohort

INITIAL_VALIDATION_COHORT: dict[str, str] = {
    "617069": "Augmentation of Transformation Capacity at KPS1/KPS2 (POWERGRID) — no revised cost recorded yet.",
    "619054": "Development of Keshod Airport (AAI) — newly added project, no revised cost recorded yet.",
    "616672": "System Strengthening at Koppal-II and Gadag-II (POWERGRID) — no revised cost recorded yet.",
    "617184": "Transmission Scheme for Davanagere/Chitradurga/Bellary REZ (POWERGRID) — no revised cost recorded yet.",
    "617279": "Transmission System for Mahan Energen evacuation (POWERGRID) — no revised cost recorded yet.",
}


def seed_validation_cohort(session: Session, as_of_date: date | None = None) -> int:
    """Idempotent: skips project_ids already present in the cohort. Returns
    the number of newly inserted rows."""
    as_of_date = as_of_date or date.today()
    existing_project_ids = {
        row.project_id for row in session.query(ValidationCohort.project_id).all()
    }

    inserted = 0
    for project_id, reason in INITIAL_VALIDATION_COHORT.items():
        if project_id in existing_project_ids:
            continue
        session.add(
            ValidationCohort(
                project_id=project_id,
                as_of_date=as_of_date,
                reason_selected=reason,
                status="ACTIVE",
                notes="Forward-looking early-warning case, not a confirmed cost-overrun label.",
            )
        )
        inserted += 1

    session.commit()
    return inserted
