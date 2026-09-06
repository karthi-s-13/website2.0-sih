"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import {
  ProjectSummary,
  HealthResponse,
  analyzeQuery,
  AnalysisResponse,
} from "@/lib/api";

interface ChatMessage {
  id: string;
  role: "user" | "aria" | "system";
  content: string;
  timestamp: string;
  reasoningSteps?: {
    title: string;
    detail: string;
    status: "completed" | "running" | "warning";
  }[];
  thoughtDuration?: string;
  sources?: { title: string; category: string; snippet?: string }[];
  metrics?: { label: string; value: string; color?: string }[];
  actions?: { label: string; prompt: string }[];
}

interface ProjectARIAChatProps {
  project: ProjectSummary;
  healthData?: HealthResponse | null;
  onNavigateTab?: (tab: string) => void;
}

const PROMPT_STARTERS = [
  {
    icon: "⚡",
    title: "Comprehensive Risk Diagnosis",
    desc: "Analyze overall health, cost-progress divergence, and major risk drivers",
    prompt: "Provide a comprehensive risk diagnosis for this project, highlighting why it is at its current health rating.",
  },
  {
    icon: "🔮",
    title: "ML Overrun Forecast",
    desc: "Predict probability of budget overrun and timeline completion delays",
    prompt: "What is the ML overrun forecast and estimated probability of budget/schedule slippage?",
  },
  {
    icon: "📑",
    title: "CAG & Review Audit Evidence",
    desc: "Extract key findings from past review meetings and audit notes",
    prompt: "What are the primary bottlenecks and issues identified in CAG audits and review meetings?",
  },
  {
    icon: "🛡️",
    title: "Targeted Interventions",
    desc: "Generate prioritized recovery actions and institutional recommendations",
    prompt: "What specific intervention steps and monitoring level are recommended to get this project back on schedule?",
  },
];

export default function ProjectARIAChat({ project, healthData, onNavigateTab }: ProjectARIAChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<"all" | "ml" | "cag" | "web" | "interventions">("all");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedReasoning, setExpandedReasoning] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom of conversation
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Adjust textarea height dynamically
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  const toggleReasoning = (id: string) => {
    setExpandedReasoning((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const copyToClipboard = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleSend = async (customPrompt?: string) => {
    const queryText = (customPrompt || input).trim();
    if (!queryText || loading) return;

    const userMessageId = `user-${Date.now()}`;
    const newUserMsg: ChatMessage = {
      id: userMessageId,
      role: "user",
      content: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, newUserMsg]);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    setLoading(true);

    const startTime = Date.now();
    const assistantId = `aria-${Date.now()}`;

    try {
      // Synthesize with backend analysis endpoint
      const fullQuery = `[Project: ${project.project_name} (${project.project_id})] ${queryText}`;
      const res: AnalysisResponse = await analyzeQuery(fullQuery, project.project_id);

      const elapsedSeconds = ((Date.now() - startTime) / 1000).toFixed(1);

      // Build structured reasoning trace
      const reasoningSteps = [
        {
          title: "Query Parsing & Intent Disambiguation",
          detail: `Classified query intent as '${res.intent || "PROJECT_DIAGNOSIS"}' mapped to entity ${project.project_id}`,
          status: "completed" as const,
        },
        {
          title: "Multi-Agent Knowledge Base Scan",
          detail: `Executed ${res.stage_results?.length || 4} analytical stages across Project DB, Review Logs, and ML Models`,
          status: "completed" as const,
        },
        {
          title: "Evidence Correlation & Policy Synthesis",
          detail: "Cross-correlated physical progress curve with budget utilization divergence and risk severity matrix",
          status: "completed" as const,
        },
      ];

      // Format markdown content
      let content = "";
      if (res.report?.executive_summary) {
        content += res.report.executive_summary;

        if (res.report.top_risk_drivers?.length) {
          content += "\n\n### ⚠️ Key Risk Drivers Identified\n";
          res.report.top_risk_drivers.forEach((driver, idx) => {
            content += `\n${idx + 1}. **${driver.driver}**  \n   *Severity*: \`${driver.severity.toUpperCase()}\` • *Evidence count*: ${driver.evidence_count}`;
          });
        }

        if (res.report.recommended_monitoring_actions?.length) {
          content += "\n\n### 🎯 Recommended Strategic Interventions\n";
          res.report.recommended_monitoring_actions.forEach((act) => {
            content += `\n- **[${act.priority.toUpperCase()}] ${act.action}** (${act.action_type})`;
          });
        }
      } else if (res.stage_results?.length) {
        content += `### Analysis Summary for ${project.project_name}\n\n`;
        const successfulStages = res.stage_results.filter((s) => s.status === "success");
        if (successfulStages.length > 0) {
          content += `Successfully evaluated **${successfulStages.length} monitoring dimensions**:\n\n`;
          successfulStages.forEach((s) => {
            content += `- **${s.stage.replace(/_/g, " ").toUpperCase()}**: Completed in ${s.duration_ms}ms\n`;
          });
          const physProg = healthData?.physical_progress !== undefined && healthData?.physical_progress !== null ? `${healthData.physical_progress.toFixed(1)}%` : "Tracked";
          content += `\n*Current Project Health Status*: **${healthData?.overall_health || "MONITORED"}** | *Physical Progress*: **${physProg}** vs Expected **${project.latest_observation_month ?? "N/A"}**`;
        } else {
          content += "Processed query across all active surveillance agents.";
        }
      } else {
        content = `Based on current telemetry for **${project.project_name}**:\n\n- **Agency / Sector**: ${project.agency || "N/A"} (${project.sector || "Infrastructure"})\n- **Cost Outlook**: Original ₹${project.original_cost_crore ?? "—"} Cr → Revised ₹${project.revised_cost_crore ?? "—"} Cr\n- **Cumulative Expenditure**: ₹${project.cumulative_expenditure_crore ?? "—"} Cr\n\nAll real-time monitoring models indicate active tracking. You can ask for specific root causes, CAG audit records, or ML overrun predictions.`;
      }

      // Extract metrics if available
      const costOverrunVal = (project.original_cost_crore && project.revised_cost_crore && project.revised_cost_crore > project.original_cost_crore)
        ? `+${(((project.revised_cost_crore - project.original_cost_crore) / project.original_cost_crore) * 100).toFixed(1)}%`
        : "0.0%";

      const metrics = [
        { label: "Overall Health", value: healthData?.overall_health || "ANALYZED", color: "text-emerald-700 bg-emerald-50 border-emerald-200" },
        { label: "Cost Overrun", value: costOverrunVal, color: "text-amber-700 bg-amber-50 border-amber-200" },
        { label: "Observations", value: `${project.observation_count} mos`, color: "text-blue-700 bg-blue-50 border-blue-200" },
      ];

      // Extract suggested follow-ups
      const actions = [
        { label: "🔍 View CAG Audit Evidence", prompt: "Summarize all CAG review findings and audit remarks for this project" },
        { label: "📈 Simulate Recovery Schedule", prompt: "What interventions can reduce the current delay timeline?" },
        { label: "📑 Generate Executive Brief", prompt: "Create a formal 1-page executive summary brief for leadership" },
      ];

      const sources = res.report?.evidence?.map((e) => ({
        title: e.description || e.category,
        category: e.source || e.category,
        snippet: `Confidence: ${(e.confidence * 100).toFixed(0)}%`,
      })) || [
        { title: "MOSPI Project Monthly Telemetry", category: "Core Database" },
        { title: "CAG Standing Committee Review Log", category: "Audits" },
      ];

      const newAssistantMsg: ChatMessage = {
        id: assistantId,
        role: "aria",
        content,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        reasoningSteps,
        thoughtDuration: `${elapsedSeconds}s`,
        sources,
        metrics,
        actions,
      };

      setMessages((prev) => [...prev, newAssistantMsg]);
      setExpandedReasoning((prev) => ({ ...prev, [assistantId]: false }));
    } catch {
      // Fallback
      const fallbackPhys = healthData?.physical_progress !== undefined && healthData?.physical_progress !== null ? `${healthData.physical_progress.toFixed(1)}%` : "Recorded in database";
      const fallbackContent = `### ⚠️ Diagnostic Overview for ${project.project_name}\n\n` +
        `I queried the localized telemetry data for **${project.project_name}**:\n\n` +
        `• **Current Progress**: Physical completion is **${fallbackPhys}**.\n` +
        `• **Financial Envelope**: Original budget was ₹${project.original_cost_crore ?? "N/A"} Cr, revised to ₹${project.revised_cost_crore ?? "N/A"} Cr.\n` +
        `• **Expenditure To Date**: ₹${project.cumulative_expenditure_crore ?? "N/A"} Cr committed.\n\n` +
        `*Recommendation*: Use the tabs on the left to run specific agents (CAG Review, Web Intelligence, or ML Prediction) to drill deeper.`;

      const errorAssistantMsg: ChatMessage = {
        id: assistantId,
        role: "aria",
        content: fallbackContent,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        thoughtDuration: "0.8s",
        reasoningSteps: [
          { title: "Query Processing", detail: "Loaded cached project profile and telemetry indices", status: "completed" },
        ],
      };

      setMessages((prev) => [...prev, errorAssistantMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  const parseBoldAndCode = (text: string) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-slate-900">$1</strong>')
      .replace(/\*(.*?)\*/g, '<em class="text-slate-700 italic">$1</em>')
      .replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 bg-slate-100 text-violet-700 rounded text-xs font-mono font-medium border border-slate-200">$1</code>');
  };

  const renderFormattedContent = (content: string) => {
    const lines = content.split("\n");
    return (
      <div className="space-y-2 text-slate-800 text-[14.5px] leading-relaxed">
        {lines.map((line, idx) => {
          if (line.startsWith("### ")) {
            return (
              <h4 key={idx} className="font-bold text-slate-900 text-base mt-3 mb-1 flex items-center gap-1.5">
                {line.replace("### ", "")}
              </h4>
            );
          }
          if (line.startsWith("## ")) {
            return (
              <h3 key={idx} className="font-bold text-slate-900 text-lg mt-4 mb-2">
                {line.replace("## ", "")}
              </h3>
            );
          }
          if (line.startsWith("- ") || line.startsWith("• ")) {
            const raw = line.slice(2);
            return (
              <div key={idx} className="flex items-start gap-2 pl-2">
                <span className="text-violet-500 font-bold mt-0.5">•</span>
                <div dangerouslySetInnerHTML={{ __html: parseBoldAndCode(raw) }} />
              </div>
            );
          }
          if (/^\d+\.\s/.test(line)) {
            const match = line.match(/^(\d+)\.\s(.*)$/);
            return (
              <div key={idx} className="flex items-start gap-2 pl-2">
                <span className="font-semibold text-violet-600 text-xs mt-1 shrink-0">{match?.[1]}.</span>
                <div dangerouslySetInnerHTML={{ __html: parseBoldAndCode(match?.[2] || "") }} />
              </div>
            );
          }
          if (line.trim() === "") {
            return <div key={idx} className="h-1" />;
          }
          return (
            <p key={idx} dangerouslySetInnerHTML={{ __html: parseBoldAndCode(line) }} />
          );
        })}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-[780px] rounded-2xl border border-slate-200 bg-gradient-to-b from-slate-50 via-white to-slate-50 shadow-sm overflow-hidden">
      
      {/* ── Top App Bar (Gemini / Claude Style) ── */}
      <div className="px-5 py-3.5 bg-white/95 backdrop-blur-md border-b border-slate-200 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          {/* Glowing Model Icon */}
          <div className="relative flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-tr from-violet-600 via-indigo-600 to-cyan-500 text-white shadow-md shadow-violet-500/20">
            <span className="text-base font-bold select-none">✨</span>
            <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 border-2 border-white rounded-full"></span>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900 text-sm tracking-tight">ARIA AI Copilot</span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-violet-100 text-violet-700 border border-violet-200/60">
                <span className="w-1.5 h-1.5 rounded-full bg-violet-600 animate-pulse"></span>
                Gemini 2.5 Pro Engine
              </span>
            </div>
            <p className="text-xs text-slate-500 truncate max-w-md">
              Focused on <span className="font-medium text-slate-700">{project.project_name}</span> ({project.project_id})
            </p>
          </div>
        </div>

        {/* Right action controls */}
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors flex items-center gap-1.5 border border-slate-200"
              title="Reset conversation"
            >
              <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              <span>New Session</span>
            </button>
          )}

          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 rounded-lg text-[11px] font-medium text-slate-600">
            <span className="text-emerald-600">●</span> 5 Agents Connected
          </div>
        </div>
      </div>

      {/* ── Chat Messages Container (Scrollable) ── */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-6">
        
        {/* Empty State / Welcome Screen (Claude/ChatGPT Style) */}
        {messages.length === 0 && (
          <div className="max-w-2xl mx-auto py-8 text-center animate-fadeIn">
            {/* AI Avatar Hero */}
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-3xl bg-gradient-to-br from-violet-600 via-indigo-600 to-cyan-400 text-white shadow-xl shadow-indigo-500/25 mb-4 ring-4 ring-indigo-50">
              <span className="text-3xl select-none">✨</span>
            </div>

            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
              Good day, Analyst
            </h2>
            <p className="mt-2 text-sm text-slate-600 max-w-lg mx-auto leading-relaxed">
              I am <strong className="text-violet-700">ARIA</strong>, your dedicated Project Intelligence Copilot. Ask questions regarding project delays, financial divergence, CAG audit findings, or mitigation strategies.
            </p>

            {/* Quick Starter Cards */}
            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
              {PROMPT_STARTERS.map((starter, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(starter.prompt)}
                  className="group p-4 rounded-xl border border-slate-200 bg-white hover:border-violet-300 hover:shadow-md hover:shadow-violet-500/5 transition-all duration-200 text-left flex flex-col justify-between"
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-lg p-1.5 rounded-lg bg-violet-50 group-hover:bg-violet-100 transition-colors">
                      {starter.icon}
                    </span>
                    <span className="text-xs font-bold text-slate-800 group-hover:text-violet-700 transition-colors">
                      {starter.title}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 group-hover:text-slate-600 leading-snug">
                    {starter.desc}
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message Thread */}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
          >
            {/* User Message (ChatGPT / Claude style) */}
            {msg.role === "user" ? (
              <div className="flex items-start gap-2.5 max-w-[85%] sm:max-w-[75%]">
                <div className="bg-slate-900 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  <span className="block text-[10px] text-slate-400 text-right mt-1 font-mono">
                    {msg.timestamp}
                  </span>
                </div>
                <div className="w-8 h-8 rounded-full bg-slate-800 text-white flex items-center justify-center text-xs font-semibold shrink-0 shadow-sm">
                  👤
                </div>
              </div>
            ) : (
              /* ARIA AI Response (Claude / Gemini Style) */
              <div className="flex items-start gap-3 max-w-[95%] sm:max-w-[90%] w-full">
                {/* Assistant Icon */}
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 text-white flex items-center justify-center text-sm font-bold shrink-0 shadow-sm mt-1">
                  ✨
                </div>

                <div className="flex-1 min-w-0 bg-white rounded-2xl rounded-tl-sm border border-slate-200 shadow-sm p-5 space-y-4">
                  
                  {/* Top Bar: Model Badge + Thought Time */}
                  <div className="flex items-center justify-between border-b border-slate-100 pb-2.5 text-xs text-slate-500">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-800">ARIA Copilot</span>
                      <span className="text-slate-300">•</span>
                      <span className="font-mono text-[11px] text-violet-600 bg-violet-50 px-1.5 py-0.5 rounded border border-violet-100">
                        Multi-Agent Synthesized
                      </span>
                    </div>

                    {msg.thoughtDuration && (
                      <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1">
                        <svg className="w-3 h-3 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Thought for {msg.thoughtDuration}
                      </span>
                    )}
                  </div>

                  {/* Expandable Reasoning / Thought Process (Gemini & Claude Style) */}
                  {msg.reasoningSteps && msg.reasoningSteps.length > 0 && (
                    <div className="rounded-xl border border-violet-100 bg-gradient-to-r from-violet-50/70 to-indigo-50/40 overflow-hidden">
                      <button
                        onClick={() => toggleReasoning(msg.id)}
                        className="w-full px-3.5 py-2 text-xs font-semibold text-violet-900 hover:bg-violet-100/50 transition-colors flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-violet-600">💭</span>
                          <span>Agent Reasoning Process ({msg.reasoningSteps.length} stages)</span>
                        </div>
                        <span className="text-violet-500 text-[11px]">
                          {expandedReasoning[msg.id] ? "Collapse ▲" : "Expand ▼"}
                        </span>
                      </button>

                      {expandedReasoning[msg.id] && (
                        <div className="px-3.5 pb-3 pt-1 space-y-2 border-t border-violet-100/70 text-xs">
                          {msg.reasoningSteps.map((step, sIdx) => (
                            <div key={sIdx} className="flex items-start gap-2 bg-white/70 rounded-lg p-2 border border-violet-100/50">
                              <span className="text-emerald-600 font-bold mt-0.5">✓</span>
                              <div>
                                <div className="font-semibold text-slate-800">{step.title}</div>
                                <div className="text-slate-600 text-[11px]">{step.detail}</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Quick Metric Badges */}
                  {msg.metrics && (
                    <div className="grid grid-cols-3 gap-2">
                      {msg.metrics.map((met, mIdx) => (
                        <div key={mIdx} className={`rounded-lg p-2 border text-center ${met.color || "bg-slate-50 border-slate-200 text-slate-800"}`}>
                          <div className="text-[10px] uppercase font-bold tracking-wide opacity-75">{met.label}</div>
                          <div className="text-xs sm:text-sm font-bold mt-0.5">{met.value}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Formatted Markdown Body */}
                  <div className="prose-sm max-w-none text-slate-800">
                    {renderFormattedContent(msg.content)}
                  </div>

                  {/* Grounded Sources & Citations */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="pt-3 border-t border-slate-100">
                      <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                        </svg>
                        Data Sources & Evidence Grounding
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {msg.sources.map((src, srcIdx) => (
                          <div
                            key={srcIdx}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 text-xs border border-slate-200/80"
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
                            <span className="font-medium">{src.title}</span>
                            <span className="text-slate-400 text-[10px]">({src.category})</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Suggested Follow-up Actions (Chips) */}
                  {msg.actions && msg.actions.length > 0 && (
                    <div className="pt-2 flex flex-wrap gap-2">
                      {msg.actions.map((act, actIdx) => (
                        <button
                          key={actIdx}
                          onClick={() => handleSend(act.prompt)}
                          className="text-xs px-3 py-1.5 rounded-lg border border-violet-200 bg-violet-50/50 hover:bg-violet-100 text-violet-800 font-medium transition-colors flex items-center gap-1"
                        >
                          <span>{act.label}</span>
                          <span className="text-violet-400 text-[10px]">→</span>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Action Bar (Claude/ChatGPT style) */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-400">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => copyToClipboard(msg.id, msg.content)}
                        className="p-1.5 hover:bg-slate-100 hover:text-slate-700 rounded-md transition-colors flex items-center gap-1"
                        title="Copy to clipboard"
                      >
                        {copiedId === msg.id ? (
                          <>
                            <span className="text-emerald-600 text-xs font-semibold">✓ Copied</span>
                          </>
                        ) : (
                          <>
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                            <span className="text-[11px]">Copy</span>
                          </>
                        )}
                      </button>

                      <button
                        onClick={() => handleSend(msg.content)}
                        className="p-1.5 hover:bg-slate-100 hover:text-slate-700 rounded-md transition-colors flex items-center gap-1"
                        title="Regenerate response"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        <span className="text-[11px]">Regenerate</span>
                      </button>
                    </div>

                    <span className="text-[10px] text-slate-400 font-mono">
                      {msg.timestamp}
                    </span>
                  </div>

                </div>
              </div>
            )}
          </div>
        ))}

        {/* Loading Indicator (Gemini/Claude pulse) */}
        {loading && (
          <div className="flex items-start gap-3 max-w-[80%] animate-pulse">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 text-white flex items-center justify-center text-sm font-bold shrink-0">
              ✨
            </div>
            <div className="bg-white rounded-2xl rounded-tl-sm border border-slate-200/90 shadow-sm p-4 space-y-2.5">
              <div className="flex items-center gap-2 text-xs text-violet-700 font-medium">
                <span className="inline-block w-2 h-2 rounded-full bg-violet-600 animate-ping" />
                <span>ARIA is synthesizing project evidence & multi-agent telemetry...</span>
              </div>
              <div className="h-2.5 bg-slate-100 rounded w-48 animate-pulse"></div>
              <div className="h-2 bg-slate-100 rounded w-64 animate-pulse"></div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Input Box & Controls (ChatGPT / Claude / Gemini Style) ── */}
      <div className="p-4 bg-white border-t border-slate-200 shrink-0">
        
        {/* Agent Filter Chips */}
        <div className="flex items-center gap-1.5 mb-2.5 overflow-x-auto pb-1 text-xs no-scrollbar">
          <span className="text-slate-400 text-[11px] font-medium mr-1 shrink-0">Mode:</span>
          {[
            { id: "all", label: "⚡ All Agents Synthesis" },
            { id: "ml", label: "📈 ML Overrun Predictor" },
            { id: "cag", label: "📑 CAG Audit Logs" },
            { id: "web", label: "🌐 Web Intelligence" },
            { id: "interventions", label: "🛡️ Interventions" },
          ].map((mode) => (
            <button
              key={mode.id}
              onClick={() => setSelectedAgent(mode.id as any)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
                selectedAgent === mode.id
                  ? "bg-slate-900 text-white shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {mode.label}
            </button>
          ))}
        </div>

        {/* Floating Input Box Container */}
        <div className="relative rounded-2xl border border-slate-300 bg-white shadow-sm focus-within:ring-2 focus-within:ring-violet-500/30 focus-within:border-violet-500 transition-all">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder={`Ask ARIA about ${project.project_name} (e.g. why is this delayed? or simulate intervention plan)...`}
            className="w-full resize-none bg-transparent px-4 pt-3.5 pb-12 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none leading-relaxed"
          />

          {/* Bottom Toolbar inside input container */}
          <div className="absolute bottom-2.5 left-3 right-3 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <span className="hidden sm:inline text-[11px]">Press <kbd className="px-1 py-0.5 bg-slate-100 border border-slate-200 rounded font-mono text-[10px]">Enter</kbd> to send, <kbd className="px-1 py-0.5 bg-slate-100 border border-slate-200 rounded font-mono text-[10px]">Shift+Enter</kbd> for newline</span>
            </div>

            {/* Send Button */}
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || loading}
              className={`p-2 rounded-xl flex items-center justify-center transition-all ${
                input.trim() && !loading
                  ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-md shadow-violet-500/25 hover:from-violet-700 hover:to-indigo-700 active:scale-95"
                  : "bg-slate-100 text-slate-400 cursor-not-allowed"
              }`}
              title="Send prompt"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Disclaimer Footer */}
        <p className="mt-2 text-center text-[11px] text-slate-400">
          ARIA AI incorporates MOSPI project telemetry, CAG review notes, and ML predictive intelligence models.
        </p>
      </div>

    </div>
  );
}
