/**
 * api.ts — Centralised API client for the AI Employee dashboard.
 *
 * All functions return real data from the backend.
 * On network error or non-200 response they throw, letting components
 * catch and fall back to mock data.
 */

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const BASE = `${API}/api/v1`;

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API PATCH ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

// ── Dashboard Stats ────────────────────────────────────────────────────────

export interface DashboardStats {
  calls: {
    today: number;
    live: number;
    completed_today: number;
    avg_duration_seconds: number;
  };
  ai: {
    runs_today: number;
    handled_today: number;
    escalated_today: number;
    handle_rate_pct: number;
    avg_latency_ms: number;
    intent_breakdown: Record<string, number>;
  };
  leads: {
    today: number;
    hot: number;
    stage_breakdown: Record<string, number>;
  };
  appointments: { today: number };
  handoffs: { today: number };
}

export const fetchDashboardStats = () =>
  get<DashboardStats>("/agents/stats");

// ── Agent Runs (Conversations) ─────────────────────────────────────────────

export interface AgentRun {
  id: string;
  status: "running" | "completed" | "escalated" | "failed";
  intent: string | null;
  input_text: string | null;
  output_text: string | null;
  latency_ms: number | null;
  created_at: string;
}

export interface AgentRunDetail extends AgentRun {
  tool_calls: {
    tool_name: string;
    status: string;
    latency_ms: number | null;
    created_at: string;
  }[];
}

export const fetchAgentRuns = (limit = 50) =>
  get<AgentRun[]>(`/agents/runs?limit=${limit}`);

export const fetchAgentRunDetail = (runId: string) =>
  get<AgentRunDetail>(`/agents/runs/${runId}`);

// ── Live Calls ─────────────────────────────────────────────────────────────

export interface LiveCall {
  call_id: string;
  customer_name: string;
  from_number: string;
  duration_seconds: number;
  conversation_id: string | null;
  intent: string | null;
}

export interface RecentCall {
  call_id: string;
  customer_name: string;
  from_number: string;
  status: string;
  duration_seconds: number | null;
  ended_at: string | null;
  created_at: string;
}

export interface CallStats {
  today_total: number;
  today_completed: number;
  live_now: number;
  avg_duration_seconds: number;
}

export const fetchLiveCalls = () =>
  get<LiveCall[]>("/calls/public/live");

export const fetchRecentCalls = (limit = 20) =>
  get<RecentCall[]>(`/calls/public/recent?limit=${limit}`);

export const fetchCallStats = () =>
  get<CallStats>("/calls/public/stats");

// ── Leads ──────────────────────────────────────────────────────────────────

export interface LeadItem {
  id: string;
  customer_name: string;
  customer_phone: string;
  status: string;
  score: "HOT" | "WARM" | "COLD";
  budget: string | null;
  budget_raw: number | null;
  requirements: Record<string, unknown>;
  requirement_label: string;
  crm_id: string | null;
  created_at: string;
}

export interface LeadStats {
  total: number;
  hot: number;
  new: number;
  stage_breakdown: Record<string, number>;
}

export const fetchLeads = (limit = 50) =>
  get<LeadItem[]>(`/leads/public/list?limit=${limit}`);

export const fetchLeadStats = () =>
  get<LeadStats>("/leads/public/stats");

// ── Utilities ──────────────────────────────────────────────────────────────

/** Format seconds → MM:SS */
export function fmtDuration(secs: number | null | undefined): string {
  if (!secs) return "—";
  const m = Math.floor(secs / 60).toString().padStart(2, "0");
  const s = (secs % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

/** Format ISO string → HH:MM */
export function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

// ── Knowledge Base ─────────────────────────────────────────────────────────

export interface KnowledgeDoc {
  id: string;
  title: string;
  file_name: string | null;
  file_type: string;
  file_size_bytes: number | null;
  status: "pending" | "processing" | "indexed" | "failed";
  chunk_count: number | null;
  error: string | null;
  created_at: string;
}

export const fetchKnowledgeDocs = () =>
  get<KnowledgeDoc[]>("/knowledge/public/list");

export async function uploadKnowledgeDoc(
  file: File,
  title: string
): Promise<KnowledgeDoc> {
  const form = new FormData();
  form.append("file", file);
  form.append("title", title);
  const res = await fetch(`${BASE}/knowledge/public/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function deleteKnowledgeDoc(docId: string): Promise<void> {
  const res = await fetch(`${BASE}/knowledge/public/${docId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
}

// ─── Integrations ──────────────────────────────────────────────────────────

export interface IntegrationItem {
  id: string;
  integration_type: string;
  status: "connected" | "disconnected" | "error" | "pending";
  display_name: string | null;
  last_synced_at: string | null;
  error_message: string | null;
  is_active: boolean;
}

export const fetchIntegrations = () =>
  get<IntegrationItem[]>("/integrations/public/list");

// ── Utilities ──────────────────────────────────────────────────────────────

/** Format bytes → human readable */
export function fmtBytes(bytes: number | null | undefined): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

export function fmtTimeFull(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

// ── Business Profile ───────────────────────────────────────────────────────────────────

export interface BusinessProfile {
  id: string;
  name: string;
  industry: string;
  phone: string | null;
  email: string | null;
  website: string | null;
  timezone: string;
  working_hours: Record<string, { open: string | null; close: string | null }>;
  services: string[] | null;
  status: string;
  settings: Record<string, unknown>;
}

export const fetchBusinessProfile = () =>
  get<BusinessProfile>("/businesses/public/profile");

export const updateBusinessProfile = (data: Partial<Omit<BusinessProfile, "id" | "status">>) =>
  patch<BusinessProfile>("/businesses/public/profile", data);
