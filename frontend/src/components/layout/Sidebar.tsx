"use client";
import { useAuth } from "@/lib/auth";
import {
  LayoutDashboard, Phone, Users, CalendarCheck, MessageSquare,
  BookOpen, Plug, Settings, Bot, UserPlus, BarChart3, FileText,
  UsersRound, RotateCcw, LogOut, ChevronDown
} from "lucide-react";

interface Props {
  activeView: string;
  onNavigate: (view: string) => void;
  liveCalls?: number;
  newLeads?: number;
}

const NAV_GROUPS = [
  {
    label: "MAIN",
    items: [
      { id: "overview",       label: "Dashboard",      icon: LayoutDashboard },
      { id: "calls",          label: "Live Calls",     icon: Phone,           badgeKey: "liveCalls" },
      { id: "leads",          label: "Leads",          icon: Users,           badgeKey: "newLeads" },
      { id: "appointments",   label: "Appointments",   icon: CalendarCheck },
      { id: "conversations",  label: "Conversations",  icon: MessageSquare },
      { id: "followups",      label: "Follow-ups",     icon: RotateCcw },
    ],
  },
  {
    label: "AI EMPLOYEE",
    items: [
      { id: "knowledge",      label: "Knowledge Base", icon: BookOpen },
      { id: "integrations",   label: "Integrations",   icon: Plug },
      { id: "aiemployees",    label: "AI Employees",   icon: Bot },
    ],
  },
  {
    label: "ANALYTICS",
    items: [
      { id: "analytics",      label: "Analytics",      icon: BarChart3 },
      { id: "reports",        label: "Reports",        icon: FileText },
    ],
  },
  {
    label: "TEAM",
    items: [
      { id: "team",           label: "Team",           icon: UsersRound },
      { id: "customers",      label: "Customers",      icon: UserPlus },
      { id: "settings",       label: "Settings",       icon: Settings },
    ],
  },
];

export default function Sidebar({ activeView, onNavigate, liveCalls = 0, newLeads = 0 }: Props) {
  const { user, business, logout } = useAuth();
  const badgeMap: Record<string, number> = { liveCalls, newLeads };

  return (
    <aside className="dash-sidebar">
      {/* Logo */}
      <div style={{ padding: "18px 16px 14px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 11,
            background: "linear-gradient(135deg, #4361ee, #2f4acb)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 4px 16px rgba(67,97,238,0.4)", flexShrink: 0,
          }}>
            <Bot size={18} color="#fff" />
          </div>
          <div>
            <p style={{ fontWeight: 800, fontSize: "0.95rem", color: "#fff", letterSpacing: "-0.02em" }}>VoxAI</p>
            <p style={{ fontSize: "0.62rem", color: "rgba(255,255,255,0.35)" }}>AI Business Employee</p>
          </div>
        </div>

        {/* Business selector */}
        {business && (
          <button style={{
            width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "7px 10px", borderRadius: 9, border: "1px solid rgba(255,255,255,0.1)",
            background: "rgba(255,255,255,0.05)", cursor: "pointer", gap: 6,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7, minWidth: 0 }}>
              <div style={{ width: 22, height: 22, borderRadius: 6, background: "linear-gradient(135deg, #4361ee, #10b981)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.6rem", fontWeight: 700, color: "#fff", flexShrink: 0 }}>
                {business.name?.charAt(0) ?? "B"}
              </div>
              <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "rgba(255,255,255,0.85)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {business.name}
              </p>
            </div>
            <ChevronDown size={12} color="rgba(255,255,255,0.4)" />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: "10px 10px", overflowY: "auto", display: "flex", flexDirection: "column", gap: 18 }}>
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <p style={{ fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.08em", color: "rgba(255,255,255,0.25)", padding: "0 6px", marginBottom: 4 }}>
              {group.label}
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeView === item.id;
                const badge = item.badgeKey ? badgeMap[item.badgeKey] : 0;
                return (
                  <button
                    key={item.id}
                    id={`nav-${item.id}`}
                    onClick={() => onNavigate(item.id)}
                    className="nav-item"
                    style={{
                      background: isActive ? "rgba(67,97,238,0.2)" : "transparent",
                      color: isActive ? "#fff" : "rgba(255,255,255,0.55)",
                      borderLeft: isActive ? "3px solid #4361ee" : "3px solid transparent",
                      paddingLeft: isActive ? 11 : 14,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                      <Icon size={15} />
                      <span>{item.label}</span>
                    </div>
                    {badge > 0 && (
                      <span className="dot-badge">{badge > 99 ? "99+" : badge}</span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Usage meter */}
      <div style={{ padding: "10px 12px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
        <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 10, padding: "10px 12px", marginBottom: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
            <span style={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.4)" }}>AI Calls</span>
            <span style={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.55)", fontFamily: "monospace" }}>
              {liveCalls > 0 ? `${liveCalls} LIVE` : "Standby"}
            </span>
          </div>
          <div style={{ height: 3, background: "rgba(255,255,255,0.08)", borderRadius: 99, overflow: "hidden" }}>
            <div style={{ width: liveCalls > 0 ? "60%" : "15%", height: "100%", background: "linear-gradient(90deg, #4361ee, #10b981)", borderRadius: 99, transition: "width 0.5s" }} />
          </div>
        </div>

        {/* User info + logout */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
            <div style={{ width: 28, height: 28, borderRadius: "50%", background: "linear-gradient(135deg, #4361ee, #8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.7rem", fontWeight: 700, color: "#fff", flexShrink: 0 }}>
              {(user?.full_name ?? "U").charAt(0).toUpperCase()}
            </div>
            <div style={{ minWidth: 0 }}>
              <p style={{ fontSize: "0.72rem", fontWeight: 600, color: "rgba(255,255,255,0.75)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {user?.full_name ?? "User"}
              </p>
              <p style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.35)", textTransform: "capitalize" }}>
                {user?.role ?? "owner"}
              </p>
            </div>
          </div>
          <button onClick={logout} title="Sign out"
            style={{ background: "none", border: "none", cursor: "pointer", color: "rgba(255,255,255,0.3)", padding: 4, borderRadius: 6, transition: "color 0.15s" }}
            onMouseOver={e => (e.currentTarget.style.color = "rgba(239,68,68,0.7)")}
            onMouseOut={e => (e.currentTarget.style.color = "rgba(255,255,255,0.3)")}>
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
}
