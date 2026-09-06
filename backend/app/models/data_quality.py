from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RawObservation(Base):
    """Verbatim copy of every source row, before any cleaning/normalization.

    Preserves the original raw data (Phase 1 requirement) independently of the
    untouched source CSVs, so lineage is queryable from the database too.
    Every column is stored as the original string exactly as read from the
    CSV cell (empty string, "-", "NA", etc. are kept as-is, not normalized).
    """

    __tablename__ = "raw_observations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_file: Mapped[str] = mapped_column(Text, nullable=False)
    source_row: Mapped[int] = mapped_column(nullable=False)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DataQualityIssue(Base):
    """A recorded data-quality finding. Bad records are never silently
    dropped — they are cleaned/quarantined and the action taken is recorded
    here alongside the original and corrected values."""

    __tablename__ = "data_quality_issues"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    issue_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)  # INFO | WARNING | ERROR
    table_name: Mapped[str] = mapped_column(Text, nullable=False)
    record_id: Mapped[str] = mapped_column(Text, nullable=False)
    field: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_row: Mapped[int | None] = mapped_column(nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
