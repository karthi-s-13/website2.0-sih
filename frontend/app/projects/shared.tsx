"use client";

import {
  DiagnosisResponse,
  EvidenceSourceType,
  HistoryResponse,
  InterventionResponse,
  PredictionResponse,
  ReviewEvidenceResponse,
  WebIntelligenceResponse,
} from "@/lib/api";

export const HEALTH_STYLES: Record<string, string> = {
  NORMAL: "bg-emerald-100 text-emerald-800 border-emerald-300",
  WATCH: "bg-yellow-100 text-yellow-800 border-yellow-300",
  ELEVATED: "bg-orange-100 text-orange-800 border-orange-300",
  HIGH: "bg-red-100 text-red-800 border-red-300",
  CRITICAL: "bg-purple-100 text-purple-800 border-purple-300",
  DATA_NOT_AVAILABLE: "bg-slate-100 text-slate-500 border-slate-300",
};

export const RISK_STYLES: Record<string, string> = {
  LOW: "bg-emerald-100 text-emerald-800 border-emerald-300",
  MODERATE: "bg-yellow-100 text-yellow-800 border-yellow-300",
  ELEVATED: "bg-orange-100 text-orange-800 border-orange-300",
  HIGH: "bg-red-100 text-red-800 border-red-300",
  CRITICAL: "bg-purple-100 text-purple-800 border-purple-300",
};

export const EVIDENCE_STYLES: Record<EvidenceSourceType, string> = {
  OBSERVED_FACT: "bg-slate-100 text-slate-700 border-slate-300",
  INFERRED_TREND: "bg-blue-100 text-blue-800 border-blue-300",
  MODEL_PREDICTION: "bg-violet-100 text-violet-800 border-violet-300",
};

export const SOURCE_QUALITY_STYLES: Record<string, string> = {
  HIGH: "bg-emerald-100 text-emerald-800 border-emerald-300",
  MEDIUM: "bg-yellow-100 text-yellow-800 border-yellow-300",
  LOW: "bg-orange-100 text-orange-800 border-orange-300",
  UNVERIFIED: "bg-slate-100 text-slate-500 border-slate-300",
};

export const SEVERITY_STYLES: Record<string, string> = {
  NORMAL: "bg-emerald-100 text-emerald-800 border-emerald-300",
  LOW: "bg-emerald-100 text-emerald-800 border-emerald-300",
  WATCH: "bg-yellow-100 text-yellow-800 border-yellow-300",
  MODERATE: "bg-yellow-100 text-yellow-800 border-yellow-300",
  ELEVATED: "bg-orange-100 text-orange-800 border-orange-300",
  HIGH: "bg-red-100 text-red-800 border-red-300",
  CRITICAL: "bg-purple-100 text-purple-800 border-purple-300",
  DATA_NOT_AVAILABLE: "bg-slate-100 text-slate-500 border-slate-300",
};

export const ACTION_TYPE_STYLES: Record<string, string> = {
  REVIEW: "bg-slate-100 text-slate-700 border-slate-300",
  VERIFICATION: "bg-orange-100 text-orange-800 border-orange-300",
  MONITORING: "bg-red-100 text-red-800 border-red-300",
  INFORMATION_REQUEST: "bg-blue-100 text-blue-800 border-blue-300",
  MILESTONE_REVIEW: "bg-yellow-100 text-yellow-800 border-yellow-300",
  COST_PROGRESS_REVIEW: "bg-violet-100 text-violet-800 border-violet-300",
  IMPLEMENTATION_REVIEW: "bg-teal-100 text-teal-800 border-teal-300",
};

export const EVIDENCE_CATEGORY_STYLES: Record<string, string> = {
  PAIMANA_STRUCTURED_DATA: "bg-slate-100 text-slate-700 border-slate-300",
  ANALYTICAL_INFERENCE: "bg-blue-100 text-blue-800 border-blue-300",
  MODEL_INFERENCE: "bg-violet-100 text-violet-800 border-violet-300",
  REVIEW_REPORT: "bg-teal-100 text-teal-800 border-teal-300",
  OFFICIAL_EXTERNAL_SOURCE: "bg-emerald-100 text-emerald-800 border-emerald-300",
  SECONDARY_SOURCE: "bg-orange-100 text-orange-800 border-orange-300",
};

export const TREND_ICON: Record<string, string> = {
  IMPROVING: "▲",
  STABLE: "▬",
  STAGNANT: "■",
  DECLINING: "▼",
  DATA_NOT_AVAILABLE: "–",
};

export type PredictionState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; result: PredictionResponse };

export type HistoryState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; result: HistoryResponse };

export type ReviewEvidenceState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; result: ReviewEvidenceResponse };

export type WebEvidenceState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; result: WebIntelligenceResponse };

export type DiagnosisState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; result: DiagnosisResponse };

export type InterventionState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; result: InterventionResponse };

export type PanelTab = "history" | "review" | "web" | "diagnosis" | "intervention";

export function fmt(value: number | null, digits = 1): string {
  return value === null ? "—" : value.toFixed(digits);
}

export function Badge({ label, styles }: { label: string; styles: Record<string, string> }) {
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

export function ProgressBar({ actual, expected }: { actual: number | null; expected: number | null }) {
  const a = actual === null ? 0 : Math.min(Math.max(actual, 0), 100);
  const e = expected === null ? null : Math.min(Math.max(expected, 0), 100);
  return (
    <div className="relative h-2 w-32 rounded-full bg-slate-100">
      <div className="absolute inset-y-0 left-0 rounded-full bg-slate-700" style={{ width: `${a}%` }} />
      {e !== null && (
        <div
          className="absolute top-[-2px] h-3 w-0.5 bg-red-500"
          style={{ left: `${e}%` }}
          title={`expected ${e.toFixed(1)}%`}
        />
      )}
    </div>
  );
}

export function SourceBadge({ source, model }: { source: string; model: string | null }) {
  return (
    <span className="text-xs text-slate-500">
      answer source:{" "}
      <span className={source === "LLM" ? "text-violet-700" : "text-slate-600"}>
        {source}
        {model ? ` (${model})` : ""}
      </span>
    </span>
  );
}

export function HistoryPanel({
  history,
  question,
  onQuestionChange,
  onAsk,
}: {
  history: HistoryState;
  question: string;
  onQuestionChange: (value: string) => void;
  onAsk: () => void;
}) {
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
          className="w-80 max-w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
          placeholder="What happened to this project?"
        />
        <button
          onClick={onAsk}
          disabled={history.status === "loading"}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:bg-slate-300"
        >
          Ask
        </button>
        {history.status === "success" && (
          <SourceBadge source={history.result.summary_source} model={history.result.summary_model} />
        )}
      </div>

      {history.status === "loading" && <p className="mt-3 text-sm text-slate-400">Asking…</p>}
      {history.status === "error" && <p className="mt-3 text-sm text-red-600">{history.message}</p>}

      {history.status === "success" && (
        <div className="mt-4 space-y-4">
          <div>
            <h4 className="text-xs font-semibold uppercase text-slate-500">Current State</h4>
            <p className="mt-1 text-sm text-slate-800">{history.result.current_state}</p>
          </div>

          {history.result.historical_risk_signals.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-500">Risk Signals</h4>
              <ul className="mt-1 space-y-1">
                {history.result.historical_risk_signals.map((signal, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                    <Badge label={signal.source_type} styles={EVIDENCE_STYLES} />
                    <span>
                      <span className="text-slate-400">{signal.month}:</span> {signal.description}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <h4 className="text-xs font-semibold uppercase text-slate-500">
              Timeline ({history.result.timeline.length} entries)
            </h4>
            <ul className="mt-1 max-h-56 space-y-1 overflow-y-auto pr-2">
              {history.result.timeline.map((entry, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <Badge label={entry.source_type} styles={EVIDENCE_STYLES} />
                  <span>
                    <span className="text-slate-400">{entry.month}:</span> {entry.description}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

export function ReviewEvidencePanel({
  review,
  question,
  onQuestionChange,
  onAsk,
}: {
  review: ReviewEvidenceState;
  question: string;
  onQuestionChange: (value: string) => void;
  onAsk: () => void;
}) {
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
          className="w-80 max-w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
          placeholder="What does the latest review report say about this project?"
        />
        <button
          onClick={onAsk}
          disabled={review.status === "loading"}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:bg-slate-300"
        >
          Search
        </button>
        {review.status === "success" && (
          <SourceBadge source={review.result.summary_source} model={review.result.summary_model} />
        )}
      </div>

      {review.status === "loading" && <p className="mt-3 text-sm text-slate-400">Searching review reports…</p>}
      {review.status === "error" && <p className="mt-3 text-sm text-red-600">{review.message}</p>}

      {review.status === "success" && (
        <div className="mt-4 space-y-4">
          <div>
            <h4 className="text-xs font-semibold uppercase text-slate-500">Answer</h4>
            <p className="mt-1 text-sm text-slate-800">{review.result.answer}</p>
            {!review.result.evidence_found && (
              <p className="mt-1 text-xs text-amber-600">
                No relevant evidence was retrieved from the indexed review reports.
              </p>
            )}
          </div>

          {review.result.citations.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-500">
                Citations ({review.result.citations.length})
              </h4>
              <ul className="mt-1 space-y-2">
                {review.result.citations.map((c, i) => (
                  <li key={i} className="rounded border border-slate-200 bg-white p-2 text-sm">
                    <div className="text-xs font-medium text-slate-700">
                      {c.document_name}, p.{c.page}{" "}
                      <span className="font-normal text-slate-400">(score {c.score.toFixed(3)})</span>
                    </div>
                    <div className="mt-1 text-xs text-slate-500">{c.excerpt}</div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function WebEvidencePanel({ web, onSearch }: { web: WebEvidenceState; onSearch: (force: boolean) => void }) {
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => onSearch(false)}
          disabled={web.status === "loading"}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:bg-slate-300"
        >
          Check
        </button>
        <button
          onClick={() => onSearch(true)}
          disabled={web.status === "loading"}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:text-slate-300"
        >
          Force search
        </button>
      </div>

      {web.status === "loading" && <p className="mt-3 text-sm text-slate-400">Searching…</p>}
      {web.status === "error" && <p className="mt-3 text-sm text-red-600">{web.message}</p>}

      {web.status === "success" && (
        <div className="mt-4 space-y-4">
          <p className="text-sm text-slate-700">
            <span className={web.result.triggered ? "text-emerald-700" : "text-slate-500"}>
              {web.result.triggered ? "Search triggered" : "Not triggered"}
            </span>
            {" — "}
            {web.result.trigger_reason}
          </p>

          {web.result.topics_searched.length > 0 && (
            <p className="text-xs text-slate-500">Topics: {web.result.topics_searched.join(", ")}</p>
          )}

          {web.result.warnings.length > 0 && (
            <ul className="space-y-1">
              {web.result.warnings.map((w, i) => (
                <li key={i} className="text-xs text-amber-600">
                  {w}
                </li>
              ))}
            </ul>
          )}

          {web.result.triggered && web.result.evidence.length === 0 && web.result.warnings.length === 0 && (
            <p className="text-sm text-slate-500">No external evidence found.</p>
          )}

          {web.result.evidence.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-500">
                Evidence ({web.result.evidence.length})
              </h4>
              <ul className="mt-1 space-y-2">
                {web.result.evidence.map((item) => (
                  <li key={item.evidence_id} className="rounded border border-slate-200 bg-white p-2 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge label={item.source_quality} styles={SOURCE_QUALITY_STYLES} />
                      <span className="text-xs font-medium text-slate-700">{item.source}</span>
                      <span className="text-xs text-slate-400">
                        {item.publication_date ?? "undated"}
                        {item.date_confidence === "UNVERIFIED" ? " (unverified date)" : ""}
                      </span>
                      <span className="text-xs text-slate-400">topic: {item.topic}</span>
                    </div>
                    <div className="mt-1 text-slate-800">{item.finding}</div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                      <span>relevance {(item.project_relevance * 100).toFixed(0)}%</span>
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                        className="truncate text-slate-500 underline hover:text-slate-700"
                      >
                        {item.url}
                      </a>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function DiagnosisPanel({ diagnosis, onRun }: { diagnosis: DiagnosisState; onRun: () => void }) {
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={onRun}
          disabled={diagnosis.status === "loading"}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:bg-slate-300"
        >
          {diagnosis.status === "success" ? "Re-run diagnosis" : "Diagnose"}
        </button>
        {diagnosis.status === "success" && (
          <span className="text-xs text-slate-500">fusion: {diagnosis.result.fusion_version}</span>
        )}
      </div>

      {diagnosis.status === "loading" && <p className="mt-3 text-sm text-slate-400">Fusing evidence…</p>}
      {diagnosis.status === "error" && <p className="mt-3 text-sm text-red-600">{diagnosis.message}</p>}

      {diagnosis.status === "success" && (
        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Badge label={diagnosis.result.overall_risk} styles={SEVERITY_STYLES} />
            {diagnosis.result.risk_score !== null && (
              <span className="text-sm text-slate-700">risk score {diagnosis.result.risk_score.toFixed(1)}</span>
            )}
            <span className="text-xs text-slate-500">
              confidence {(diagnosis.result.confidence * 100).toFixed(0)}%
            </span>
          </div>

          {diagnosis.result.drivers.length === 0 && (
            <p className="text-sm text-slate-500">No risk drivers identified.</p>
          )}

          {diagnosis.result.drivers.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-500">
                Risk Drivers ({diagnosis.result.drivers.length})
              </h4>
              <ul className="mt-1 space-y-2">
                {diagnosis.result.drivers.map((d) => {
                  const items = d.evidence_ids
                    .map((id) => diagnosis.result.evidence.find((e) => e.evidence_id === id))
                    .filter((e): e is NonNullable<typeof e> => Boolean(e));
                  return (
                    <li key={d.rank} className="rounded border border-slate-200 bg-white p-2 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-400">#{d.rank}</span>
                        <Badge label={d.severity} styles={SEVERITY_STYLES} />
                        <span className="font-medium text-slate-800">{d.driver}</span>
                      </div>
                      {items.length > 0 && (
                        <ul className="mt-2 space-y-1 pl-4">
                          {items.map((e) => (
                            <li key={e.evidence_id} className="flex items-start gap-2 text-xs text-slate-600">
                              <Badge label={e.category} styles={EVIDENCE_CATEGORY_STYLES} />
                              <span>{e.description}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          <div>
            <h4 className="text-xs font-semibold uppercase text-slate-500">
              Full Evidence Pool ({diagnosis.result.evidence.length})
            </h4>
            <ul className="mt-1 max-h-56 space-y-1 overflow-y-auto pr-2">
              {diagnosis.result.evidence.map((e) => (
                <li key={e.evidence_id} className="flex items-start gap-2 text-xs text-slate-600">
                  <Badge label={e.category} styles={EVIDENCE_CATEGORY_STYLES} />
                  <span>{e.description}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

export function InterventionPanel({
  intervention,
  onRun,
}: {
  intervention: InterventionState;
  onRun: () => void;
}) {
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={onRun}
          disabled={intervention.status === "loading"}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:bg-slate-300"
        >
          {intervention.status === "success" ? "Re-run" : "Recommend actions"}
        </button>
      </div>

      {intervention.status === "loading" && (
        <p className="mt-3 text-sm text-slate-400">Diagnosing and mapping actions…</p>
      )}
      {intervention.status === "error" && <p className="mt-3 text-sm text-red-600">{intervention.message}</p>}

      {intervention.status === "success" && (
        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Badge label={intervention.result.overall_risk} styles={SEVERITY_STYLES} />
            <span className="text-xs text-slate-500">
              suggested monitoring level: {intervention.result.suggested_monitoring_level}
            </span>
          </div>

          {intervention.result.recommendations.length === 0 && (
            <p className="text-sm text-slate-500">No recommendations - no risk drivers identified.</p>
          )}

          {intervention.result.recommendations.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-500">
                Recommended Monitoring Actions ({intervention.result.recommendations.length})
              </h4>
              <ul className="mt-1 space-y-2">
                {intervention.result.recommendations.map((r, i) => (
                  <li key={i} className="rounded border border-slate-200 bg-white p-2 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge label={r.priority} styles={SEVERITY_STYLES} />
                      <Badge label={r.action_type} styles={ACTION_TYPE_STYLES} />
                      <span className="text-xs text-slate-400">{r.review_area}</span>
                    </div>
                    <div className="mt-1 font-medium text-slate-800">{r.action}</div>
                    <div className="mt-1 text-xs text-slate-500">{r.reason}</div>
                    <div className="mt-1 text-xs text-slate-400">
                      {r.evidence_ids.length} evidence item(s)
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
