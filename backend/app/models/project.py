from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Project(Base):
    """Canonical project master record (source of truth: latest known values).

    Fields not present in the source Flash Report data (e.g. ministry, sector)
    are left nullable rather than fabricated (see DR-001 vs. actual schema).
    """

    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_name: Mapped[str] = mapped_column(Text, nullable=False)
    agency: Mapped[str | None] = mapped_column(Text, nullable=True)
    agency_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ministry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str | None] = mapped_column(String(128), nullable=True)

    original_cost_crore: Mapped[float | None] = mapped_column(Numeric(14, 2, asdecimal=False), nullable=True)
    revised_cost_crore: Mapped[float | None] = mapped_column(Numeric(14, 2, asdecimal=False), nullable=True)

    date_of_approval: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    original_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    revised_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    current_status: Mapped[str | None] = mapped_column(String(64), nullable=True)

    first_observation_month: Mapped[date | None] = mapped_column(Date, nullable=True)
    latest_observation_month: Mapped[date | None] = mapped_column(Date, nullable=True)
    observation_count: Mapped[int] = mapped_column(default=0, nullable=False)

    source_files: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    observations: Mapped[list["ProjectMonthlyObservation"]] = relationship(
        back_populates="project", order_by="ProjectMonthlyObservation.observation_month"
    )
    milestones: Mapped[list["ProjectMilestone"]] = relationship(back_populates="project")
    events: Mapped[list["ProjectEvent"]] = relationship(
        back_populates="project", order_by="ProjectEvent.event_month"
    )


class ProjectMonthlyObservation(Base):
    """One cleaned monthly Flash Report record for a project (DR-002 / DR-003).

    Cost and target/revised-completion-date fields are captured per observation
    (not just once on `projects`) because they are themselves point-in-time
    facts that can change from one report edition to the next.
    """

    __tablename__ = "project_monthly_observations"
    __table_args__ = (
        UniqueConstraint("project_id", "observation_month", name="uq_project_observation_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), nullable=False)
    observation_month: Mapped[date] = mapped_column(Date, nullable=False)

    report_label: Mapped[str] = mapped_column(String(32), nullable=False)
    record_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    date_of_approval: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    revised_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    original_cost_crore: Mapped[float | None] = mapped_column(Numeric(14, 2, asdecimal=False), nullable=True)
    revised_cost_crore: Mapped[float | None] = mapped_column(Numeric(14, 2, asdecimal=False), nullable=True)
    cumulative_expenditure_crore: Mapped[float | None] = mapped_column(
        Numeric(14, 2, asdecimal=False), nullable=True
    )
    physical_progress_percent: Mapped[float | None] = mapped_column(
        Numeric(6, 2, asdecimal=False), nullable=True
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    source_row: Mapped[int] = mapped_column(nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="observations")


class ProjectMilestone(Base):
    """Milestone records (FR-006/DR-002). Populated only when the source data
    actually contains milestone information — never fabricated."""

    __tablename__ = "project_milestones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), nullable=False)
    milestone_name: Mapped[str] = mapped_column(Text, nullable=False)
    planned_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_row: Mapped[int | None] = mapped_column(nullable=True)

    project: Mapped["Project"] = relationship(back_populates="milestones")


class ProjectEvent(Base):
    """Deterministically derived timeline events (FR-006/FR-007), e.g. a
    revised cost or revised completion date first appearing in the record.

    Events are derived only from observed field transitions — never inferred
    or fabricated content.
    """

    __tablename__ = "project_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), nullable=False)
    event_month: Mapped[date] = mapped_column(Date, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    previous_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="events")
