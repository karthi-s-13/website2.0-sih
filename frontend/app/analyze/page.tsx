"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AnalysisResponse,
  ApiRequestError,
  PortfolioResponse,
  ProjectSummary,
  analyzeQuery,
  getPortfolio,
  listProjects,
} from "@/lib/api";

const SEVERITY_STYLES: Record<string, string> = {
  NORMAL: "bg-emerald-100 text-emerald-800 border-emerald-300",
  LOW: "bg-emerald-100 text-emerald-800 border-emerald-300",
  WATCH: "bg-yellow-100 text-yellow-800 border-yellow-300",
  MODERATE: "bg-yellow-100 text-yellow-800 border-yellow-300",
  ELEVATED: "bg-orange-100 text-orange-800 border-orange-300",
  HIGH: "bg-red-100 text-red-800 border-red-300",
  CRITICAL: "bg-purple-100 text-purple-800 border-purple-300",
  DATA_NOT_AVAILABLE: "bg-slate-100 text-slate-500 border-slate-300",
};

const STAGE_STATUS_STYLES: Record<string, string> = {
  SUCCESS: "bg-emerald-100 text-emerald-800 border-emerald-300",
  FAILED: "bg-red-100 text-red-800 border-red-300",
  SKIPPED: "bg-slate-100 text-slate-500 border-slate-300",
};

const EVIDENCE_CATEGORY_STYLES: Record<string, string> = {
  PAIMANA_STRUCTURED_DATA: "bg-slate-100 text-slate-700 border-slate-300",
  ANALYTICAL_INFERENCE: "bg-blue-100 text-blue-800 border-blue-300",
  MODEL_INFERENCE: "bg-violet-100 text-violet-800 border-violet-300",
  REVIEW_REPORT: "bg-teal-100 text-teal-800 border-teal-300",
  OFFICIAL_EXTERNAL_SOURCE: "bg-emerald-100 text-emerald-800 border-emerald-300",
  SECONDARY_SOURCE: "bg-orange-100 text-orange-800 border-orange-300",
};

function Badge({ label, styles }: { label: string; styles: Record<string, string> }) {
  return (
    <span
      className={`inline-block w-fit rounded-full border px-2 py-0.5 text-xs font-medium ${
        styles[label] ?? "border-slate-300 bg-slate-100 text-slate-600"
      }`}
    >
      {label.replace(/_/g, " ")}
    </span>
  );
}

type AnalyzeState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; result: AnalysisResponse };

type PortfolioState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; result: PortfolioResponse };

const EXAMPLE_QUESTIONS = [
  "What is the current health?",
  "What is the cost risk?",
  "What happened to this project?",
  "Why is this project at risk?",
  "What should be reviewed?",
];

export default function AnalyzePage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [query, setQuery] = useState("What is the current health?");
  const [projectId, setProjectId] = useState("");
  const [analysis, setAnalysis] = useState<AnalyzeState>({ status: "idle" });
  const [portfolio, setPortfolio] = useState<PortfolioState>({ status: "idle" });

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => setProjects([]));
  }, []);

  async function runAnalyze() {
    setAnalysis({ status: "loading" });
    try {
      const result = await analyzeQuery(query, projectId || undefined);
      setAnalysis({ status: "success", result });
    } catch (err) {
      const message = err instanceof ApiRequestError ? `${err.errorCode}: ${err.message}` : "Request failed";
      setAnalysis({ status: "error", message });
    }
  }

  async function runPortfolio() {
    setPortfolio({ status: "loading" });
    try {
      const result = await getPortfolio(5);
      setPortfolio({ status: "success", result });
    } catch (err) {
      const message = err instanceof ApiRequestError ? `${err.errorCode}: ${err.message}` : "Request failed";
      setPortfolio({ status: "error", message });
    }
  }

  const report = analysis.status === "success" ? analysis.result.report : null;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Ask the Coordinator</h1>
        <Link href="/projects" className="text-sm text-slate-600 underline hover:text-slate-900">
          ← Project dashboard
        </Link>
      </div>
      <p className="mt-1 text-sm text-slate-600">
        One natural-language entry point over every agent (Phases 3–10): intent detection, project
        resolution, planning, risk-triggered expansion, and final synthesis (Phase 11).
      </p>

      <div className="mt-6 rounded-md border border-slate-200 bg-white p-4">
        <label className="block text-xs font-semibold uppercase text-slate-500">Question</label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={2}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          placeholder="What is the cost risk for this project?"
        />
        <div className="mt-2 flex flex-wrap gap-1">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => setQuery(q)}
              className="rounded-full border border-slate-300 px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-50"
            >
              {q}
            </button>
          ))}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <label className="text-xs font-semibold uppercase text-slate-500">Project (optional)</label>
          <select
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            className="rounded-md border border-slate-300 px-2 py-1 text-sm"
          >
            <option value="">Resolve from question text</option>
            {projects.map((p) => (
              <option key={p.project_id} value={p.project_id}>
                {p.project_name.slice(0, 60)} ({p.project_id})
              </option>
            ))}
          </select>
          <button
            onClick={runAnalyze}
            disabled={analysis.status === "loading" || !query.trim()}
            className="rounded-md bg-slate-900 px-4 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:bg-slate-300"
          >
            Analyze
          </button>
        </div>
      </div>

      {analysis.status === "loading" && <p className="mt-4 text-sm text-slate-400">Coordinating agents…</p>}
      {analysis.status === "error" && (
        <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {analysis.message}
        </p>
      )}

      {analysis.status === "success" && (
        <div className="mt-6 space-y-4">
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
            <Badge label={analysis.result.intent} styles={{}} />
            <span>source: {analysis.result.intent_source}</span>
            <span>plan: {analysis.result.plan.join(" → ")}</span>
            {analysis.result.expanded && <Badge label="RISK-TRIGGERED EXPANSION" styles={{ "RISK-TRIGGERED EXPANSION": "bg-purple-100 text-purple-800 border-purple-300" }} />}
          </div>

          {analysis.result.stage_results.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {analysis.result.stage_results.map((sr, i) => (
                <span key={i} className="flex items-center gap-1 text-xs text-slate-500">
                  <Badge label={sr.status} styles={STAGE_STATUS_STYLES} />
                  {sr.stage} ({sr.duration_ms.toFixed(0)}ms)
                </span>
              ))}
            </div>
          )}

          {analysis.result.resolution_status === "AMBIGUOUS" && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm font-medium text-amber-800">
                Multiple projects match — pick one and try again:
              </p>
              <ul className="mt-2 space-y-1">
                {analysis.result.candidates.map((c) => (
                  <li key={c.project_id}>
                    <button
                      onClick={() => setProjectId(c.project_id)}
                      className="text-sm text-slate-700 underline hover:text-slate-900"
                    >
                      {c.project_name} ({c.project_id})
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {report && (
            <div className="rounded-md border border-slate-200 bg-white p-4 space-y-4">
              {report.human_review_required && (
                <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  HUMAN REVIEW REQUIRED — {report.human_review_reason}
                </div>
              )}

              <div>
                <h3 className="text-xs font-semibold uppercase text-slate-500">Executive Summary</h3>
                <p className="mt-1 text-sm text-slate-800">{report.executive_summary}</p>
              </div>

              {report.current_health && (
                <div>
                  <h3 className="text-xs font-semibold uppercase text-slate-500">Current Health</h3>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge label={String(report.current_health.overall_health)} styles={SEVERITY_STYLES} />
                    <span className="text-xs text-slate-500">
                      progress gap {String(report.current_health.progress_gap)}
                    </span>
                  </div>
                </div>
              )}

              {report.cost_overrun_risk && (
                <div>
                  <h3 className="text-xs font-semibold uppercase text-slate-500">Cost-Overrun Risk</h3>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge label={String(report.cost_overrun_risk.risk_level)} styles={SEVERITY_STYLES} />
                    <span className="text-xs text-slate-500">
                      {(Number(report.cost_overrun_risk.probability) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              )}

              {report.key_changes.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold uppercase text-slate-500">Key Changes</h3>
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
                    {report.key_changes.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </div>
              )}

              {report.top_risk_drivers.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold uppercase text-slate-500">Top Risk Drivers</h3>
                  <ol className="mt-1 space-y-1 text-sm text-slate-700">
                    {report.top_risk_drivers.map((d) => (
                      <li key={d.rank} className="flex items-center gap-2">
                        <Badge label={d.severity} styles={SEVERITY_STYLES} />
                        {d.rank}. {d.driver}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {report.evidence.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold uppercase text-slate-500">Evidence</h3>
                  <ul className="mt-1 max-h-48 space-y-1 overflow-y-auto pr-2">
                    {report.evidence.map((e) => (
                      <li key={e.evidence_id} className="flex items-start gap-2 text-xs text-slate-600">
                        <Badge label={e.category} styles={EVIDENCE_CATEGORY_STYLES} />
                        <span>{e.description}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {report.recommended_monitoring_actions.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold uppercase text-slate-500">Recommended Monitoring Actions</h3>
                  <ol className="mt-1 space-y-1 text-sm text-slate-700">
                    {report.recommended_monitoring_actions.map((r, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <Badge label={r.priority} styles={SEVERITY_STYLES} />
                        {r.action}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              <div className="text-xs text-slate-400">trace: {report.trace_id}</div>
            </div>
          )}
        </div>
      )}

      <div className="mt-10 border-t border-slate-200 pt-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Portfolio Mode</h2>
          <button
            onClick={runPortfolio}
            disabled={portfolio.status === "loading"}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Rank all projects
          </button>
        </div>
        {portfolio.status === "loading" && <p className="mt-2 text-sm text-slate-400">Ranking…</p>}
        {portfolio.status === "success" && (
          <table className="mt-3 w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
              <tr>
                <th className="py-1">Rank</th>
                <th className="py-1">Project</th>
                <th className="py-1">Risk Score</th>
                <th className="py-1">Health</th>
                <th className="py-1">ML Risk</th>
                <th className="py-1">Top Driver</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.result.ranked.map((r) => (
                <tr key={r.project_id} className="border-b border-slate-100">
                  <td className="py-1">{r.rank}</td>
                  <td className="py-1">{r.project_name.slice(0, 50)}</td>
                  <td className="py-1">{r.risk_score.toFixed(1)}</td>
                  <td className="py-1">{r.overall_health ?? "—"}</td>
                  <td className="py-1">{r.ml_risk_level ?? "—"}</td>
                  <td className="py-1">{r.diagnosis_summary?.top_driver ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </main>
  );
}
