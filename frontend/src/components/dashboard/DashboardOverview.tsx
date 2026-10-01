"use client";
import { useState, useEffect, useCallback } from "react";
import {
  Phone, Users, CalendarCheck, Bot, TrendingUp,
  ArrowUpRight, ArrowDownRight, RefreshCw, ExternalLink, Zap,
} from "lucide-react";
import AIAvatar from "@/components/AIAvatar";
import { fetchDashboardStats, fetchLeads, fetchLiveCalls, type DashboardStats, type LeadItem, type LiveCall, fmtDuration } from "@/lib/api";


// ── Tiny sparkline bars ────────────────────────────────────────────────────
const MOCK_BARS = [3, 6, 4, 8, 7, 12, 10, 9, 14, 11, 16, 13];
function MiniChart({ color, up }: { color: string; up: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 28 }}>
      {MOCK_BARS.map((h, i) => (
        <div key={i} className="mini-bar" style={{ width: 3, height: (h / 16) * 28, background: `${color}${i > 8 ? "cc" : "50"}`, animationDelay: `${i * 0.04}s` }} />
      ))}
      {up ? <ArrowUpRight size={11} color={color} style={{ flexShrink: 0 }} /> : <ArrowDownRight size={11} color={color} style={{ flexShrink: 0 }} />}
    </div>
  );
}

// ── Animated counter ───────────────────────────────────────────────────────
function Counter({ value }: { value: number }) {
  const [displayed, setDisplayed] = useState(0);
  useEffect(() => {
    if (value === 0) { setDisplayed(0); return; }
    let v = 0;
    const step = Math.max(1, Math.ceil(value / 35));
    const t = setInterval(() => {
      v = Math.min(v + step, value);
      setDisplayed(v);
      if (v >= value) clearInterval(t);
    }, 18);
    return () => clearInterval(t);
  }, [value]);
  return <>{displayed.toLocaleString("en-IN")}</>;
}

const EMPTY_STATS: DashboardStats = {
  calls: { today: 0, live: 0, completed_today: 0, avg_duration_seconds: 0 },
  ai:   { runs_today: 0, handled_today: 0, escalated_today: 0, handle_rate_pct: 0, avg_latency_ms: 0, intent_breakdown: {} },
  leads: { today: 0, hot: 0, stage_breakdown: {} },
  appointments: { today: 0 },
  handoffs: { today: 0 },
};

const TABS = ["Recent Leads", "Appointments", "Call History", "Follow-ups"];

const scoreStyle: Record<string, { bg: string; color: string; label: string }> = {
  HOT:  { bg: "#fee2e2", color: "#991b1b", label: "🔥 Hot" },
  WARM: { bg: "#fef3c7", color: "#92400e", label: "⚡ Warm" },
  COLD: { bg: "#dbeafe", color: "#1e40af", label: "❄ Cold" },
};
const statusStyle: Record<string, { bg: string; color: string }> = {
  new:        { bg: "#dbeafe", color: "#1e40af" },
  contacted:  { bg: "#fef3c7", color: "#92400e" },
  qualified:  { bg: "#dcfce7", color: "#166534" },
  proposal:   { bg: "#ede9fe", color: "#5b21b6" },
  won:        { bg: "#dcfce7", color: "#166534" },
};

export default function DashboardOverview() {
  const [stats, setStats] = useState<DashboardStats>(EMPTY_STATS);
  const [leads, setLeads] = useState<LeadItem[]>([]);
  const [liveCalls, setLiveCalls] = useState<LiveCall[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [avatarMode, setAvatarMode] = useState<"idle" | "speaking" | "listening">("idle");
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [s, l, lc] = await Promise.all([fetchDashboardStats(), fetchLeads(5), fetchLiveCalls()]);
      setStats(s);
      setLeads(l);
      setLiveCalls(lc);
    } catch { /* backend offline — keep zeros */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 10_000); return () => clearInterval(t); }, [refresh]);

  // Avatar reflects live call count
  useEffect(() => {
    if (liveCalls.length > 0) setAvatarMode("speaking");
    else setAvatarMode("idle");
  }, [liveCalls.length]);

  const statCards = [
    { label: "Total Calls",       value: stats.calls.today,         delta: `+${stats.calls.completed_today > 0 ? Math.round((stats.calls.completed_today / Math.max(stats.calls.today, 1)) * 100) : 0}%`, up: true,  color: "#4361ee", icon: Phone,         sub: `${stats.calls.live} live now` },
    { label: "Qualified Leads",   value: stats.leads.today,         delta: `${stats.leads.hot} hot`,     up: true,  color: "#10b981", icon: Users,         sub: `${stats.leads.hot} HOT` },
    { label: "Appointments",      value: stats.appointments.today,  delta: `today`,                      up: true,  color: "#8b5cf6", icon: CalendarCheck, sub: "booked today" },
    { label: "AI Handled",        value: stats.ai.handled_today,    delta: `${stats.ai.handle_rate_pct}%`, up: true, color: "#06b6d4", icon: Bot,           sub: "handle rate" },
    { label: "Escalations",       value: stats.handoffs.today,      delta: `of ${stats.ai.runs_today}`,  up: false, color: "#f59e0b", icon: TrendingUp,    sub: "human handoffs" },
    { label: "Avg Response",      value: stats.ai.avg_latency_ms,   delta: "ms",                         up: true,  color: "#10b981", icon: Zap,           sub: "AI latency", suffix: "ms" },
  ];

  const fmtVal = (v: number, suffix?: string) => {
    if (suffix === "ms") return `${v}`;
    return `${v.toLocaleString("en-IN")}`;
  };

  // Derive channel breakdown from AI intent data
  const intentEntries = Object.entries(stats.ai.intent_breakdown);
  const totalIntents = intentEntries.reduce((s, [, c]) => s + c, 0);
  const channels = intentEntries.length > 0
    ? intentEntries.map(([label, count], i) => ({
        label: label.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
        pct: Math.round((count / totalIntents) * 100),
        color: ["#4361ee", "#10b981", "#8b5cf6", "#f59e0b", "#06b6d4"][i % 5],
      }))
    : [
        { label: "No data yet", pct: 100, color: "#94a3b8" },
      ];

  const funnelSteps = [
    { label: "Total Calls",   value: stats.calls.today,              pct: 100 },
    { label: "Qualified",     value: stats.leads.today,              pct: stats.calls.today > 0 ? Math.round((stats.leads.today / stats.calls.today) * 100) : 0 },
    { label: "Appointments",  value: stats.appointments.today,       pct: stats.calls.today > 0 ? Math.round((stats.appointments.today / stats.calls.today) * 100) : 0 },
    { label: "Closed Deals",  value: Math.round(stats.appointments.today * 0.38), pct: stats.calls.today > 0 ? Math.round((Math.round(stats.appointments.today * 0.38) / stats.calls.today) * 100) : 0 },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Hero banner */}
      <div style={{
        background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 60%, #0f172a 100%)",
        borderRadius: 18, padding: "18px 24px",
        display: "flex", alignItems: "center", gap: 20,
        position: "relative", overflow: "hidden",
      }}>
        <div style={{ position: "absolute", width: 400, height: 400, borderRadius: "50%", background: "radial-gradient(circle, rgba(67,97,238,0.12) 0%, transparent 70%)", top: -200, right: -100 }} />
        <div style={{ flex: 1, position: "relative", zIndex: 1 }}>
          <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", marginBottom: 4 }}>
            {new Date().toLocaleDateString("en-IN", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
          </p>
          <blockquote style={{ fontSize: "0.82rem", fontStyle: "italic", color: "rgba(255,255,255,0.55)", borderLeft: "3px solid rgba(67,97,238,0.5)", paddingLeft: 12, marginBottom: 10 }}>
            &ldquo;Never miss a customer. Your AI Employee answers, qualifies and books — all on autopilot.&rdquo;
          </blockquote>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <span className="badge" style={{ background: "rgba(16,185,129,0.15)", color: "#34d399" }}>🟢 AI Online</span>
            <span className="badge" style={{ background: "rgba(67,97,238,0.15)", color: "#818cf8" }}>🎯 {stats.calls.live} Live Calls</span>
            <span className="badge" style={{ background: "rgba(245,158,11,0.15)", color: "#fbbf24" }}>⚡ {stats.ai.avg_latency_ms}ms avg response</span>
          </div>
        </div>
        {/* Small avatar in banner */}
        <div style={{ position: "relative", zIndex: 1 }}>
          <AIAvatar mode={avatarMode} size={76} showRings={false} />
        </div>
        <div style={{ position: "absolute", top: 12, right: 12, zIndex: 1, display: "flex", gap: 6 }}>
          <button onClick={refresh}
            style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 8, padding: "5px 10px", color: "rgba(255,255,255,0.6)", fontSize: "0.7rem", cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}>
            <RefreshCw size={10} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} /> Refresh
          </button>
        </div>
      </div>

      {/* Stat cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 10 }}>
        {statCards.map((s, i) => {
          const Icon = s.icon;
          return (
            <div key={s.label} className="stat-card fade-in" style={{ animationDelay: `${i * 0.04}s`, opacity: 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div style={{ width: 34, height: 34, borderRadius: 10, background: `${s.color}15`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <Icon size={16} color={s.color} />
                </div>
                <span style={{ fontSize: "0.68rem", fontWeight: 700, color: s.up ? "#10b981" : "#ef4444" }}>
                  {s.delta}
                </span>
              </div>
              <p style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text)", letterSpacing: "-0.03em", lineHeight: 1.1 }}>
                {fmtVal(s.value, s.suffix)}
              </p>
              <p style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-2)" }}>{s.label}</p>
              <MiniChart color={s.color} up={s.up} />
            </div>
          );
        })}
      </div>

      {/* Middle row: Live calls + AI Employee card */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 14 }}>
        {/* Live calls section */}
        <div>
          <div className="flex-between" style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="live-dot" />
              <h2 style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text)" }}>Live Calls ({stats.calls.live})</h2>
              <span className="badge" style={{ background: "rgba(239,68,68,0.1)", color: "#dc2626" }}>● {stats.calls.live} in progress</span>
            </div>
            <button className="btn btn-ghost btn-sm" style={{ fontSize: "0.75rem", gap: 4 }}>
              View All <ExternalLink size={11} />
            </button>
          </div>

          {/* Live call cards — real data */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {liveCalls.length === 0 ? (
              <div style={{ gridColumn: "span 2", textAlign: "center", padding: "24px 0", color: "var(--text-3)", fontSize: "0.8rem" }}>
                <Phone size={20} style={{ opacity: 0.3, margin: "0 auto 8px", display: "block" }} />
                No active calls right now
              </div>
            ) : liveCalls.map((call) => (
              <div key={call.call_id} className="live-call-card" style={{ border: "1.5px solid rgba(67,97,238,0.2)" }}>
                <div className="flex-between" style={{ marginBottom: 10 }}>
                  <span style={{ background: "rgba(239,68,68,0.12)", color: "#dc2626", fontSize: "0.65rem", fontWeight: 700, padding: "3px 8px", borderRadius: 99, display: "flex", alignItems: "center", gap: 4 }}>
                    ● LIVE {fmtDuration(call.duration_seconds)}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                  <div style={{ width: 36, height: 36, borderRadius: "50%", background: "rgba(67,97,238,0.2)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: "0.85rem", color: "#4361ee", flexShrink: 0 }}>
                    {(call.customer_name ?? "?").charAt(0)}
                  </div>
                  <div>
                    <p style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--text)" }}>{call.customer_name}</p>
                    <p style={{ fontSize: "0.7rem", color: "var(--text-3)", fontFamily: "monospace" }}>{call.from_number}</p>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
                  {call.intent && <span className="badge badge-blue">{call.intent.replace(/_/g, " ")}</span>}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <div className="waveform" style={{ height: 24 }}>
                    {Array.from({ length: 8 }).map((_, i) => <span key={i} style={{ background: "#4361ee" }} />)}
                  </div>
                </div>
                <div style={{ background: "rgba(67,97,238,0.05)", border: "1px solid rgba(67,97,238,0.12)", borderRadius: 8, padding: "7px 10px", display: "flex", alignItems: "center", gap: 6 }}>
                  <span className="live-dot" style={{ width: 6, height: 6 }} />
                  <p style={{ fontSize: "0.72rem", color: "var(--text-2)" }}>AI is currently: <strong style={{ color: "#4361ee" }}>Handling {call.intent ? call.intent.replace(/_/g, " ") : "customer request"}...</strong></p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI Employee status card */}
        <div className="card" style={{ padding: 18, display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <div className="flex-between" style={{ width: "100%", marginBottom: 4 }}>
            <h3 style={{ fontWeight: 700, fontSize: "0.82rem", color: "var(--text)" }}>AI Employee Status</h3>
            <span className="badge badge-green">● {stats.calls.live > 0 ? "On Call" : "Ready"}</span>
          </div>

          {/* Animated avatar */}
          <AIAvatar mode={avatarMode} size={100} showRings={true} />

          <div style={{ textAlign: "center" }}>
            <p style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--text)" }}>AI Receptionist</p>
            <p style={{ fontSize: "0.7rem", color: "var(--text-3)" }}>
              {stats.calls.live > 0 ? `🗣 Handling ${stats.calls.live} call${stats.calls.live > 1 ? "s" : ""}...` : "Online · Ready for calls"}
            </p>
          </div>

          {/* Capabilities */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 5, justifyContent: "center" }}>
            {["📞 Phone", "💬 WhatsApp", "📧 Email", "🗂️ CRM", "📅 Calendar", "📚 Knowledge"].map((c) => (
              <span key={c} className="badge badge-blue" style={{ fontSize: "0.62rem" }}>{c}</span>
            ))}
          </div>

          {/* Stats summary */}
          <div style={{ width: "100%", display: "flex", gap: 6 }}>
            {[
              { label: "Today", value: stats.ai.runs_today, color: "#4361ee" },
              { label: "Handled", value: `${stats.ai.handle_rate_pct}%`, color: "#10b981" },
              { label: "Latency", value: `${stats.ai.avg_latency_ms}ms`, color: "#8b5cf6" },
            ].map((b) => (
              <div key={b.label} style={{ flex: 1, background: `${b.color}10`, border: `1px solid ${b.color}25`, borderRadius: 8, padding: "5px 6px", textAlign: "center" }}>
                <p style={{ fontSize: "0.7rem", fontWeight: 700, color: b.color }}>{b.value}</p>
                <p style={{ fontSize: "0.58rem", color: "var(--text-3)" }}>{b.label}</p>
              </div>
            ))}
          </div>

          <button className="btn btn-primary btn-sm" style={{ width: "100%", borderRadius: 9 }}>
            <Zap size={12} /> Configure AI Employee
          </button>
        </div>
      </div>

      {/* Bottom row: Leads table + Analytics */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 14 }}>
        {/* Leads + tabs */}
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div className="tab-bar" style={{ padding: "0 16px" }}>
            {TABS.map((t, i) => (
              <button key={t} className={`tab-item ${activeTab === i ? "active" : ""}`} onClick={() => setActiveTab(i)}>{t}</button>
            ))}
            <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", padding: "0 0 4px" }}>
              <button className="btn btn-ghost btn-sm" style={{ fontSize: "0.72rem", color: "var(--primary)", gap: 3 }}>
                View All <ExternalLink size={10} />
              </button>
            </div>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                {["Name", "Phone", "Requirement", "Budget", "Status", "Score", "Source", "Time", "Actions"].map(h => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => {
                const sc = scoreStyle[lead.score] ?? scoreStyle.COLD;
                const st = statusStyle[lead.status] ?? statusStyle.new;
                const initials = (lead.customer_name ?? "?").split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
                const timeAgo = (() => {
                  const diff = (Date.now() - new Date(lead.created_at).getTime()) / 60000;
                  if (diff < 1) return "just now";
                  if (diff < 60) return `${Math.round(diff)} min ago`;
                  return new Date(lead.created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
                })();
                return (
                  <tr key={lead.id}>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{ width: 28, height: 28, borderRadius: "50%", background: "linear-gradient(135deg, #4361ee20, #10b98120)", border: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.65rem", fontWeight: 700, color: "var(--primary)", flexShrink: 0 }}>
                          {initials}
                        </div>
                        <span style={{ fontWeight: 600, color: "var(--text)" }}>{lead.customer_name}</span>
                      </div>
                    </td>
                    <td style={{ color: "var(--text-3)", fontFamily: "monospace", fontSize: "0.75rem" }}>{lead.customer_phone}</td>
                    <td style={{ color: "var(--text-2)" }}>{lead.requirement_label || "—"}</td>
                    <td style={{ fontWeight: 700, color: "#10b981" }}>{lead.budget ?? "—"}</td>
                    <td><span style={{ background: st.bg, color: st.color, fontSize: "0.65rem", fontWeight: 600, padding: "2px 8px", borderRadius: 99 }}>{lead.status.charAt(0).toUpperCase() + lead.status.slice(1)}</span></td>
                    <td><span style={{ background: sc.bg, color: sc.color, fontSize: "0.65rem", fontWeight: 600, padding: "2px 8px", borderRadius: 99 }}>{sc.label}</span></td>
                    <td><span style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--text-2)", fontSize: "0.75rem" }}>📞 Call</span></td>
                    <td style={{ color: "var(--text-3)", fontSize: "0.72rem", whiteSpace: "nowrap" }}>{timeAgo}</td>
                    <td>
                      <div style={{ display: "flex", gap: 4 }}>
                        <button style={{ background: "none", border: "1px solid var(--border)", borderRadius: 6, padding: "3px 7px", fontSize: "0.65rem", cursor: "pointer", color: "var(--text-2)" }}>📞</button>
                        <button style={{ background: "none", border: "1px solid var(--border)", borderRadius: 6, padding: "3px 7px", fontSize: "0.65rem", cursor: "pointer", color: "var(--text-2)" }}>💬</button>
                        <button style={{ background: "none", border: "1px solid var(--border)", borderRadius: 6, padding: "3px 7px", fontSize: "0.65rem", cursor: "pointer", color: "var(--text-2)" }}>⋯</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Analytics sidebar */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {/* Intent Breakdown */}
          <div className="card" style={{ padding: 14 }}>
            <div className="flex-between" style={{ marginBottom: 10 }}>
              <p style={{ fontWeight: 700, fontSize: "0.8rem", color: "var(--text)" }}>Intent Breakdown</p>
              <span style={{ fontSize: "0.7rem", color: "var(--text-3)" }}>Today</span>
            </div>
            {channels.map(c => (
              <div key={c.label} style={{ marginBottom: 7 }}>
                <div className="flex-between" style={{ marginBottom: 3 }}>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-2)" }}>{c.label}</span>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: c.color }}>{c.pct}%</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${c.pct}%`, background: c.color }} />
                </div>
              </div>
            ))}
          </div>

          {/* Conversion Funnel */}
          <div className="card" style={{ padding: 14 }}>
            <p style={{ fontWeight: 700, fontSize: "0.8rem", color: "var(--text)", marginBottom: 10 }}>Conversion Funnel</p>
            {funnelSteps.map((f, i) => (
              <div key={f.label} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <span style={{ fontSize: "0.72rem", color: "var(--text-2)", width: 80, flexShrink: 0 }}>{f.label}</span>
                <div className="progress-bar" style={{ flex: 1 }}>
                  <div className="progress-fill" style={{ width: `${f.pct}%`, background: ["#4361ee", "#10b981", "#8b5cf6", "#f59e0b"][i] }} />
                </div>
                <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--text)", width: 24, textAlign: "right" }}>{f.value}</span>
              </div>
            ))}
          </div>

          {/* AI Resolution */}
          <div className="card" style={{ padding: 14 }}>
            <p style={{ fontWeight: 700, fontSize: "0.8rem", color: "var(--text)", marginBottom: 8 }}>AI Resolution Rate</p>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ position: "relative", width: 64, height: 64, flexShrink: 0 }}>
                <svg width="64" height="64" viewBox="0 0 64 64">
                  <circle cx="32" cy="32" r="26" fill="none" stroke="var(--border)" strokeWidth="6" />
                  <circle cx="32" cy="32" r="26" fill="none" stroke="#4361ee" strokeWidth="6"
                    strokeDasharray={`${2 * Math.PI * 26 * stats.ai.handle_rate_pct / 100} ${2 * Math.PI * 26}`}
                    strokeLinecap="round" transform="rotate(-90 32 32)" />
                </svg>
                <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.8rem", fontWeight: 800, color: "#4361ee" }}>
                  {stats.ai.handle_rate_pct}%
                </div>
              </div>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 4 }}>
                  <Bot size={12} color="#4361ee" />
                  <span style={{ fontSize: "0.72rem", color: "var(--text-2)" }}>{stats.ai.handled_today} AI Handled</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <span style={{ fontSize: "0.72rem", color: "var(--text-3)" }}>{stats.handoffs.today} Human Handoff</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes ringPulse { 0% { transform: scale(1); opacity: 0.6; } 100% { transform: scale(1.6); opacity: 0; } }
        @keyframes breathe { 0%,100% { transform: scale(1) translateY(0); } 40% { transform: scale(1.012) translateY(-2px); } }
        @keyframes nod { 0%,100% { transform: rotate(0); } 20% { transform: rotate(1.5deg); } 50% { transform: rotate(-1deg); } }
        @keyframes speakGlow { 0%,100% { box-shadow: 0 0 0 0 rgba(67,97,238,0); } 50% { box-shadow: 0 0 0 12px rgba(67,97,238,0.15); } }
        @keyframes livePulse { 0%,100% { opacity:1; transform:scale(1); } 50% { opacity:0.5; transform:scale(1.4); } }
        @keyframes fadeInUp { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
        @keyframes barGrow { from { transform: scaleY(0); } to { transform: scaleY(1); } }
        @keyframes wave1 { 0%,100%{height:4px} 50%{height:20px} }
        @keyframes wave2 { 0%,100%{height:8px} 50%{height:28px} }
        @keyframes wave3 { 0%,100%{height:6px} 50%{height:22px} }
        @keyframes wave4 { 0%,100%{height:10px} 50%{height:32px} }
        @keyframes wave5 { 0%,100%{height:5px} 50%{height:18px} }
        .waveform span:nth-child(1){animation:wave1 0.9s ease-in-out infinite}
        .waveform span:nth-child(2){animation:wave2 0.9s ease-in-out infinite 0.1s}
        .waveform span:nth-child(3){animation:wave3 0.9s ease-in-out infinite 0.2s}
        .waveform span:nth-child(4){animation:wave4 0.9s ease-in-out infinite 0.3s}
        .waveform span:nth-child(5){animation:wave2 0.9s ease-in-out infinite 0.4s}
        .waveform span:nth-child(6){animation:wave3 0.9s ease-in-out infinite 0.5s}
        .waveform span:nth-child(7){animation:wave1 0.9s ease-in-out infinite 0.6s}
        .waveform span:nth-child(8){animation:wave5 0.9s ease-in-out infinite 0.35s}
      `}</style>
    </div>
  );
}
