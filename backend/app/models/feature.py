from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class FeatureVersion(Base):
    """Registry of feature-set versions (DR-004/DR-007). A new version must be
    created whenever a formula or the rolling-window size changes, so every
    stored feature row is reproducible from its (feature_version, inputs)."""

    __tablename__ = "feature_versions"

    version: Mapped[str] = mapped_column(String(32), primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rolling_window_months: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_progress_method: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProjectMonthlyFeature(Base):
    """One point-in-time feature vector for (project_id, snapshot_month,
    feature_version). Computed only from observations with
    observation_month <= snapshot_month (see services/features/pipeline.py).
    """

    __tablename__ = "project_monthly_features"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "snapshot_month", "feature_version", name="uq_project_snapshot_feature_version"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), nullable=False)
    snapshot_month: Mapped[date] = mapped_column(Date, nullable=False)
    feature_version: Mapped[str] = mapped_column(ForeignKey("feature_versions.version"), nullable=False)

    cost_utilisation: Mapped[float | None] = mapped_column(Numeric(10, 6, asdecimal=False), nullable=True)
    expenditure_growth: Mapped[float | None] = mapped_column(Numeric(10, 6, asdecimal=False), nullable=True)
    monthly_expenditure_growth: Mapped[float | None] = mapped_column(
        Numeric(14, 4, asdecimal=False), nullable=True
    )
    schedule_utilisation: Mapped[float | None] = mapped_column(Numeric(10, 6, asdecimal=False), nullable=True)
    physical_progress: Mapped[float | None] = mapped_column(Numeric(6, 2, asdecimal=False), nullable=True)
    expected_progress: Mapped[float | None] = mapped_column(Numeric(10, 4, asdecimal=False), nullable=True)
    progress_gap: Mapped[float | None] = mapped_column(Numeric(10, 4, asdecimal=False), nullable=True)
    expenditure_progress_divergence: Mapped[float | None] = mapped_column(
        Numeric(10, 6, asdecimal=False), nullable=True
    )
    monthly_progress_change: Mapped[float | None] = mapped_column(
        Numeric(10, 4, asdecimal=False), nullable=True
    )
    rolling_progress_change: Mapped[float | None] = mapped_column(
        Numeric(10, 4, asdecimal=False), nullable=True
    )
    rolling_expenditure_change: Mapped[float | None] = mapped_column(
        Numeric(14, 4, asdecimal=False), nullable=True
    )
    project_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remaining_schedule_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remaining_cost_budget_crore: Mapped[float | None] = mapped_column(
        Numeric(14, 4, asdecimal=False), nullable=True
    )

    input_observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
