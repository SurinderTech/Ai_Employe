"use client";

import { useState, useEffect, useCallback } from "react";
import { CheckCircle, AlertCircle, RefreshCw, ExternalLink, Plug, Zap } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface IntegrationStatus {
  id: string;
  integration_type: string;
  display_name: string;
  status: "connected" | "disconnected" | "error" | "pending";
  icon: string;
  description: string;
  config_keys: string[];
  configured: boolean;
  last_synced_at: string | null;
  error_message: string | null;
}

// Static metadata for integrations not in the env-based list
const STATIC_INTEGRATIONS: IntegrationStatus[] = [
  {
    id: "static-pgvector",
    integration_type: "pgvector",
    display_name: "PostgreSQL + pgvector",
    status: "connected", // if backend is up, this is connected
    icon: "🗄️",
    description: "Vector embeddings storage and semantic similarity search for RAG",
    config_keys: ["DATABASE_URL"],
    configured: true,
    last_synced_at: null,
    error_message: null,
  },
  {
    id: "static-redis",
    integration_type: "redis",
    display_name: "Redis Cache",
    status: "pending",
    icon: "⚡",
    description: "Session state, rate limiting, and webhook deduplication",
    config_keys: ["REDIS_URL"],
    configured: true,
    last_synced_at: null,
    error_message: null,
  },
];

const statusInfo: Record<string, { label: string; cls: string }> = {
  connected:    { label: "Connected",    cls: "badge-green" },
  disconnected: { label: "Not Connected",cls: "badge-blue"  },
  error:        { label: "Error",        cls: "badge-red"   },
  pending:      { label: "Pending",      cls: "badge-amber" },
};

const integrationColor: Record<string, string> = {
  twilio:          "#ef4444",
  gemini:          "#a855f7",
  hubspot:         "#f59e0b",
  google_calendar: "#4f6eff",
  whatsapp:        "#22d3a0",
  pgvector:        "#22d3a0",
  redis:           "#f59e0b",
};

const setupLinks: Record<string, string> = {
  twilio:          "https://console.twilio.com/",
  hubspot:         "https://app.hubspot.com/",
  google_calendar: "https://console.cloud.google.com/",
  gemini:          "https://aistudio.google.com/apikey",
};

export default function Integrations() {
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [backendOnline, setBackendOnline] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/integrations/public/list`);
      if (!res.ok) throw new Error(`${res.status}`);
      const data: IntegrationStatus[] = await res.json();
      // Merge static items
      const merged = [
        ...data,
        ...STATIC_INTEGRATIONS.filter(
          (s) => !data.find((d) => d.integration_type === s.integration_type)
        ),
      ];
      setIntegrations(merged);
      setBackendOnline(true);
    } catch {
      // Backend not running — show placeholder state
      setIntegrations([
        ...STATIC_INTEGRATIONS.map((i) => ({
          ...i,
          status: "disconnected" as const,
          error_message: "Backend not running",
        })),
      ]);
      setBackendOnline(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 30_000);
    return () => clearInterval(t);
  }, [load]);

  const connected    = integrations.filter((i) => i.status === "connected").length;
  const disconnected = integrations.filter((i) => i.status !== "connected").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Integrations</h2>
          <p className="text-xs mt-0.5" style={{ color: "rgba(226,232,240,0.4)" }}>
            Connect your business tools — AI Employee coordinates across all of them
          </p>
        </div>
        <button
          onClick={load}
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

      {/* Backend status banner */}
      {!loading && (
        <div
          className="flex items-center gap-3 px-4 py-3 rounded-xl text-xs"
          style={{
            background: backendOnline ? "rgba(34,211,160,0.06)" : "rgba(239,68,68,0.06)",
            border: `1px solid ${backendOnline ? "rgba(34,211,160,0.2)" : "rgba(239,68,68,0.2)"}`,
          }}
        >
          <span
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ background: backendOnline ? "#22d3a0" : "#ef4444" }}
          />
          <span style={{ color: backendOnline ? "#22d3a0" : "#ef4444", fontWeight: 600 }}>
            Backend {backendOnline ? "Online" : "Offline"}
          </span>
          <span style={{ color: "rgba(226,232,240,0.5)" }}>
            {backendOnline
              ? `Showing real config from .env — ${connected} connected, ${disconnected} not configured`
              : "Start the FastAPI backend to see real integration status"}
          </span>
        </div>
      )}

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Connected",     value: connected,    color: "#22d3a0" },
          { label: "Not Configured",value: disconnected, color: "#ef4444" },
          { label: "Total",         value: integrations.length, color: "#4f6eff" },
        ].map((s) => (
          <div key={s.label} className="glass-card p-4 stat-card">
            <p className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</p>
            <p className="text-xs mt-1" style={{ color: "rgba(226,232,240,0.5)" }}>
              {s.label}
            </p>
          </div>
        ))}
      </div>

      {/* Integration cards */}
      {loading ? (
        <div className="text-center py-10" style={{ color: "rgba(226,232,240,0.4)" }}>
          Loading integration status...
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {integrations.map((item) => {
            const ss = statusInfo[item.status] ?? statusInfo.pending;
            const color = integrationColor[item.integration_type] ?? "#888";
            const link = setupLinks[item.integration_type];

            return (
              <div
                key={item.id}
                id={`integration-${item.integration_type}`}
                className="glass-card p-5 transition-all"
                style={{
                  borderColor: item.status === "connected"
                    ? `${color}30`
                    : "rgba(255,255,255,0.06)",
                }}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center text-xl"
                      style={{ background: `${color}15` }}
                    >
                      {item.icon}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">{item.display_name}</p>
                      <span className={`badge ${ss.cls}`} style={{ fontSize: "0.6rem" }}>
                        {ss.label}
                      </span>
                    </div>
                  </div>
                  {item.status === "connected" ? (
                    <CheckCircle size={16} style={{ color: "#22d3a0", flexShrink: 0 }} />
                  ) : item.status === "error" ? (
                    <AlertCircle size={16} style={{ color: "#ef4444", flexShrink: 0 }} />
                  ) : (
                    <Plug size={16} style={{ color: "rgba(226,232,240,0.25)", flexShrink: 0 }} />
                  )}
                </div>

                <p className="text-xs mb-3" style={{ color: "rgba(226,232,240,0.5)" }}>
                  {item.description}
                </p>

                {/* Config keys */}
                {item.config_keys && item.config_keys.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {item.config_keys.map((k) => (
                      <span
                        key={k}
                        className="text-xs font-mono px-1.5 py-0.5 rounded"
                        style={{
                          background: "rgba(255,255,255,0.04)",
                          color: "rgba(226,232,240,0.4)",
                          border: "1px solid rgba(255,255,255,0.06)",
                        }}
                      >
                        {k}
                      </span>
                    ))}
                  </div>
                )}

                {item.error_message && (
                  <p className="text-xs mb-3" style={{ color: "#ef4444" }}>
                    ⚠ {item.error_message}
                  </p>
                )}

                <div className="flex items-center justify-between">
                  <p className="text-xs" style={{ color: "rgba(226,232,240,0.3)" }}>
                    {item.last_synced_at
                      ? `Last sync: ${new Date(item.last_synced_at).toLocaleTimeString()}`
                      : item.status === "connected"
                        ? "Active"
                        : "Set in .env to connect"}
                  </p>
                  {link && !item.configured && (
                    <a
                      href={link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg transition-all"
                      style={{
                        background: `${color}12`,
                        color,
                        border: `1px solid ${color}25`,
                      }}
                    >
                      <ExternalLink size={10} /> Setup
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Architecture diagram */}
      <div
        className="glass-card p-5"
        style={{ borderColor: "rgba(168,85,247,0.2)", background: "rgba(168,85,247,0.03)" }}
      >
        <div className="flex items-center gap-2 mb-3">
          <Zap size={14} style={{ color: "#a855f7" }} />
          <h3 className="text-xs font-semibold text-white">AI Employee Integration Architecture</h3>
        </div>
        <p className="text-xs" style={{ color: "rgba(226,232,240,0.45)" }}>
          Customer → Twilio Voice → FastAPI Webhook → LangGraph Orchestrator → [CRM · Calendar · WhatsApp · RAG] → Response
        </p>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}