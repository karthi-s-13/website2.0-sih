"use client";

import { useEffect, useRef } from "react";
import {
  PredictionResponse,
  HealthResponse,
  HistoryResponse,
  ReviewEvidenceResponse,
  WebIntelligenceResponse,
  DiagnosisResponse,
  InterventionResponse,
  ProjectSummary,
} from "@/lib/api";
import {
  HEALTH_STYLES,
  RISK_STYLES,
  SEVERITY_STYLES,
  ACTION_TYPE_STYLES,
  TREND_ICON,
  Badge,
  ProgressBar,
  fmt,
} from "../shared";

export interface AIReportData {
  projectId: string;
  projectName: string;
  generatedAt: string; // ISO string
  health: HealthResponse | null;
  prediction: PredictionResponse | null;
  history: HistoryResponse | null;
  review: ReviewEvidenceResponse | null;
  web: WebIntelligenceResponse | null;
  diagnosis: DiagnosisResponse | null;
  intervention: InterventionResponse | null;
}

function computeVerdict(data: AIReportData): {
  grade: "A" | "B" | "C" | "D" | "F";
  color: string;
  bg: string;
  label: string;
  summary: string;
} {
  let score = 100;

  // Deduct based on health
  const healthPenalty: Record<string, number> = {
    NORMAL: 0,
    WATCH: 10,
    ELEVATED: 20,
    HIGH: 35,
    CRITICAL: 50,
    DATA_NOT_AVAILABLE: 15,
  };
  if (data.health?.overall_health) score -= healthPenalty[data.health.overall_health] ?? 15;

  // Deduct based on risk level
  const riskPenalty: Record<string, number> = {
    LOW: 0,
    MODERATE: 8,
    ELEVATED: 16,
    HIGH: 25,
    CRITICAL: 40,
  };
  if (data.prediction?.risk_level) score -= riskPenalty[data.prediction.risk_level] ?? 12;

  // Deduct based on diagnosis overall_risk
  const diagPenalty: Record<string, number> = {
    NORMAL: 0,
    LOW: 0,
    WATCH: 8,
    MODERATE: 12,
    ELEVATED: 18,
    HIGH: 28,
    CRITICAL: 40,
  };
  if (data.diagnosis?.overall_risk) score -= diagPenalty[data.diagnosis.overall_risk] ?? 10;

  // Deduct for critical web findings
  if (data.web?.triggered && data.web.evidence.length > 3) score -= 5;

  score = Math.max(0, Math.min(100, score));

  if (score >= 85)
    return { grade: "A", color: "text-emerald-700", bg: "bg-emerald-50 border-emerald-200", label: "Excellent", summary: "Project is on track with minimal risk." };
  if (score >= 70)
    return { grade: "B", color: "text-blue-700", bg: "bg-blue-50 border-blue-200", label: "Good", summary: "Project is progressing with minor concerns worth monitoring." };
  if (score >= 55)
    return { grade: "C", color: "text-yellow-700", bg: "bg-yellow-50 border-yellow-200", label: "Fair", summary: "Moderate risks detected. Intervention recommended." };
  if (score >= 40)
    return { grade: "D", color: "text-orange-700", bg: "bg-orange-50 border-orange-200", label: "At Risk", summary: "Significant risks detected. Immediate review required." };
  return { grade: "F", color: "text-red-700", bg: "bg-red-50 border-red-200", label: "Critical", summary: "Severe risk indicators. Escalation required immediately." };
}

function formatCrore(value: number | null): string {
  if (value === null) return "—";
  if (value >= 10000) return `₹${(value / 1000).toFixed(1)}K Cr`;
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 1 })} Cr`;
}

function Section({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">{icon}</span>
        <h3 className="text-sm font-bold uppercase tracking-wide text-slate-600">{title}</h3>
      </div>
      {children}
    </div>
  );
}

export function AIReportCard({ report, project }: { report: AIReportData; project: ProjectSummary }) {
  const verdict = computeVerdict(report);
  const generatedDate = new Date(report.generatedAt).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });

  const handlePrint = () => {
    window.print();
  };

  return (
    <div id="ai-report-card" className="space-y-5">
      {/* Report Header */}
      <div className={`rounded-xl border-2 p-6 ${verdict.bg} print:break-inside-avoid`}>
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-1">AI Report Card</div>
            <h2 className="text-xl font-bold text-slate-900">{project.project_name}</h2>
            <div className="mt-1 text-sm text-slate-500">
              {project.agency} &middot; {project.state} &middot; {project.sector}
            </div>
            <div className="mt-2 text-xs text-slate-400">Generated: {generatedDate}</div>
          </div>
          <div className="text-right flex flex-col items-end gap-2">
            <div className={`text-6xl font-black ${verdict.color}`}>{verdict.grade}</div>
            <div className={`text-xs font-bold uppercase tracking-wide ${verdict.color}`}>{verdict.label}</div>
          </div>
        </div>
        <p className={`mt-3 text-sm font-medium ${verdict.color} border-t border-current border-opacity-20 pt-3`}>
          {verdict.summary}
        </p>
      </div>

      {/* Print Button — hidden in print */}
      <div className="flex justify-end gap-2 print:hidden">
        <button
          onClick={handlePrint}
          className="flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
        >
          🖨️ Print / Export PDF
        </button>
      </div>

      {/* Health Summary */}
      <Section title="Health Summary" icon="🏥">
        {report.health ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-xs text-slate-500 mb-1">Overall Health</div>
              <Badge label={report.health.overall_health} styles={HEALTH_STYLES} />
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-1">Physical Progress</div>
              <div className="flex items-center gap-2">
                <ProgressBar actual={report.health.physical_progress} expected={report.health.expected_progress} />
                <span className="text-sm font-semibold text-slate-800">{fmt(report.health.physical_progress)}%</span>
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-1">Cost Utilisation</div>
              <div className="text-sm font-semibold text-slate-800">{fmt(report.health.cost_utilisation)}%</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-1">Recent Trend</div>
              <div className="text-sm font-semibold text-slate-800">
                {TREND_ICON[report.health.recent_trend.label]} {report.health.recent_trend.label.replace(/_/g, " ")}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-400">Health data unavailable.</p>
        )}
      </Section>

      {/* ML Risk Prediction */}
      <Section title="ML Cost Risk Prediction" icon="🤖">
        {report.prediction ? (
          <div className="flex flex-wrap items-center gap-4">
            <Badge label={report.prediction.risk_level} styles={RISK_STYLES} />
            <div className="text-sm text-slate-700">
              Probability of cost overrun:{" "}
              <span className="font-bold text-slate-900">
                {(report.prediction.probability * 100).toFixed(1)}%
              </span>
            </div>
            <div className="ml-auto text-xs text-slate-400">Model v{report.prediction.model_version}</div>
          </div>
        ) : (
          <p className="text-sm text-slate-400">Prediction unavailable — no observation month found.</p>
        )}
      </Section>

      {/* Financials */}
      <Section title="Financial Overview" icon="💰">
        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="text-xs text-slate-500 mb-1">Original Cost</div>
            <div className="text-lg font-bold text-slate-900">{formatCrore(project.original_cost_crore)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Revised Cost</div>
            <div className="text-lg font-bold text-slate-900">{formatCrore(project.revised_cost_crore)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Expenditure</div>
            <div className="text-lg font-bold text-slate-900">{formatCrore(project.cumulative_expenditure_crore)}</div>
          </div>
        </div>
      </Section>

      {/* Project History */}
      <Section title="Project History" icon="📜">
        {report.history ? (
          <div className="space-y-2">
            <p className="text-sm text-slate-800">{report.history.current_state}</p>
            {report.history.historical_risk_signals.length > 0 && (
              <div className="mt-3">
                <div className="text-xs font-semibold uppercase text-slate-500 mb-1">
                  Top Risk Signals ({report.history.historical_risk_signals.length})
                </div>
                <ul className="space-y-1">
                  {report.history.historical_risk_signals.slice(0, 3).map((s, i) => (
                    <li key={i} className="text-sm text-slate-700 flex gap-2">
                      <span className="text-slate-400 shrink-0">{s.month}:</span> {s.description}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-400">History data unavailable.</p>
        )}
      </Section>

      {/* Review Report Findings */}
      <Section title="Review Report Findings" icon="📄">
        {report.review ? (
          <div className="space-y-2">
            <p className="text-sm text-slate-800">{report.review.answer}</p>
            {!report.review.evidence_found && (
              <p className="text-xs text-amber-600">No evidence found in indexed review reports.</p>
            )}
            {report.review.citations.length > 0 && (
              <div className="text-xs text-slate-500 mt-1">
                {report.review.citations.length} citation(s) from review documents.
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-400">Review report data unavailable.</p>
        )}
      </Section>

      {/* Web Intelligence */}
      <Section title="External Web Intelligence" icon="🌐">
        {report.web ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span
                className={`text-xs font-semibold uppercase ${
                  report.web.triggered ? "text-emerald-700" : "text-slate-500"
                }`}
              >
                {report.web.triggered ? "Search Triggered" : "Search Not Triggered"}
              </span>
              <span className="text-xs text-slate-500">— {report.web.trigger_reason}</span>
            </div>
            {report.web.evidence.length > 0 && (
              <ul className="space-y-1 mt-2">
                {report.web.evidence.slice(0, 3).map((e) => (
                  <li key={e.evidence_id} className="text-sm text-slate-700 border-l-2 border-slate-200 pl-2">
                    <span className="font-medium text-slate-900">{e.source}</span> — {e.finding}
                  </li>
                ))}
                {report.web.evidence.length > 3 && (
                  <li className="text-xs text-slate-400">+{report.web.evidence.length - 3} more findings</li>
                )}
              </ul>
            )}
            {report.web.triggered && report.web.evidence.length === 0 && (
              <p className="text-sm text-slate-400">No external evidence found.</p>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-400">Web intelligence unavailable.</p>
        )}
      </Section>

      {/* AI Diagnosis */}
      <Section title="AI Risk Diagnosis" icon="🔍">
        {report.diagnosis ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Badge label={report.diagnosis.overall_risk} styles={SEVERITY_STYLES} />
              {report.diagnosis.risk_score !== null && (
                <span className="text-sm text-slate-700">
                  Risk score: <span className="font-bold">{report.diagnosis.risk_score.toFixed(1)}</span>
                </span>
              )}
              <span className="text-xs text-slate-400 ml-auto">
                Confidence: {(report.diagnosis.confidence * 100).toFixed(0)}%
              </span>
            </div>
            {report.diagnosis.drivers.length > 0 && (
              <div>
                <div className="text-xs font-semibold uppercase text-slate-500 mb-1">
                  Key Risk Drivers ({report.diagnosis.drivers.length})
                </div>
                <ul className="space-y-1">
                  {report.diagnosis.drivers.slice(0, 4).map((d) => (
                    <li key={d.rank} className="flex items-start gap-2 text-sm text-slate-700">
                      <span className="text-slate-400 font-mono shrink-0">#{d.rank}</span>
                      <Badge label={d.severity} styles={SEVERITY_STYLES} />
                      <span>{d.driver}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-400">Diagnosis data unavailable.</p>
        )}
      </Section>

      {/* Recommended Actions */}
      <Section title="Recommended Monitoring Actions" icon="🎯">
        {report.intervention ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Badge label={report.intervention.overall_risk} styles={SEVERITY_STYLES} />
              <span className="text-xs text-slate-500">
                Monitoring level: <span className="font-medium">{report.intervention.suggested_monitoring_level}</span>
              </span>
            </div>
            {report.intervention.recommendations.length > 0 ? (
              <ul className="space-y-2">
                {report.intervention.recommendations.slice(0, 5).map((r, i) => (
                  <li key={i} className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <Badge label={r.priority} styles={SEVERITY_STYLES} />
                      <Badge label={r.action_type} styles={ACTION_TYPE_STYLES} />
                      <span className="text-xs text-slate-400">{r.review_area}</span>
                    </div>
                    <div className="font-medium text-slate-800">{r.action}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{r.reason}</div>
                  </li>
                ))}
                {report.intervention.recommendations.length > 5 && (
                  <li className="text-xs text-slate-400 text-center">
                    +{report.intervention.recommendations.length - 5} more recommendations
                  </li>
                )}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No specific actions recommended.</p>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-400">Intervention data unavailable.</p>
        )}
      </Section>

      {/* Footer */}
      <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 text-center text-xs text-slate-400">
        This AI Report Card was auto-generated by the Project Monitoring Intelligence System on {generatedDate}.
        All assessments are AI-generated and should be reviewed by a qualified project officer.
      </div>
    </div>
  );
}
