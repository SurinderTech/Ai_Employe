"use client";
import { Bell, Search, CalendarRange, ChevronDown } from "lucide-react";
import { useAuth } from "@/lib/auth";

interface Props {
  title?: string;
  notifications?: number;
}

export default function Topbar({ notifications = 0 }: Props) {
  const { user, business } = useAuth();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good Morning" : hour < 17 ? "Good Afternoon" : "Good Evening";

  return (
    <header className="dash-topbar">
      {/* Greeting */}
      <div style={{ flex: 1 }}>
        <p style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--text)" }}>
          {greeting}, {user?.full_name?.split(" ")[0] ?? "there"}! 👋
        </p>
        <p style={{ fontSize: "0.7rem", color: "var(--text-3)" }}>
          {business?.name ?? "Your"} · AI Employee is working 24/7
        </p>
      </div>

      {/* Search */}
      <div style={{ position: "relative", width: 240 }}>
        <Search size={13} style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "var(--text-3)" }} />
        <input
          placeholder="Search leads, calls..."
          style={{
            width: "100%", paddingLeft: 32, paddingRight: 12, paddingTop: 7, paddingBottom: 7,
            border: "1px solid var(--border)", borderRadius: 10, fontSize: "0.8rem",
            color: "var(--text)", background: "var(--surface-2)", outline: "none", fontFamily: "inherit",
          }}
        />
      </div>

      {/* Date range */}
      <button style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 12px", borderRadius: 9, border: "1px solid var(--border)", background: "var(--surface)", fontSize: "0.75rem", color: "var(--text-2)", cursor: "pointer" }}>
        <CalendarRange size={13} />
        Last 7 Days
        <ChevronDown size={11} />
      </button>

      {/* Notifications */}
      <button style={{ position: "relative", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 9, padding: "6px 10px", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Bell size={16} color="var(--text-2)" />
        {notifications > 0 && (
          <span style={{ position: "absolute", top: -4, right: -4, width: 16, height: 16, borderRadius: "50%", background: "var(--accent-red)", fontSize: "0.6rem", fontWeight: 700, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}>
            {notifications}
          </span>
        )}
      </button>

      {/* Profile */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 8px 4px 4px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface)", cursor: "pointer" }}>
        <div style={{ width: 30, height: 30, borderRadius: "50%", background: "linear-gradient(135deg, #4361ee, #8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.75rem", fontWeight: 700, color: "#fff" }}>
          {(user?.full_name ?? "U").charAt(0)}
        </div>
        <div>
          <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text)" }}>{user?.full_name ?? "User"}</p>
          <p style={{ fontSize: "0.62rem", color: "var(--text-3)", textTransform: "capitalize" }}>{user?.role ?? "Owner"}</p>
        </div>
        <ChevronDown size={12} color="var(--text-3)" />
      </div>
    </header>
  );
}
