"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import { analyzeQuery, AnalysisResponse } from "@/lib/api";
import { useARIA } from "./ARIAContext";

interface Message {
  id: string;
  role: "user" | "aria" | "error";
  text: string;
  timestamp: Date;
}

const PORTFOLIO_STARTERS = [
  "Which projects are at highest risk?",
  "Show me all CRITICAL health projects",
  "What are the top concerns this month?",
];

const PROJECT_STARTERS = [
  "What is the current status of this project?",
  "What are the key risk drivers?",
  "What actions should be taken?",
  "What does the review report say?",
];

function formatResponse(res: AnalysisResponse): string {
  // If report exists, use the executive summary
  if (res.report?.executive_summary) {
    let text = res.report.executive_summary;

    if (res.report.top_risk_drivers?.length) {
      text += "\n\n**Top Risk Drivers:**\n" +
        res.report.top_risk_drivers
          .slice(0, 3)
          .map((d) => `• [${d.severity}] ${d.driver}`)
          .join("\n");
    }

    if (res.report.recommended_monitoring_actions?.length) {
      text += "\n\n**Recommended Actions:**\n" +
        res.report.recommended_monitoring_actions
          .slice(0, 3)
          .map((a) => `• [${a.priority}] ${a.action}`)
          .join("\n");
    }

    return text;
  }

  // Fallback: show stage results
  const stages = res.stage_results
    ?.filter((s) => s.status === "success" || s.error)
    .map((s) => s.error ? `${s.stage}: ${s.error}` : `${s.stage}: completed`)
    .join("\n");
  if (stages) return stages;

  // Fallback: errors
  if (res.errors?.length) return "I encountered an issue: " + res.errors.join("; ");

  return "I've processed your query but couldn't find a detailed result. Try rephrasing your question.";
}

function renderText(text: string) {
  // Simple markdown-like rendering
  return text.split("\n").map((line, i) => {
    if (line.startsWith("**") && line.endsWith("**")) {
      return <p key={i} className="font-semibold text-slate-800 mt-2 mb-0.5 text-xs uppercase tracking-wide">{line.replace(/\*\*/g, "")}</p>;
    }
    if (line.startsWith("• ")) {
      return <p key={i} className="flex gap-1.5 text-sm text-slate-700"><span className="text-slate-400 shrink-0">•</span>{line.slice(2)}</p>;
    }
    if (line.trim() === "") return <div key={i} className="h-1" />;
    return <p key={i} className="text-sm text-slate-800 leading-relaxed">{line}</p>;
  });
}

export default function ARIAChat() {
  const { mode, projectId, projectName } = useARIA();

  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initialized, setInitialized] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Build greeting based on mode
  const greeting: Message = {
    id: "greeting",
    role: "aria",
    text:
      mode === "project" && projectName
        ? `Hi! I'm **ARIA** — your AI Risk & Intelligence Assistant.\n\nI'm focused on **${projectName}**. Ask me anything about this project — its health, risk drivers, history, review findings, or recommended actions.`
        : `Hi! I'm **ARIA** — your AI Risk & Intelligence Assistant.\n\nI have access to the full project portfolio and all monitoring agents. Ask me about any project, portfolio risk, or overall status.`,
    timestamp: new Date(),
  };

  // Reset messages when project context changes
  useEffect(() => {
    setMessages([]);
    setInitialized(false);
  }, [projectId]);

  // Add greeting when opened for the first time
  useEffect(() => {
    if (open && !initialized) {
      setMessages([greeting]);
      setInitialized(true);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open, initialized]);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      text: text.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await analyzeQuery(text.trim(), projectId ?? undefined);
      const ariaMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "aria",
        text: formatResponse(res),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, ariaMsg]);
    } catch (err: any) {
      const errMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "error",
        text: err?.message || "I couldn't reach the backend. Please check if the server is running.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    sendMessage(input);
  }

  const starters = mode === "project" ? PROJECT_STARTERS : PORTFOLIO_STARTERS;

  return (
    <>
      {/* ── Floating Button ── */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Open ARIA chat"
        className={`fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full shadow-xl transition-all duration-300 print:hidden ${
          open
            ? "bg-slate-800 rotate-45 scale-95"
            : "bg-gradient-to-br from-violet-600 to-indigo-700 hover:scale-110"
        }`}
      >
        {open ? (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
            <line x1="4" y1="4" x2="16" y2="16" /><line x1="16" y1="4" x2="4" y2="16" />
          </svg>
        ) : (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            <circle cx="9" cy="10" r="1" fill="white" /><circle cx="12" cy="10" r="1" fill="white" /><circle cx="15" cy="10" r="1" fill="white" />
          </svg>
        )}
        {!open && (
          <span className="absolute -top-1 -right-1 flex h-4 w-4">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-4 w-4 bg-violet-500" />
          </span>
        )}
      </button>

      {/* ── Chat Panel ── */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 flex w-80 flex-col rounded-2xl border border-slate-200 bg-white shadow-2xl overflow-hidden print:hidden"
          style={{ height: "480px" }}>

          {/* Header */}
          <div className="flex items-center gap-3 bg-gradient-to-r from-violet-700 to-indigo-700 px-4 py-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/20 text-white font-bold text-sm">
              A
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white font-semibold text-sm">ARIA</div>
              <div className="text-violet-200 text-xs truncate">
                {mode === "project" && projectName
                  ? `📌 ${projectName}`
                  : "🌐 Portfolio Intelligence"}
              </div>
            </div>
            <div className="flex h-2 w-2 rounded-full bg-emerald-400" title="Online" />
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 bg-slate-50">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col gap-0.5 ${msg.role === "user" ? "items-end" : "items-start"}`}
              >
                {msg.role !== "user" && (
                  <span className="text-xs text-slate-400 px-1">ARIA</span>
                )}
                <div
                  className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                    msg.role === "user"
                      ? "bg-violet-600 text-white rounded-br-sm"
                      : msg.role === "error"
                      ? "bg-red-50 border border-red-200 text-red-700 rounded-bl-sm"
                      : "bg-white border border-slate-200 text-slate-800 rounded-bl-sm shadow-sm"
                  }`}
                >
                  {msg.role === "user" ? (
                    <p className="text-sm">{msg.text}</p>
                  ) : (
                    <div className="space-y-0.5">{renderText(msg.text)}</div>
                  )}
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {loading && (
              <div className="flex items-start gap-1">
                <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-sm px-3 py-2.5 shadow-sm">
                  <div className="flex gap-1 items-center h-4">
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-bounce"
                        style={{ animationDelay: `${i * 150}ms` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Starter suggestions — shown only when no messages beyond greeting */}
          {messages.length <= 1 && !loading && (
            <div className="px-3 py-2 border-t border-slate-100 bg-white">
              <p className="text-xs text-slate-400 mb-1.5">Suggested questions</p>
              <div className="flex flex-col gap-1">
                {starters.slice(0, 3).map((s) => (
                  <button
                    key={s}
                    onClick={() => sendMessage(s)}
                    className="text-left text-xs text-violet-700 bg-violet-50 hover:bg-violet-100 rounded-lg px-2.5 py-1.5 transition-colors border border-violet-100"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <form onSubmit={handleSubmit} className="flex items-center gap-2 border-t border-slate-200 bg-white px-3 py-2.5">
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                mode === "project" ? "Ask about this project…" : "Ask about the portfolio…"
              }
              disabled={loading}
              className="flex-1 min-w-0 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-violet-400 focus:outline-none focus:bg-white disabled:opacity-50 transition-colors"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-600 text-white hover:bg-violet-700 disabled:bg-slate-200 disabled:text-slate-400 transition-colors"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </form>
        </div>
      )}
    </>
  );
}
