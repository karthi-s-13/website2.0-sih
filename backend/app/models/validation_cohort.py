from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ValidationCohort(Base):
    """The initial 5-project forward-looking early-warning validation cohort.

    These projects do not yet carry a revised cost as of `as_of_date`. They
    must never be treated as confirmed cost-overrun labels — see
    docs/development_phases.md and SRS section 3.
    """

    __tablename__ = "validation_cohort"

    cohort_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason_selected: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="ACTIVE")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
