"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";

// Dashboard views
import DashboardOverview from "@/components/dashboard/DashboardOverview";
import LiveCalls from "@/components/dashboard/LiveCalls";
import LeadPipeline from "@/components/dashboard/LeadPipeline";
import AgentLogs from "@/components/dashboard/AgentLogs";
import KnowledgeBase from "@/components/dashboard/KnowledgeBase";
import Integrations from "@/components/dashboard/Integrations";
import { fetchCallStats, fetchLeadStats } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const { token, loading } = useAuth();
  const [activeView, setActiveView] = useState("overview");
  const [liveCalls, setLiveCalls] = useState(0);
  const [newLeads, setNewLeads] = useState(0);

  // Auth guard
  useEffect(() => {
    if (!loading && !token) {
      router.push("/auth/login");
    }
  }, [token, loading, router]);

  // Poll sidebar badges
  const pollBadges = useCallback(async () => {
    try {
      const [cs, ls] = await Promise.all([fetchCallStats(), fetchLeadStats()]);
      setLiveCalls(cs.live_now);
      setNewLeads(ls.new);
    } catch { /* backend not running */ }
  }, []);

  useEffect(() => {
    pollBadges();
    const t = setInterval(pollBadges, 10_000);
    return () => clearInterval(t);
  }, [pollBadges]);

  if (loading) {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#f0f4ff", flexDirection: "column", gap: 16 }}>
        <div style={{ width: 44, height: 44, borderRadius: 14, background: "linear-gradient(135deg, #4361ee, #2f4acb)", display: "flex", alignItems: "center", justifyContent: "center", animation: "spin 1.5s linear infinite" }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
        </div>
        <p style={{ color: "#64748b", fontSize: "0.875rem" }}>Loading VoxAI...</p>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (!token) return null;

  const renderView = () => {
    switch (activeView) {
      case "overview":       return <DashboardOverview />;
      case "calls":          return <LiveCalls />;
      case "leads":          return <LeadPipeline />;
      case "agents":
      case "conversations":  return <AgentLogs />;
      case "knowledge":      return <KnowledgeBase />;
      case "integrations":   return <Integrations />;
      default:
        return (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", flexDirection: "column", gap: 10 }}>
            <p style={{ fontSize: "2rem" }}>🚧</p>
            <p style={{ fontWeight: 700, color: "var(--text)" }}>{activeView.charAt(0).toUpperCase() + activeView.slice(1)}</p>
            <p style={{ color: "var(--text-3)", fontSize: "0.85rem" }}>Coming soon — this feature is in development</p>
          </div>
        );
    }
  };

  return (
    <div className="dash-layout">
      <Sidebar activeView={activeView} onNavigate={setActiveView} liveCalls={liveCalls} newLeads={newLeads} />
      <div className="dash-main">
        <Topbar notifications={liveCalls} />
        <main className="dash-content">
          {renderView()}
        </main>
      </div>
    </div>
  );
}
