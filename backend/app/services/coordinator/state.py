"""Shared Agent State (spec section 9) - the structured object every stage
reads from / writes exactly its own field of (spec section 10: "agents
must... write only their assigned state fields... never silently overwrite
another agent's result").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.services.anomaly.service import AnomalyResult
from app.services.diagnosis.service import DiagnosisResult
from app.services.health.formulas import HealthVector
from app.services.history.service import HistoryResult
from app.services.intervention.service import InterventionResult
from app.services.prediction.service import PredictionResult
from app.services.rag.service import EvidenceResult
from app.services.coordinator.portfolio import PortfolioResult
from app.services.coordinator.resolution import ProjectCandidate
from app.services.reporting.builder import Report
from app.services.web.service import WebIntelligenceResult

# Spec section 67.
PENDING = "PENDING"
RUNNING = "RUNNING"
SUCCESS = "SUCCESS"
PARTIAL = "PARTIAL"
FAILED = "FAILED"
SKIPPED = "SKIPPED"
BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class StageResult:
    stage: str
    status: str
    error: str | None
    duration_ms: float


@dataclass
class AnalysisState:
    trace_id: str
    analysis_id: str
    query: str
    intent: str = ""
    intent_source: str = ""
    project_id: str | None = None
    project_name: str | None = None
    as_of_date: date | None = None
    plan: list[str] = field(default_factory=list)
    expanded: bool = False

    history: HistoryResult | None = None
    health: HealthVector | None = None
    prediction: PredictionResult | None = None
    prediction_error: bool = False
    anomalies: AnomalyResult | None = None
    review: EvidenceResult | None = None
    web: WebIntelligenceResult | None = None
    diagnosis: DiagnosisResult | None = None
    intervention: InterventionResult | None = None
    report: Report | None = None
    portfolio: PortfolioResult | None = None

    # Set when project resolution is ambiguous (spec section 8) - the
    # caller must disambiguate before any analysis can run.
    resolution_status: str | None = None
    candidates: list[ProjectCandidate] = field(default_factory=list)

    stage_results: list[StageResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
