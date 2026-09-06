"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ApiRequestError,
  ProjectSummary,
  HealthResponse,
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

type HealthState = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; data: HealthResponse };

export default function ProjectDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const [loadError, setLoadError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<PanelTab | "overview">("overview");

  const [prediction, setPrediction] = useState<PredictionState>({ status: "idle" });
  const [history, setHistory] = useState<HistoryState>({ status: "idle" });
  const [historyQuestion, setHistoryQuestion] = useState("");
  const [review, setReview] = useState<ReviewEvidenceState>({ status: "idle" });
  const [reviewQuestion, setReviewQuestion] = useState("");
  const [web, setWeb] = useState<WebEvidenceState>({ status: "idle" });
  const [diagnosis, setDiagnosis] = useState<DiagnosisState>({ status: "idle" });
  const [intervention, setIntervention] = useState<InterventionState>({ status: "idle" });

  useEffect(() => {
    if (!id) return;

    const projectId = typeof id === "string" ? id : id[0];

    getProjectDetail(projectId)
      .then((data) => setProject(data))
      .catch((err) => {
        setLoadError(err instanceof ApiRequestError ? err.message : "Failed to load project details.");
      });

    getProjectHealth(projectId)
      .then((data) => setHealth({ status: "ready", data }))
      .catch((err) => {
        setHealth({ status: "error", message: err instanceof ApiRequestError ? err.message : "Failed to load health data." });
      });
  }, [id]);

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
    const projectId = typeof id === "string" ? id : id[0];
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
    const projectId = typeof id === "string" ? id : id[0];
    setReview({ status: "loading" });
    try {
      const result = await getReviewEvidence(projectId, q);
      setReview({ status: "success", result });
    } catch (err: any) {
      setReview({ status: "error", message: err.message || "Request failed" });
    }
  }

  async function checkWebEvidence(force: boolean) {
    const projectId = typeof id === "string" ? id : id[0];
    setWeb({ status: "loading" });
    try {
      const result = await getWebEvidence(projectId, force);
      setWeb({ status: "success", result });
    } catch (err: any) {
      setWeb({ status: "error", message: err.message || "Request failed" });
    }
  }

  async function runDiagnosis() {
    const projectId = typeof id === "string" ? id : id[0];
    setDiagnosis({ status: "loading" });
    try {
      const result = await getDiagnosis(projectId);
      setDiagnosis({ status: "success", result });
    } catch (err: any) {
      setDiagnosis({ status: "error", message: err.message || "Request failed" });
    }
  }

  async function runInterventions() {
    const projectId = typeof id === "string" ? id : id[0];
    setIntervention({ status: "loading" });
    try {
      const result = await getInterventions(projectId);
      setIntervention({ status: "success", result });
    } catch (err: any) {
      setIntervention({ status: "error", message: err.message || "Request failed" });
    }
  }

  function handleTabChange(tab: PanelTab | "overview") {
    setActiveTab(tab);
    if (tab === "history" && history.status === "idle") askHistory();
    if (tab === "review" && review.status === "idle") askReview();
    if (tab === "web" && web.status === "idle") checkWebEvidence(false);
    if (tab === "diagnosis" && diagnosis.status === "idle") runDiagnosis();
    if (tab === "intervention" && intervention.status === "idle") runInterventions();
  }

  function formatCrore(value: number | null): string {
    if (value === null) return "—";
    if (value >= 10000) return `₹${(value / 1000).toFixed(1)}K Cr`;
    return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 1 })} Cr`;
  }

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

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <Link href="/projects" className="text-sm text-slate-500 hover:text-slate-800">
            &larr; Back to Dashboard
          </Link>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">{project.project_name}</h1>
          <div className="mt-1 flex items-center gap-2 text-sm text-slate-600">
            <span>{project.agency ?? "Unknown Agency"}</span>
            <span className="text-slate-300">|</span>
            <span>{project.state ?? "Unknown State"}</span>
            <span className="text-slate-300">|</span>
            <span>{project.sector ?? "Unknown Sector"}</span>
          </div>
        </div>
        {health.status === "ready" && (
          <div className="text-right">
            <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Overall Health</div>
            <Badge label={health.data.overall_health} styles={HEALTH_STYLES} />
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Left Sidebar - Navigation Tabs */}
        <div className="lg:col-span-1 space-y-1">
          <button
            onClick={() => handleTabChange("overview")}
            className={`w-full text-left px-4 py-2 text-sm font-medium rounded-md ${
              activeTab === "overview" ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => handleTabChange("history")}
            className={`w-full text-left px-4 py-2 text-sm font-medium rounded-md ${
              activeTab === "history" ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            History & Timeline
          </button>
          <button
            onClick={() => handleTabChange("review")}
            className={`w-full text-left px-4 py-2 text-sm font-medium rounded-md ${
              activeTab === "review" ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            Review Evidence
          </button>
          <button
            onClick={() => handleTabChange("web")}
            className={`w-full text-left px-4 py-2 text-sm font-medium rounded-md ${
              activeTab === "web" ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            Web Intelligence
          </button>
          <button
            onClick={() => handleTabChange("diagnosis")}
            className={`w-full text-left px-4 py-2 text-sm font-medium rounded-md ${
              activeTab === "diagnosis" ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            AI Diagnosis
          </button>
          <button
            onClick={() => handleTabChange("intervention")}
            className={`w-full text-left px-4 py-2 text-sm font-medium rounded-md ${
              activeTab === "intervention" ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            Interventions
          </button>
        </div>

        {/* Right Content Area */}
        <div className="lg:col-span-3">
          
          {activeTab === "overview" && (
            <div className="space-y-6">
              {/* General Details Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Original Cost</div>
                  <div className="mt-2 text-2xl font-bold text-slate-900">{formatCrore(project.original_cost_crore)}</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Revised Cost</div>
                  <div className="mt-2 text-2xl font-bold text-slate-900">{formatCrore(project.revised_cost_crore)}</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Cumulative Expenditure</div>
                  <div className="mt-2 text-2xl font-bold text-slate-900">{formatCrore(project.cumulative_expenditure_crore)}</div>
                </div>
              </div>

              {/* Progress & Health Details */}
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
                        <span className="text-sm font-medium text-slate-900">
                          {fmt(health.data.physical_progress)}%
                        </span>
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
                        {TREND_ICON[health.data.recent_trend.label]} {health.data.recent_trend.label.replace(/_/g, " ")}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Cost Risk Prediction */}
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
                
                {prediction.status === "idle" && <p className="text-sm text-slate-500">Run a prediction to assess cost overrun risk.</p>}
                {prediction.status === "loading" && <p className="text-sm text-slate-500">Running prediction model...</p>}
                {prediction.status === "error" && <p className="text-sm text-red-600">{prediction.message}</p>}
                
                {prediction.status === "success" && (
                  <div className="flex items-center gap-4">
                    <Badge label={prediction.result.risk_level} styles={RISK_STYLES} />
                    <div className="text-sm text-slate-700">
                      Probability of overrun: <span className="font-semibold">{(prediction.result.probability * 100).toFixed(1)}%</span>
                    </div>
                    <div className="text-xs text-slate-400 ml-auto">
                      Model: {prediction.result.model_version}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* AI Panels */}
          {activeTab !== "overview" && (
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900 mb-4 capitalize">
                {activeTab.replace("-", " ")}
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
