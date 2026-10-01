"use client";

import { Phone, User, Brain, Mic, RefreshCw, Clock } from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import {
  fetchLiveCalls,
  fetchRecentCalls,
  type LiveCall,
  type RecentCall,
  fmtDuration,
  fmtTime,
} from "@/lib/api";

// ── Live call card ─────────────────────────────────────────────────────────

function LiveCallCard({ call }: { call: LiveCall & { _duration: number } }) {
  const [duration, setDuration] = useState(call._duration);

  useEffect(() => {
    const t = setInterval(() => setDuration((d) => d + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const initials = (call.customer_name ?? "?")
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div
      id={`live-call-${call.call_id}`}
      className="glass-card p-5"
      style={{ borderColor: "rgba(34,211,160,0.25)" }}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-white text-sm"
            style={{ background: "linear-gradient(135deg, #4f6eff, #22d3a0)" }}
          >
            {initials}
          </div>
          <div>
            <p className="text-sm font-semibold text-white">{call.customer_name}</p>
            <p className="text-xs" style={{ color: "rgba(226,232,240,0.4)" }}>
              {call.from_number}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="live-dot-inner" />
          <span className="text-xs font-bold" style={{ color: "var(--color-accent-green)" }}>
            LIVE
          </span>
          <span className="text-xs font-mono" style={{ color: "rgba(226,232,240,0.6)" }}>
            {fmtDuration(duration)}
          </span>
        </div>
      </div>

      {/* Intent badge */}
      <div className="flex items-center gap-2 mb-3">
        {call.intent ? (
          <span className="badge badge-blue">{call.intent}</span>
        ) : (
          <span className="badge badge-amber">classifying...</span>
        )}
      </div>

      {/* AI thinking box */}
      <div
        className="rounded-lg p-3"
        style={{
          background: "rgba(79,110,255,0.08)",
          border: "1px solid rgba(79,110,255,0.15)",
        }}
      >
        <div className="flex items-center gap-2 mb-1">
          <Brain size={12} style={{ color: "#4f6eff" }} />
          <span className="text-xs font-semibold" style={{ color: "#4f6eff" }}>
            AI Agent processing...
          </span>
        </div>
        <p className="text-xs" style={{ color: "rgba(226,232,240,0.65)" }}>
          {call.intent
            ? `Handling ${call.intent.replace(/_/g, " ")} request`
            : "Analysing customer input..."}
        </p>
      </div>

      <div className="flex items-center gap-4 mt-3">
        <button
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-colors"
          style={{
            background: "rgba(239,68,68,0.1)",
            color: "#ef4444",
            border: "1px solid rgba(239,68,68,0.2)",
          }}
        >
          <User size={11} /> Take Over
        </button>
        <button
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-colors"
          style={{
            background: "rgba(107,143,255,0.1)",
            color: "#6b8fff",
            border: "1px solid rgba(107,143,255,0.2)",
          }}
        >
          <Mic size={11} /> Listen
        </button>
      </div>
    </div>
  );
}

// ── Outcome badge ──────────────────────────────────────────────────────────

function outcomeFromStatus(status: string): { label: string; ok: boolean } {
  switch (status) {
    case "completed": return { label: "Completed", ok: true };
    case "no-answer": return { label: "No Answer", ok: false };
    case "failed":    return { label: "Failed", ok: false };
    case "busy":      return { label: "Busy", ok: false };
    default:          return { label: status, ok: true };
  }
}

// ── Main component ─────────────────────────────────────────────────────────

export default function LiveCalls() {
  const [live, setLive] = useState<Array<LiveCall & { _duration: number }>>([]);
  const [recent, setRecent] = useState<RecentCall[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [liveData, recentData] = await Promise.all([
        fetchLiveCalls(),
        fetchRecentCalls(10),
      ]);
      // Attach a local duration tracker so the timer can increment from the
      // server-provided duration_seconds
      setLive(liveData.map((c) => ({ ...c, _duration: c.duration_seconds })));
      setRecent(recentData);
    } catch {
      // Backend not up — keep empty (no mock calls shown)
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5_000);
    return () => clearInterval(t);
  }, [refresh]);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white">Live Calls</h1>
          {live.length > 0 ? (
            <span className="badge badge-green">🔴 {live.length} ACTIVE</span>
          ) : (
            <span className="badge badge-amber">No active calls</span>
          )}
        </div>
        <button
          onClick={refresh}
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

      {/* Live call cards */}
      {loading ? (
        <div
          className="glass-card p-12 text-center mb-8"
          style={{ color: "rgba(226,232,240,0.4)" }}
        >
          <p className="text-sm">Connecting to backend...</p>
        </div>
      ) : live.length === 0 ? (
        <div
          className="glass-card p-12 text-center mb-8"
          style={{ borderColor: "rgba(107,143,255,0.1)" }}
        >
          <Phone
            size={32}
            className="mx-auto mb-4"
            style={{ color: "rgba(107,143,255,0.3)" }}
          />
          <p className="text-sm font-medium text-white">No active calls right now</p>
          <p
            className="text-xs mt-2"
            style={{ color: "rgba(226,232,240,0.4)" }}
          >
            When a customer calls your Twilio number, it will appear here in real time.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-5 mb-8">
          {live.map((call) => (
            <LiveCallCard key={call.call_id} call={call} />
          ))}
        </div>
      )}

      {/* Recent calls table */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">Recent Calls</h2>
          {recent.length === 0 && !loading && (
            <span
              className="text-xs"
              style={{ color: "rgba(226,232,240,0.4)" }}
            >
              No calls yet
            </span>
          )}
        </div>
        {recent.length === 0 ? (
          <div
            className="py-10 text-center"
            style={{ color: "rgba(226,232,240,0.3)" }}
          >
            <Clock size={24} className="mx-auto mb-3" style={{ opacity: 0.4 }} />
            <p className="text-xs">
              Completed calls will appear here. Start the backend and make a call.
            </p>
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr style={{ color: "rgba(226,232,240,0.4)" }}>
                <th className="text-left py-2 pb-3">Customer</th>
                <th className="text-left py-2 pb-3">Number</th>
                <th className="text-left py-2 pb-3">Duration</th>
                <th className="text-left py-2 pb-3">Outcome</th>
                <th className="text-left py-2 pb-3">Time</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((row) => {
                const { label, ok } = outcomeFromStatus(row.status);
                return (
                  <tr
                    key={row.call_id}
                    style={{ borderTop: "1px solid rgba(255,255,255,0.04)" }}
                  >
                    <td className="py-2.5 text-white font-medium">
                      {row.customer_name}
                    </td>
                    <td
                      className="py-2.5 font-mono"
                      style={{ color: "rgba(226,232,240,0.5)" }}
                    >
                      {row.from_number}
                    </td>
                    <td
                      className="py-2.5 font-mono"
                      style={{ color: "rgba(226,232,240,0.6)" }}
                    >
                      {fmtDuration(row.duration_seconds)}
                    </td>
                    <td className="py-2.5">
                      <span className={`badge ${ok ? "badge-green" : "badge-red"}`}>
                        {label}
                      </span>
                    </td>
                    <td
                      className="py-2.5 font-mono"
                      style={{ color: "rgba(226,232,240,0.4)" }}
                    >
                      {fmtTime(row.created_at)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
