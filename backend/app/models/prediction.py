from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Prediction(Base):
    """A logged ML prediction (FR-010, NFR-008 reproducibility: model_version
    and feature_version are always recorded alongside the result)."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), nullable=False)

    prediction_date: Mapped[date] = mapped_column(Date, nullable=False)
    snapshot_month: Mapped[date] = mapped_column(Date, nullable=False)
    input_observation_month: Mapped[date] = mapped_column(Date, nullable=False)

    risk_type: Mapped[str] = mapped_column(String(32), nullable=False)
    probability: Mapped[float] = mapped_column(Numeric(8, 6, asdecimal=False), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)

    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    feature_version: Mapped[str] = mapped_column(String(64), nullable=False)
    leakage_check: Mapped[str] = mapped_column(String(16), nullable=False)

    raw_features_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
