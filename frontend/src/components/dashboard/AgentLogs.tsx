"use client";

import { useEffect, useState, useCallback } from "react";
import { RefreshCw } from "lucide-react";
import {
  fetchAgentRuns,
  fetchAgentRunDetail,
  type AgentRun,
  type AgentRunDetail,
  fmtTimeFull,
} from "@/lib/api";

const statusColor: Record<string, string> = {
  running:   "#4f6eff",
  completed: "#22d3a0",
  escalated: "#f59e0b",
  failed:    "#ef4444",
};

const intentIcon: Record<string, string> = {
  property_inquiry:    "🏠",
  appointment_request: "📅",
  price_inquiry:       "💰",
  support:             "🛠️",
  complaint:           "⚠️",
  out_of_scope:        "❓",
};

const toolIcon: Record<string, string> = {
  search_knowledge:      "🔍",
  search_properties:     "🏠",
  get_or_create_customer:"👤",
  create_lead:           "📋",
  update_lead_stage:     "📈",
  get_available_slots:   "📅",
  create_appointment:    "📅",
  send_lead_whatsapp:    "💬",
  send_appointment_confirmation: "✅",
  notify_human_handoff:  "🚨",
};

export default function AgentLogs() {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRun, setSelectedRun] = useState<AgentRun | null>(null);
  const [detail, setDetail] = useState<AgentRunDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchRuns = useCallback(async () => {
    try {
      const data = await fetchAgentRuns(50);
      setRuns(data);
    } catch {
      // Backend not available — keep existing data
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
    const interval = setInterval(fetchRuns, 5_000);
    return () => clearInterval(interval);
  }, [fetchRuns]);

  const selectRun = useCallback(async (run: AgentRun) => {
    if (selectedRun?.id === run.id) {
      setSelectedRun(null);
      setDetail(null);
      return;
    }
    setSelectedRun(run);
    setDetail(null);
    setDetailLoading(true);
    try {
      const d = await fetchAgentRunDetail(run.id);
      setDetail(d);
    } catch {
      // Detail fetch failed — we still show the basic run info
    } finally {
      setDetailLoading(false);
    }
  }, [selectedRun]);

  const completed = runs.filter((r) => r.status === "completed").length;
  const escalated = runs.filter((r) => r.status === "escalated").length;
  const failed    = runs.filter((r) => r.status === "failed").length;
  const avgLatency = runs.length
    ? Math.round(runs.reduce((s, r) => s + (r.latency_ms ?? 0), 0) / runs.length)
    : 0;

  const intentCounts: Record<string, number> = {};
  for (const r of runs) {
    if (r.intent) intentCounts[r.intent] = (intentCounts[r.intent] ?? 0) + 1;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Agent Execution Log</h2>
          <p className="text-xs mt-0.5" style={{ color: "rgba(226,232,240,0.4)" }}>
            Every AI decision, tool call, and outcome — full observability
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full"
            style={{ background: "rgba(34,211,160,0.1)", border: "1px solid rgba(34,211,160,0.3)" }}
          >
            <span className="live-dot-inner" />
            <span className="text-xs font-semibold" style={{ color: "#22d3a0" }}>LIVE</span>
          </div>
          <button
            onClick={fetchRuns}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-all"
            style={{
              background: "rgba(79,110,255,0.1)",
              color: "#6b8fff",
              border: "1px solid rgba(79,110,255,0.2)",
            }}
          >
            <RefreshCw size={11} /> Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Run list */}
        <div className="col-span-2 glass-card" style={{ maxHeight: 560, overflowY: "auto" }}>
          {loading ? (
            <div className="p-8 text-center" style={{ color: "rgba(226,232,240,0.4)" }}>
              Connecting to backend...
            </div>
          ) : runs.length === 0 ? (
            <div className="p-10 text-center" style={{ color: "rgba(226,232,240,0.3)" }}>
              <p className="text-sm mb-1">No agent runs yet</p>
              <p className="text-xs">Make a call to your Twilio number to see the AI think here.</p>
            </div>
          ) : (
            <div className="divide-y" style={{ borderColor: "rgba(255,255,255,0.04)" }}>
              {runs.map((run) => (
                <div
                  key={run.id}
                  className="p-4 cursor-pointer transition-all duration-150"
                  style={{
                    background:
                      selectedRun?.id === run.id
                        ? "rgba(79,110,255,0.08)"
                        : "transparent",
                  }}
                  onClick={() => selectRun(run)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      <span className="text-lg flex-shrink-0 mt-0.5">
                        {intentIcon[run.intent ?? ""] ?? "🤖"}
                      </span>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className="text-xs font-mono px-2 py-0.5 rounded-full"
                            style={{
                              background: `${statusColor[run.status] ?? "#888"}20`,
                              color: statusColor[run.status] ?? "#888",
                              border: `1px solid ${statusColor[run.status] ?? "#888"}40`,
                            }}
                          >
                            {run.status}
                          </span>
                          <span className="text-xs font-mono" style={{ color: "rgba(226,232,240,0.4)" }}>
                            {run.intent ?? "unknown"}
                          </span>
                        </div>
                        <p className="text-xs truncate" style={{ color: "rgba(226,232,240,0.65)" }}>
                          💬 &quot;{run.input_text}&quot;
                        </p>

                        {/* Expanded detail */}
                        {selectedRun?.id === run.id && (
                          <div className="mt-3 space-y-3">
                            <p className="text-xs" style={{ color: "rgba(226,232,240,0.5)" }}>
                              <span style={{ color: "#22d3a0" }}>AI:</span>{" "}
                              {run.output_text}
                            </p>
                            {detailLoading && (
                              <p className="text-xs" style={{ color: "rgba(226,232,240,0.3)" }}>
                                Loading tool calls...
                              </p>
                            )}
                            {detail?.tool_calls && detail.tool_calls.length > 0 && (
                              <div className="space-y-1">
                                <p className="text-xs font-semibold" style={{ color: "rgba(226,232,240,0.4)" }}>
                                  Tools used:
                                </p>
                                {detail.tool_calls.map((tc, i) => (
                                  <div key={i} className="flex items-center gap-2">
                                    <span>{toolIcon[tc.tool_name] ?? "🔧"}</span>
                                    <span className="text-xs font-mono" style={{ color: "rgba(226,232,240,0.6)" }}>
                                      {tc.tool_name}
                                    </span>
                                    <span
                                      className="text-xs"
                                      style={{ color: tc.status === "success" ? "#22d3a0" : "#ef4444" }}
                                    >
                                      {tc.status}
                                    </span>
                                    {tc.latency_ms && (
                                      <span className="text-xs" style={{ color: "#4f6eff" }}>
                                        {tc.latency_ms}ms
                                      </span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <p className="text-xs font-mono" style={{ color: "rgba(226,232,240,0.35)" }}>
                        {fmtTimeFull(run.created_at)}
                      </p>
                      {run.latency_ms && (
                        <p className="text-xs mt-0.5" style={{ color: "#4f6eff" }}>
                          ⚡ {run.latency_ms}ms
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Stats sidebar */}
        <div className="space-y-4">
          <div className="glass-card p-4">
            <h3 className="text-xs font-semibold text-white mb-3">Run Summary</h3>
            <div className="space-y-3">
              {[
                { label: "Total Runs",  value: runs.length,  color: "#4f6eff" },
                { label: "Completed",   value: completed,    color: "#22d3a0" },
                { label: "Escalated",   value: escalated,    color: "#f59e0b" },
                { label: "Failed",      value: failed,       color: "#ef4444" },
                { label: "Avg Latency", value: `${avgLatency}ms`, color: "#a855f7" },
              ].map((s) => (
                <div key={s.label} className="flex justify-between items-center">
                  <span className="text-xs" style={{ color: "rgba(226,232,240,0.5)" }}>
                    {s.label}
                  </span>
                  <span className="text-sm font-bold" style={{ color: s.color }}>
                    {s.value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card p-4">
            <h3 className="text-xs font-semibold text-white mb-3">Intent Breakdown</h3>
            {Object.keys(intentCounts).length === 0 ? (
              <p className="text-xs" style={{ color: "rgba(226,232,240,0.3)" }}>No data yet</p>
            ) : (
              Object.entries(intentCounts)
                .sort(([, a], [, b]) => b - a)
                .map(([intent, count]) => {
                  const pct = runs.length ? Math.round((count / runs.length) * 100) : 0;
                  return (
                    <div key={intent} className="mb-2">
                      <div className="flex justify-between text-xs mb-1">
                        <span
                          style={{
                            color: "rgba(226,232,240,0.5)",
                            fontFamily: "monospace",
                            fontSize: 10,
                          }}
                        >
                          {intentIcon[intent] ?? "🤖"} {intent}
                        </span>
                        <span style={{ color: "rgba(226,232,240,0.7)" }}>{count}</span>
                      </div>
                      <div
                        className="w-full rounded-full"
                        style={{ height: 3, background: "rgba(255,255,255,0.06)" }}
                      >
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${pct}%`, background: "#4f6eff" }}
                        />
                      </div>
                    </div>
                  );
                })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
