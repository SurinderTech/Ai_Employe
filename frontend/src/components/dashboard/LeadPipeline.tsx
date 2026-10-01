"use client";

import { RefreshCw, Plus } from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import {
  fetchLeads,
  fetchLeadStats,
  type LeadItem,
  type LeadStats,
  fmtTime,
} from "@/lib/api";

const scoreConfig: Record<string, { cls: string; icon: string }> = {
  HOT:  { cls: "badge-red",   icon: "🔥" },
  WARM: { cls: "badge-amber", icon: "⚡" },
  COLD: { cls: "badge-blue",  icon: "❄️" },
};

const statusConfig: Record<string, { label: string; cls: string }> = {
  new:         { label: "New",       cls: "badge-blue"   },
  contacted:   { label: "Contacted", cls: "badge-amber"  },
  qualified:   { label: "Qualified", cls: "badge-green"  },
  proposal:    { label: "Proposal",  cls: "badge-purple" },
  negotiation: { label: "Negotiation", cls: "badge-amber" },
  won:         { label: "Won 🎉",    cls: "badge-green"  },
  lost:        { label: "Lost",      cls: "badge-red"    },
};

const STAGE_ORDER = ["new", "contacted", "qualified", "proposal", "negotiation", "won", "lost"];
const STAGE_COLORS: Record<string, string> = {
  new: "#4f6eff", contacted: "#f59e0b", qualified: "#22d3a0",
  proposal: "#a855f7", negotiation: "#f59e0b", won: "#22d3a0", lost: "#ef4444",
};

export default function LeadPipeline() {
  const [leads, setLeads] = useState<LeadItem[]>([]);
  const [leadStats, setLeadStats] = useState<LeadStats>({
    total: 0, hot: 0, new: 0, stage_breakdown: {},
  });
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [l, s] = await Promise.all([fetchLeads(100), fetchLeadStats()]);
      setLeads(l);
      setLeadStats(s);
    } catch {
      // Backend not available
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 15_000);
    return () => clearInterval(t);
  }, [refresh]);

  const stageSummary = STAGE_ORDER.slice(0, 4).map((stage) => ({
    label: statusConfig[stage]?.label ?? stage,
    count: leadStats.stage_breakdown[stage] ?? 0,
    color: STAGE_COLORS[stage] ?? "#4f6eff",
  }));

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white">Lead Pipeline</h1>
          {leadStats.hot > 0 && (
            <span className="badge badge-red">🔥 {leadStats.hot} HOT</span>
          )}
          {leadStats.total > 0 && (
            <span className="badge badge-blue">{leadStats.total} TOTAL</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refresh}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-all"
            style={{
              background: "rgba(79,110,255,0.08)",
              color: "#6b8fff",
              border: "1px solid rgba(79,110,255,0.15)",
            }}
          >
            <RefreshCw size={11} /> Refresh
          </button>
          <button
            id="btn-add-lead"
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white transition-all"
            style={{ background: "linear-gradient(135deg, #4f6eff, #22d3a0)" }}
          >
            <Plus size={14} /> Add Lead
          </button>
        </div>
      </div>

      {/* Pipeline stage summary */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {stageSummary.map((stage) => (
          <div key={stage.label} className="glass-card p-4 stat-card">
            <p className="text-2xl font-bold text-white">{stage.count}</p>
            <div className="flex items-center gap-2 mt-1">
              <div className="w-2 h-2 rounded-full" style={{ background: stage.color }} />
              <p className="text-xs" style={{ color: "rgba(226,232,240,0.5)" }}>
                {stage.label}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Lead table */}
      <div className="glass-card">
        <div className="p-5 pb-0 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">All Leads</h2>
          {loading && (
            <span className="text-xs" style={{ color: "rgba(226,232,240,0.4)" }}>
              Loading...
            </span>
          )}
        </div>
        <div className="overflow-x-auto">
          {leads.length === 0 && !loading ? (
            <div className="p-12 text-center" style={{ color: "rgba(226,232,240,0.3)" }}>
              <p className="text-sm mb-2">No leads yet</p>
              <p className="text-xs">
                Leads are created automatically when the AI handles calls. Make sure the backend and
                Twilio are configured.
              </p>
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr
                  style={{
                    borderBottom: "1px solid rgba(255,255,255,0.06)",
                    color: "rgba(226,232,240,0.4)",
                  }}
                >
                  <th className="text-left px-5 py-3">Customer</th>
                  <th className="text-left px-5 py-3">Requirement</th>
                  <th className="text-left px-5 py-3">Budget</th>
                  <th className="text-left px-5 py-3">Score</th>
                  <th className="text-left px-5 py-3">Status</th>
                  <th className="text-left px-5 py-3">Time</th>
                  <th className="text-left px-5 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => {
                  const sc = scoreConfig[lead.score] ?? scoreConfig.COLD;
                  const st = statusConfig[lead.status] ?? { label: lead.status, cls: "badge-blue" };
                  const initials = (lead.customer_name ?? "?")
                    .split(" ")
                    .map((w) => w[0])
                    .join("")
                    .slice(0, 2)
                    .toUpperCase();

                  return (
                    <tr
                      key={lead.id}
                      id={`lead-${lead.id}`}
                      className="transition-colors hover:bg-white/[0.02]"
                      style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}
                    >
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2.5">
                          <div
                            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white"
                            style={{
                              background: "linear-gradient(135deg, #4f6eff, #22d3a0)",
                            }}
                          >
                            {initials}
                          </div>
                          <div>
                            <p className="text-white font-medium">{lead.customer_name}</p>
                            <p style={{ color: "rgba(226,232,240,0.4)" }}>
                              {lead.customer_phone}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3" style={{ color: "rgba(226,232,240,0.7)" }}>
                        {lead.requirement_label || "—"}
                      </td>
                      <td
                        className="px-5 py-3 font-semibold"
                        style={{ color: "#22d3a0" }}
                      >
                        {lead.budget ?? "—"}
                      </td>
                      <td className="px-5 py-3">
                        <span className={`badge ${sc.cls}`}>
                          {sc.icon} {lead.score}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        <span className={`badge ${st.cls}`}>{st.label}</span>
                      </td>
                      <td
                        className="px-5 py-3 font-mono"
                        style={{ color: "rgba(226,232,240,0.4)" }}
                      >
                        {fmtTime(lead.created_at)}
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-1.5">
                          {lead.status === "new" || lead.status === "contacted" ? (
                            <button
                              className="px-2.5 py-1 rounded-md text-xs transition-colors"
                              style={{
                                background: "rgba(79,110,255,0.1)",
                                color: "#6b8fff",
                                border: "1px solid rgba(79,110,255,0.2)",
                              }}
                            >
                              Book Visit
                            </button>
                          ) : null}
                          <button
                            className="px-2.5 py-1 rounded-md text-xs transition-colors"
                            style={{
                              background: "rgba(34,211,160,0.08)",
                              color: "#22d3a0",
                              border: "1px solid rgba(34,211,160,0.15)",
                            }}
                          >
                            WhatsApp
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
