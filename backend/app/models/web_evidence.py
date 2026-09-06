from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class WebEvidence(Base):
    """One verified external (web) finding about a project (Phase 8 Web
    Intelligence Agent - SRS/spec section 20's "Evidence Store" stage).

    Mirrors the Evidence object shape from spec section 22, adapted for a
    web source (a URL instead of a document/page). `source_quality` is
    derived from `trust_tier` (spec section 21) so downstream consumers
    (the future Phase 9 Evidence Agent) can weight or discard low-trust
    findings without re-deriving trust themselves.
    """

    __tablename__ = "web_evidence"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), nullable=False)

    source_type: Mapped[str] = mapped_column(String(16), nullable=False, default="WEB")
    topic: Mapped[str] = mapped_column(String(64), nullable=False)
    query_used: Mapped[str] = mapped_column(Text, nullable=False)

    source: Mapped[str] = mapped_column(Text, nullable=False)  # publisher / site name
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)

    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_confidence: Mapped[str] = mapped_column(String(16), nullable=False)  # VERIFIED | UNVERIFIED

    finding: Mapped[str] = mapped_column(Text, nullable=False)
    project_relevance: Mapped[float] = mapped_column(Float, nullable=False)

    trust_tier: Mapped[str] = mapped_column(String(8), nullable=False)  # TIER_1..TIER_5
    source_quality: Mapped[str] = mapped_column(String(16), nullable=False)  # HIGH|MEDIUM|LOW|UNVERIFIED

    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
