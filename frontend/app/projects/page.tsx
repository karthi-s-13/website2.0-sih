"use client";



import Link from "next/link";
import dynamic from "next/dynamic";
import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";
import {
  ApiRequestError,
  DiagnosisResponse,
  EvidenceSourceType,
  HealthResponse,
  HistoryResponse,
  InterventionResponse,
  ModelInfo,
  PredictionResponse,
  ProjectSummary,
  ReviewEvidenceResponse,
  WebIntelligenceResponse,
  getDiagnosis,
  getInterventions,
  getModelInfo,
  getProjectHealth,
  getProjectHistory,
  getReviewEvidence,
  getWebEvidence,
  listProjects,
  predictProject,
} from "@/lib/api";

import { HEALTH_STYLES, TREND_ICON, Badge, ProgressBar, fmt } from "./shared";

type Health = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; data: HealthResponse };

/* ================================================================
   Dashboard Overview — KPI cards, Status donut, Sector bars, Map
   ================================================================ */

const STATUS_COLORS: Record<string, { color: string; label: string }> = {
  NORMAL: { color: "#55c4a2", label: "On Track" },
  WATCH: { color: "#f0c040", label: "At Risk" },
  ELEVATED: { color: "#ee9a3f", label: "Likely Delayed" },
  HIGH: { color: "#e86450", label: "Likely Delayed" },
  CRITICAL: { color: "#a855f7", label: "Severe Risk" },
  DATA_NOT_AVAILABLE: { color: "#9db4c4", label: "Data Unavailable" },
};

const HEALTH_SEVERITY_RANK: Record<string, number> = {
  NORMAL: 0,
  WATCH: 1,
  ELEVATED: 2,
  HIGH: 3,
  CRITICAL: 4,
  DATA_NOT_AVAILABLE: -1,
};

function worstHealth(a: string, b: string): string {
  return (HEALTH_SEVERITY_RANK[a] ?? -1) >= (HEALTH_SEVERITY_RANK[b] ?? -1) ? a : b;
}

function healthToCssClass(h: string): string {
  switch (h) {
    case "NORMAL": return "map-health-normal";
    case "WATCH": return "map-health-watch";
    case "ELEVATED": return "map-health-elevated";
    case "HIGH": return "map-health-high";
    case "CRITICAL": return "map-health-critical";
    default: return "map-health-unknown";
  }
}

function formatCrore(value: number): string {
  if (value >= 10000) return `₹${(value / 1000).toFixed(1)}K Cr`;
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 1 })} Cr`;
}

const DynamicIndiaMap = dynamic(() => import("./IndiaMap"), { 
  ssr: false,
  loading: () => <div className="p-4 text-slate-400 text-sm">Loading Leaflet map...</div>
});

function DashboardOverview({
  projects,
  health,
}: {
  projects: ProjectSummary[];
  health: Record<string, Health>;
}) {
  const mapRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    state: string;
    count: number;
    cost: number;
    health: string;
  } | null>(null);

  // ── Computed aggregates ──
  const kpis = useMemo(() => {
    let originalCost = 0;
    let revisedCost = 0;
    let cumulativeExp = 0;
    for (const p of projects) {
      originalCost += p.original_cost_crore ?? 0;
      revisedCost += p.revised_cost_crore ?? 0;
      cumulativeExp += p.cumulative_expenditure_crore ?? 0;
    }
    return {
      totalProjects: projects.length,
      originalCost,
      revisedCost,
      cumulativeExp,
    };
  }, [projects]);

  // ── Status breakdown for donut ──
  const statusBreakdown = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const p of projects) {
      const h = health[p.project_id];
      const key = h?.status === "ready" ? h.data.overall_health : "DATA_NOT_AVAILABLE";
      counts[key] = (counts[key] ?? 0) + 1;
    }
    // Return sorted by severity
    const order = ["NORMAL", "WATCH", "ELEVATED", "HIGH", "CRITICAL", "DATA_NOT_AVAILABLE"];
    return order.filter((k) => counts[k]).map((key) => ({
      key,
      count: counts[key],
      ...(STATUS_COLORS[key] ?? STATUS_COLORS.DATA_NOT_AVAILABLE),
    }));
  }, [projects, health]);

  // Build donut conic-gradient
  const donutStyle = useMemo(() => {
    const total = projects.length || 1;
    let cumPct = 0;
    const stops: string[] = [];
    for (const seg of statusBreakdown) {
      const pct = (seg.count / total) * 100;
      stops.push(`${seg.color} ${cumPct}% ${cumPct + pct}%`);
      cumPct += pct;
    }
    return { background: `conic-gradient(${stops.join(", ")})` };
  }, [statusBreakdown, projects.length]);

  // ── Sector distribution ──
  const sectors = useMemo(() => {
    const map: Record<string, { count: number; cost: number }> = {};
    for (const p of projects) {
      const sec = p.sector ?? "Unknown";
      if (!map[sec]) map[sec] = { count: 0, cost: 0 };
      map[sec].count += 1;
      map[sec].cost += p.revised_cost_crore ?? p.original_cost_crore ?? 0;
    }
    const items = Object.entries(map)
      .map(([name, { count, cost }]) => ({ name, count, cost }))
      .sort((a, b) => b.cost - a.cost);
    const maxCost = Math.max(...items.map((i) => i.cost), 1);
    return { items, maxCost };
  }, [projects]);

  // ── State → project mapping for India map ──
  const stateData = useMemo(() => {
    const map: Record<string, { count: number; cost: number; worstHealth: string }> = {};
    for (const p of projects) {
      const st = p.state;
      if (!st) continue;
      if (!map[st]) map[st] = { count: 0, cost: 0, worstHealth: "NORMAL" };
      map[st].count += 1;
      map[st].cost += p.revised_cost_crore ?? p.original_cost_crore ?? 0;
      const h = health[p.project_id];
      const hLevel = h?.status === "ready" ? h.data.overall_health : "DATA_NOT_AVAILABLE";
      map[st].worstHealth = worstHealth(map[st].worstHealth, hLevel);
    }
    return map;
  }, [projects, health]);

  function handleMapHover(e: React.MouseEvent, stateName: string) {
    const data = stateData[stateName];
    if (!data || !mapRef.current) return;
    const rect = mapRef.current.getBoundingClientRect();
    setTooltip({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      state: stateName,
      count: data.count,
      cost: data.cost,
      health: data.worstHealth,
    });
  }

  return (
    <div className="mt-6">
      {/* KPI Summary Cards */}
      <div className="dash-kpi-grid">
        <div className="dash-kpi-card" data-accent="blue">
          <div className="dash-kpi-icon">📊</div>
          <span className="dash-kpi-value">{kpis.totalProjects}</span>
          <span className="dash-kpi-label">Ongoing Projects</span>
        </div>
        <div className="dash-kpi-card" data-accent="gold">
          <div className="dash-kpi-icon">💰</div>
          <span className="dash-kpi-value">{formatCrore(kpis.originalCost)}</span>
          <span className="dash-kpi-label">Original Cost</span>
        </div>
        <div className="dash-kpi-card" data-accent="teal">
          <div className="dash-kpi-icon">📈</div>
          <span className="dash-kpi-value">{formatCrore(kpis.revisedCost)}</span>
          <span className="dash-kpi-label">Revised Cost</span>
        </div>
        <div className="dash-kpi-card" data-accent="orange">
          <div className="dash-kpi-icon">🏗️</div>
          <span className="dash-kpi-value">{formatCrore(kpis.cumulativeExp)}</span>
          <span className="dash-kpi-label">Cumulative Expenditure</span>
        </div>
      </div>

      {/* Overview Row: Donut + Sector + Map */}
      <div className="dash-overview-row">
        {/* Status Donut */}
        <div className="dash-panel">
          <div className="dash-panel-title">Project Status Overview</div>
          <div className="dash-donut-wrap">
            <div className="dash-donut" style={donutStyle}>
              <div className="dash-donut-hole">
                <strong>{projects.length}</strong>
                <span>Projects</span>
              </div>
            </div>
            <div className="dash-donut-legend">
              {statusBreakdown.map((seg) => (
                <div key={seg.key} className="dash-legend-item">
                  <span className="dash-legend-dot" style={{ background: seg.color }} />
                  {seg.label} ({seg.count})
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sector Distribution */}
        <div className="dash-panel">
          <div className="dash-panel-title">Sector-wise Distribution</div>
          <div className="dash-sector-list">
            {sectors.items.map((sec) => (
              <div key={sec.name} className="dash-sector-item">
                <div className="dash-sector-header">
                  <span className="dash-sector-name">{sec.name}</span>
                  <span className="dash-sector-meta">
                    {sec.count} project{sec.count !== 1 ? "s" : ""} · {formatCrore(sec.cost)}
                  </span>
                </div>
                <div className="dash-sector-bar-bg">
                  <div
                    className="dash-sector-bar-fill"
                    style={{ width: `${(sec.cost / sectors.maxCost) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* India Map */}
        <div className="dash-panel">
          <div className="dash-panel-title">Geographic Distribution</div>
          <div className="dash-map-wrap overflow-hidden" style={{ minHeight: "300px" }}>
            <DynamicIndiaMap stateData={stateData} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [health, setHealth] = useState<Record<string, Health>>({});

  useEffect(() => {
    listProjects()
      .then((data) => {
        setProjects(data);
        for (const project of data) {
          setHealth((prev) => ({ ...prev, [project.project_id]: { status: "loading" } }));
          getProjectHealth(project.project_id)
            .then((result) =>
              setHealth((prev) => ({ ...prev, [project.project_id]: { status: "ready", data: result } }))
            )
            .catch((err) =>
              setHealth((prev) => ({
                ...prev,
                [project.project_id]: {
                  status: "error",
                  message: err instanceof ApiRequestError ? err.errorCode : "failed",
                },
              }))
            );
        }
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : "Failed to load projects"));
    getModelInfo()
      .then(setModelInfo)
      .catch(() => setModelInfo(null));
  }, []);

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Project Monitoring Dashboard</h1>
        <Link href="/analyze" className="text-sm text-slate-600 underline hover:text-slate-900">
          Ask the Coordinator →
        </Link>
      </div>
      <p className="mt-1 text-sm text-slate-600">
        Deterministic health metrics (Phase 4), pretrained-model cost-overrun risk (Phase 3), an
        evidence-backed history agent (Phase 6), review-report RAG (Phase 7), the Web
        Intelligence Agent (Phase 8), evidence-fused risk diagnosis (Phase 9), monitoring-action
        recommendations (Phase 10), and the Coordinator Agent (Phase 11).
      </p>

      {modelInfo && (
        <div className="mt-4 rounded-md border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600">
          <span className="font-medium text-slate-800">{modelInfo.model_version}</span>
          {" · "}
          trained on {modelInfo.n_training_rows.toLocaleString()} rows ({modelInfo.trained_at.slice(0, 10)})
          {" · "}
          ROC-AUC {modelInfo.oof_metrics.roc_auc?.toFixed(3)}
        </div>
      )}

      {loadError && (
        <p className="mt-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {loadError}
        </p>
      )}

      {!projects && !loadError && <p className="mt-6 text-sm text-slate-500">Loading projects…</p>}

      {projects && projects.length > 0 && (
        <>
          {/* ────── Dashboard Overview Section ────── */}
          <DashboardOverview projects={projects} health={health} />

          {/* ────── Project Table ────── */}

        <div className="mt-6 overflow-x-auto rounded-md border border-slate-200 bg-white">
          <table className="w-full min-w-[960px] text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Progress vs Expected</th>
                <th className="px-4 py-3">Cost Util.</th>
                <th className="px-4 py-3">Divergence</th>
                <th className="px-4 py-3">Trend</th>
                <th className="px-4 py-3">Health</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => {
                const h = health[project.project_id] ?? { status: "loading" };
                return (
                  <Fragment key={project.project_id}>
                    <tr className="border-b border-slate-100 align-top">
                      <td className="max-w-[220px] px-4 py-3">
                        <div className="font-medium text-slate-900">{project.project_name}</div>
                        <div className="text-xs text-slate-500">
                          {project.project_id} · {project.state ?? "—"}
                        </div>
                        <div className="text-xs text-slate-400">
                          ₹{project.original_cost_crore?.toLocaleString() ?? "—"} cr · as of{" "}
                          {project.latest_observation_month ?? "—"}
                        </div>
                      </td>

                      {h.status === "ready" ? (
                        <>
                          <td className="px-4 py-3">
                            <ProgressBar actual={h.data.physical_progress} expected={h.data.expected_progress} />
                            <div className="mt-1 text-xs text-slate-500">
                              {fmt(h.data.physical_progress)}% actual / {fmt(h.data.expected_progress)}% expected
                            </div>
                            <div className="text-xs text-slate-400">
                              gap {h.data.progress_gap !== null && h.data.progress_gap > 0 ? "+" : ""}
                              {fmt(h.data.progress_gap)} pts
                            </div>
                          </td>
                          <td className="px-4 py-3 text-slate-700">{fmt(h.data.cost_utilisation)}%</td>
                          <td className="px-4 py-3 text-slate-700">
                            {h.data.expenditure_progress_divergence !== null &&
                            h.data.expenditure_progress_divergence > 0
                              ? "+"
                              : ""}
                            {fmt(h.data.expenditure_progress_divergence)} pts
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-slate-600">
                              {TREND_ICON[h.data.recent_trend.label]} {h.data.recent_trend.label.toLowerCase()}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <Badge label={h.data.overall_health} styles={HEALTH_STYLES} />
                          </td>
                        </>
                      ) : h.status === "error" ? (
                        <td colSpan={5} className="px-4 py-3 text-xs text-red-600">
                          health unavailable ({h.message})
                        </td>
                      ) : (
                        <td colSpan={5} className="px-4 py-3 text-xs text-slate-400">
                          loading…
                        </td>
                      )}

                      <td className="px-4 py-3 text-right">
                        <Link
                          href={`/projects/${project.project_id}`}
                          className="rounded-md border px-3 py-1.5 text-xs font-medium border-slate-300 text-slate-700 hover:bg-slate-50 inline-block"
                        >
                          View Details
                        </Link>
                      </td>
                    </tr>
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
        </>
      )}
    </main>
  );
}
