"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useARIA } from "../../components/ARIAContext";
import {
  ApiRequestError,
  ProjectSummary,
  HealthResponse,
  PredictionResponse,
  HistoryResponse,
  ReviewEvidenceResponse,
  WebIntelligenceResponse,
  DiagnosisResponse,
  InterventionResponse,
  getProjectDetail,
  getProjectHealth,
  predictProject,
  getProjectHistory,
  getReviewEvidence,
  getWebEvidence,
  getDiagnosis,
  getInterventions,
} from "@/lib/api";

import {
  HEALTH_STYLES,
  RISK_STYLES,
  TREND_ICON,
  Badge,
  ProgressBar,
  fmt,
  PanelTab,
  PredictionState,
  HistoryState,
  ReviewEvidenceState,
  WebEvidenceState,
  DiagnosisState,
  InterventionState,
  HistoryPanel,
  ReviewEvidencePanel,
  WebEvidencePanel,
  DiagnosisPanel,
  InterventionPanel,
} from "../shared";

import { AIReportCard, AIReportData } from "./AIReportCard";

type HealthState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: HealthResponse };

type ReportCardState =
  | { status: "idle" }
  | { status: "generating"; progress: Record<string, "pending" | "running" | "done" | "error"> }
  | { status: "ready"; report: AIReportData };

const AGENT_LABELS: Record<string, string> = {
  health: "Health Data",
  prediction: "ML Prediction",
  history: "Project History",
  review: "Review Reports",
  web: "Web Intelligence",
  diagnosis: "AI Diagnosis",
  intervention: "Interventions",
};

function formatCrore(value: number | null): string {
  if (value === null) return "—";
  if (value >= 10000) return `₹${(value / 1000).toFixed(1)}K Cr`;
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 1 })} Cr`;
}

export default function ProjectDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const projectId = typeof id === "string" ? id : Array.isArray(id) ? id[0] : "";

  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const [loadError, setLoadError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<PanelTab | "overview" | "report-card">("overview");

  const [prediction, setPrediction] = useState<PredictionState>({ status: "idle" });
  const [history, setHistory] = useState<HistoryState>({ status: "idle" });
  const [historyQuestion, setHistoryQuestion] = useState("");
  const [review, setReview] = useState<ReviewEvidenceState>({ status: "idle" });
  const [reviewQuestion, setReviewQuestion] = useState("");
  const [web, setWeb] = useState<WebEvidenceState>({ status: "idle" });
  const [diagnosis, setDiagnosis] = useState<DiagnosisState>({ status: "idle" });
  const [intervention, setIntervention] = useState<InterventionState>({ status: "idle" });

  const [reportCard, setReportCard] = useState<ReportCardState>({ status: "idle" });

  const { setProjectContext, clearProjectContext } = useARIA();

  // ── Load project & health ──────────────────────────────────────────────────
  useEffect(() => {
    if (!projectId) return;

    getProjectDetail(projectId)
      .then((data) => {
        setProject(data);
        setProjectContext(data.project_id, data.project_name);
      })
      .catch((err) => {
        setLoadError(err instanceof ApiRequestError ? err.message : "Failed to load project details.");
      });

    getProjectHealth(projectId)
      .then((data) => setHealth({ status: "ready", data }))
      .catch((err) => {
        setHealth({
          status: "error",
          message: err instanceof ApiRequestError ? err.message : "Failed to load health data.",
        });
      });

    return () => clearProjectContext();
  }, [projectId, setProjectContext, clearProjectContext]);

  // ── Load cached report from localStorage ─────────────────────────────────
  useEffect(() => {
    if (!projectId) return;
    try {
      const cached = localStorage.getItem(`ai_report_${projectId}`);
      if (cached) {
        const report: AIReportData = JSON.parse(cached);
        setReportCard({ status: "ready", report });
      }
    } catch {
      // ignore
    }
  }, [projectId]);

  // ── Individual agent functions ────────────────────────────────────────────
  async function runPrediction() {
    if (!project?.latest_observation_month) return;
    setPrediction({ status: "loading" });
    try {
      const result = await predictProject(project.project_id, project.latest_observation_month);
      setPrediction({ status: "success", result });
    } catch (err: any) {
      setPrediction({ status: "error", message: err.message || "Prediction failed" });
    }
  }

  async function askHistory() {
    const q = historyQuestion.trim() || "What happened to this project?";
    setHistory({ status: "loading" });
    try {
      const result = await getProjectHistory(projectId, q);
      setHistory({ status: "success", result });
    } catch (err: any) {
      setHistory({ status: "error", message: err.message || "Request failed" });
    }
  }

  async function askReview() {
    const q = reviewQuestion.trim() || "What does the latest review report say about this project?";
    setReview({ status: "loading" });
    try {
      const result = await getReviewEvidence(projectId, q);
      setReview({ status: "success", result });
    } catch (err: any) {
      setReview({ status: "error", message: err.message || "Request failed" });
    }
  }

  async function checkWebEvidence(force: boolean) {
    setWeb({ status: "loading" });
    try {
      const result = await getWebEvidence(projectId, force);
      setWeb({ status: "success", result });
    } catch (err: any) {
      setWeb({ status: "error", message: err.message || "Request failed" });
    }
  }

  async function runDiagnosis() {
    setDiagnosis({ status: "loading" });
    try {
      const result = await getDiagnosis(projectId);
      setDiagnosis({ status: "success", result });
    } catch (err: any) {
      setDiagnosis({ status: "error", message: err.message || "Request failed" });
    }
  }

  async function runInterventions() {
    setIntervention({ status: "loading" });
    try {
      const result = await getInterventions(projectId);
      setIntervention({ status: "success", result });
    } catch (err: any) {
      setIntervention({ status: "error", message: err.message || "Request failed" });
    }
  }

  function handleTabChange(tab: PanelTab | "overview" | "report-card") {
    setActiveTab(tab);
    if (tab === "history" && history.status === "idle") askHistory();
    if (tab === "review" && review.status === "idle") askReview();
    if (tab === "web" && web.status === "idle") checkWebEvidence(false);
    if (tab === "diagnosis" && diagnosis.status === "idle") runDiagnosis();
    if (tab === "intervention" && intervention.status === "idle") runInterventions();
  }

  // ── Generate AI Report Card ───────────────────────────────────────────────
  const generateReportCard = useCallback(async () => {
    if (!project) return;

    const agentKeys = ["health", "prediction", "history", "review", "web", "diagnosis", "intervention"];
    const initProgress = Object.fromEntries(agentKeys.map((k) => [k, "pending" as const]));
    setReportCard({ status: "generating", progress: initProgress });
    setActiveTab("report-card");

    const setAgentStatus = (key: string, status: "running" | "done" | "error") => {
      setReportCard((prev) => {
        if (prev.status !== "generating") return prev;
        return { ...prev, progress: { ...prev.progress, [key]: status } };
      });
    };

    // Run all agents in parallel with individual progress tracking
    async function run<T>(key: string, fn: () => Promise<T>): Promise<T | null> {
      setAgentStatus(key, "running");
      try {
        const result = await fn();
        setAgentStatus(key, "done");
        return result;
      } catch {
        setAgentStatus(key, "error");
        return null;
      }
    }

    const [
      healthResult,
      predictionResult,
      historyResult,
      reviewResult,
      webResult,
      diagnosisResult,
      interventionResult,
    ] = await Promise.all([
      run<HealthResponse>("health", () => getProjectHealth(projectId)),
      run<PredictionResponse | null>(
        "prediction",
        () =>
          project.latest_observation_month
            ? predictProject(project.project_id, project.latest_observation_month)
            : Promise.resolve(null)
      ),
      run<HistoryResponse>("history", () =>
        getProjectHistory(projectId, "What happened to this project?")
      ),
      run<ReviewEvidenceResponse>("review", () =>
        getReviewEvidence(projectId, "What does the latest review report say about this project?")
      ),
      run<WebIntelligenceResponse>("web", () => getWebEvidence(projectId, false)),
      run<DiagnosisResponse>("diagnosis", () => getDiagnosis(projectId)),
      run<InterventionResponse>("intervention", () => getInterventions(projectId)),
    ]);

    // Update individual agent states too so tabs show latest data
    if (healthResult) setHealth({ status: "ready", data: healthResult });
    if (predictionResult) setPrediction({ status: "success", result: predictionResult });
    if (historyResult) setHistory({ status: "success", result: historyResult });
    if (reviewResult) setReview({ status: "success", result: reviewResult });
    if (webResult) setWeb({ status: "success", result: webResult });
    if (diagnosisResult) setDiagnosis({ status: "success", result: diagnosisResult });
    if (interventionResult) setIntervention({ status: "success", result: interventionResult });

    const report: AIReportData = {
      projectId: project.project_id,
      projectName: project.project_name,
      generatedAt: new Date().toISOString(),
      health: healthResult,
      prediction: predictionResult ?? null,
      history: historyResult,
      review: reviewResult,
      web: webResult,
      diagnosis: diagnosisResult,
      intervention: interventionResult,
    };

    // Persist to localStorage
    try {
      localStorage.setItem(`ai_report_${projectId}`, JSON.stringify(report));
    } catch {
      // Storage full or unavailable — silent fail
    }

    setReportCard({ status: "ready", report });
  }, [project, projectId]);

  // ── Error & loading states ────────────────────────────────────────────────
  if (loadError) {
    return (
      <main className="mx-auto max-w-7xl px-6 py-10">
        <div className="rounded-md bg-red-50 p-4 text-red-700">{loadError}</div>
        <Link href="/projects" className="mt-4 inline-block text-blue-600 hover:underline">
          &larr; Back to Dashboard
        </Link>
      </main>
    );
  }

  if (!project) {
    return (
      <main className="mx-auto max-w-7xl px-6 py-10">
        <div className="text-slate-500">Loading project details...</div>
      </main>
    );
  }

  const isGenerating = reportCard.status === "generating";
  const hasReport = reportCard.status === "ready";

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      {/* ── Page Header ── */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link href="/projects" className="text-sm text-slate-500 hover:text-slate-800">
            &larr; Back to Dashboard
          </Link>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">{project.project_name}</h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-600">
            <span>{project.agency ?? "Unknown Agency"}</span>
            <span className="text-slate-300">|</span>
            <span>{project.state ?? "Unknown State"}</span>
            <span className="text-slate-300">|</span>
            <span>{project.sector ?? "Unknown Sector"}</span>
          </div>
        </div>

        <div className="flex flex-col items-end gap-3">
          {health.status === "ready" && (
            <div className="text-right">
              <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Overall Health</div>
              <Badge label={health.data.overall_health} styles={HEALTH_STYLES} />
            </div>
          )}

          {/* AI Report Card Button */}
          <button
            onClick={generateReportCard}
            disabled={isGenerating}
            className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold shadow-sm transition-all ${
              isGenerating
                ? "cursor-not-allowed bg-slate-200 text-slate-400"
                : hasReport
                ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-700 hover:to-indigo-700 shadow-violet-200"
                : "bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-700 hover:to-indigo-700 shadow-violet-200"
            }`}
          >
            {isGenerating ? (
              <>
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-400 border-t-transparent" />
                Generating Report...
              </>
            ) : hasReport ? (
              <>✨ Regenerate AI Report Card</>
            ) : (
              <>✨ Generate AI Report Card</>
            )}
          </button>

          {hasReport && reportCard.status === "ready" && (
            <button
              onClick={() => setActiveTab("report-card")}
              className="text-xs text-violet-600 hover:underline"
            >
              View saved report →
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* ── Left Sidebar ── */}
        <div className="lg:col-span-1 space-y-1">
          {/* Report Card tab (highlighted) */}
          {(isGenerating || hasReport) && (
            <button
              onClick={() => setActiveTab("report-card")}
              className={`w-full text-left px-4 py-2.5 text-sm font-semibold rounded-md flex items-center gap-2 ${
                activeTab === "report-card"
                  ? "bg-violet-700 text-white"
                  : "bg-violet-50 text-violet-700 border border-violet-200 hover:bg-violet-100"
              }`}
            >
              <span>✨</span> AI Report Card
              {hasReport && <span className="ml-auto text-xs opacity-70">Saved</span>}
              {isGenerating && (
                <span className="ml-auto inline-block h-3 w-3 animate-spin rounded-full border-2 border-violet-300 border-t-transparent" />
              )}
            </button>
          )}

          <div className="pt-1 space-y-0.5">
            {(
              [
                ["overview", "Overview"],
                ["history", "History & Timeline"],
                ["review", "Review Evidence"],
                ["web", "Web Intelligence"],
                ["diagnosis", "AI Diagnosis"],
                ["intervention", "Interventions"],
              ] as const
            ).map(([tab, label]) => (
              <button
                key={tab}
                onClick={() => handleTabChange(tab)}
                className={`w-full text-left px-4 py-2 text-sm font-medium rounded-md ${
                  activeTab === tab
                    ? "bg-slate-900 text-white"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* ── Right Content ── */}
        <div className="lg:col-span-3">

          {/* ── Report Card Tab ── */}
          {activeTab === "report-card" && (
            <>
              {/* Progress Tracker */}
              {reportCard.status === "generating" && (
                <div className="rounded-xl border border-violet-200 bg-violet-50 p-5 mb-5">
                  <h3 className="text-sm font-bold text-violet-800 mb-3 flex items-center gap-2">
                    <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-violet-400 border-t-transparent" />
                    Running AI Agents...
                  </h3>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {Object.entries(reportCard.progress).map(([key, status]) => (
                      <div
                        key={key}
                        className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium border ${
                          status === "done"
                            ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                            : status === "error"
                            ? "bg-red-50 border-red-200 text-red-700"
                            : status === "running"
                            ? "bg-blue-50 border-blue-200 text-blue-700"
                            : "bg-white border-slate-200 text-slate-400"
                        }`}
                      >
                        {status === "done" && <span>✅</span>}
                        {status === "error" && <span>❌</span>}
                        {status === "running" && (
                          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-blue-300 border-t-transparent" />
                        )}
                        {status === "pending" && <span className="h-3 w-3 rounded-full border-2 border-slate-200" />}
                        {AGENT_LABELS[key]}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Rendered Report */}
              {reportCard.status === "ready" && (
                <AIReportCard report={reportCard.report} project={project} />
              )}
            </>
          )}

          {/* ── Overview Tab ── */}
          {activeTab === "overview" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  ["Original Cost", project.original_cost_crore],
                  ["Revised Cost", project.revised_cost_crore],
                  ["Cumulative Expenditure", project.cumulative_expenditure_crore],
                ].map(([label, val]) => (
                  <div key={label as string} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label as string}</div>
                    <div className="mt-2 text-2xl font-bold text-slate-900">{formatCrore(val as number | null)}</div>
                  </div>
                ))}
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">Progress Details</h3>
                {health.status === "loading" && <p className="text-sm text-slate-500">Loading progress data...</p>}
                {health.status === "error" && <p className="text-sm text-red-600">{health.message}</p>}
                {health.status === "ready" && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <div className="text-sm text-slate-500 mb-1">Physical vs Expected Progress</div>
                      <div className="flex items-center gap-3">
                        <ProgressBar actual={health.data.physical_progress} expected={health.data.expected_progress} />
                        <span className="text-sm font-medium text-slate-900">{fmt(health.data.physical_progress)}%</span>
                      </div>
                      <div className="mt-1 text-xs text-slate-400">
                        Gap: {health.data.progress_gap !== null && health.data.progress_gap > 0 ? "+" : ""}
                        {fmt(health.data.progress_gap)}%
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-500 mb-1">Cost vs Schedule Utilisation</div>
                      <div className="text-sm text-slate-800">
                        Cost: <span className="font-medium">{fmt(health.data.cost_utilisation)}%</span>
                      </div>
                      <div className="text-sm text-slate-800 mt-1">
                        Schedule: <span className="font-medium">{fmt(health.data.schedule_utilisation)}%</span>
                      </div>
                      <div className="mt-1 text-xs text-slate-400">
                        Divergence: {fmt(health.data.expenditure_progress_divergence)} pts
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-500 mb-1">Recent Trend</div>
                      <div className="text-sm font-medium text-slate-900">
                        {TREND_ICON[health.data.recent_trend.label]}{" "}
                        {health.data.recent_trend.label.replace(/_/g, " ")}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-slate-900">Cost Risk Prediction</h3>
                  <button
                    onClick={runPrediction}
                    disabled={prediction.status === "loading" || !project.latest_observation_month}
                    className="rounded-md bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-200 disabled:cursor-not-allowed disabled:bg-slate-50"
                  >
                    {prediction.status === "success" ? "Re-run Prediction" : "Run Prediction"}
                  </button>
                </div>
                {prediction.status === "idle" && (
                  <p className="text-sm text-slate-500">Run a prediction to assess cost overrun risk.</p>
                )}
                {prediction.status === "loading" && (
                  <p className="text-sm text-slate-500">Running prediction model...</p>
                )}
                {prediction.status === "error" && (
                  <p className="text-sm text-red-600">{prediction.message}</p>
                )}
                {prediction.status === "success" && (
                  <div className="flex items-center gap-4">
                    <Badge label={prediction.result.risk_level} styles={RISK_STYLES} />
                    <div className="text-sm text-slate-700">
                      Probability of overrun:{" "}
                      <span className="font-semibold">{(prediction.result.probability * 100).toFixed(1)}%</span>
                    </div>
                    <div className="text-xs text-slate-400 ml-auto">
                      Model: {prediction.result.model_version}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── AI Agent Panels ── */}
          {activeTab !== "overview" && activeTab !== "report-card" && (
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900 mb-4 capitalize">
                {(activeTab as string).replace("-", " ")}
              </h3>
              {activeTab === "history" && (
                <HistoryPanel
                  history={history}
                  question={historyQuestion}
                  onQuestionChange={setHistoryQuestion}
                  onAsk={askHistory}
                />
              )}
              {activeTab === "review" && (
                <ReviewEvidencePanel
                  review={review}
                  question={reviewQuestion}
                  onQuestionChange={setReviewQuestion}
                  onAsk={askReview}
                />
              )}
              {activeTab === "web" && (
                <WebEvidencePanel web={web} onSearch={(force) => checkWebEvidence(force)} />
              )}
              {activeTab === "diagnosis" && (
                <DiagnosisPanel diagnosis={diagnosis} onRun={runDiagnosis} />
              )}
              {activeTab === "intervention" && (
                <InterventionPanel intervention={intervention} onRun={runInterventions} />
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
