"use client";
/**
 * AuthContext — lightweight multi-tenant auth state.
 * Matches the OTP-based backend flow:
 *   Register:  POST /auth/register      → returns { message }  (no token yet)
 *   Verify:    POST /auth/verify-email  → returns { access_token, refresh_token }
 *   Login:     POST /auth/login         → returns { requires_otp: true }  (2FA OTP sent)
 *   OTP login: POST /auth/verify-otp   → returns { access_token, refresh_token }
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

export interface AuthBusiness {
  id: string;
  name: string;
  slug: string;
  industry: string;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  business: AuthBusiness | null;
  loading: boolean;
}

interface AuthContextValue extends AuthState {
  /** Step 1 of signup: creates account, sends verification email. Returns { message }. */
  register: (name: string, email: string, password: string, phone?: string) => Promise<{ message: string }>;
  /** Step 2 of signup: verifies email OTP, returns the JWT access token. */
  verifyEmail: (email: string, code: string) => Promise<string>;
  /** Step 3 of signup: creates first business using the freshly verified token. */
  createBusiness: (name: string, industry: string, phone?: string, explicitToken?: string) => Promise<AuthBusiness>;
  /** Step 1 of login: submits credentials. Throws with err.requiresOtp=true if OTP was sent. */
  login: (email: string, password: string) => Promise<void>;
  /** Step 2 of login: verifies 2FA OTP and completes auth session. */
  verifyLoginOtp: (email: string, code: string) => Promise<void>;
  logout: () => void;
  setActiveBusiness: (b: AuthBusiness) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Safely read token from localStorage — returns null for missing/invalid values. */
function getStoredToken(): string | null {
  try {
    const t = localStorage.getItem("ai_token");
    if (!t || t === "null" || t === "undefined") return null;
    return t;
  } catch {
    return null;
  }
}

/** After receiving a JWT, fetch user profile + business and persist to state. */
async function fetchAndStoreSession(
  token: string,
  email: string,
  setState: React.Dispatch<React.SetStateAction<AuthState>>,
) {
  const meRes = await fetch(`${API}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const user: AuthUser = meRes.ok
    ? await meRes.json()
    : { id: "", email, full_name: email, role: "owner" };

  const bizRes = await fetch(`${API}/api/v1/businesses?limit=1`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const bizData = bizRes.ok ? await bizRes.json() : [];
  const business: AuthBusiness | null =
    Array.isArray(bizData) && bizData.length > 0 ? bizData[0] : null;

  localStorage.setItem("ai_token", token);
  localStorage.setItem("ai_user", JSON.stringify(user));
  if (business) localStorage.setItem("ai_business", JSON.stringify(business));

  setState({ token, user, business, loading: false });
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: null,
    user: null,
    business: null,
    loading: true,
  });

  // Hydrate from localStorage on mount
  useEffect(() => {
    try {
      const token = getStoredToken();
      const user = localStorage.getItem("ai_user");
      const business = localStorage.getItem("ai_business");
      setState({
        token,
        user: user ? JSON.parse(user) : null,
        business: business ? JSON.parse(business) : null,
        loading: false,
      });
    } catch {
      setState((s) => ({ ...s, loading: false }));
    }
  }, []);

  // ── Login step 1: submit credentials ──────────────────────────────────────
  const login = useCallback(async (email: string, password: string) => {
    console.log(`[auth] POST ${API}/api/v1/auth/login`);
    let res: Response;
    try {
      res = await fetch(`${API}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
    } catch {
      throw new Error("Backend not reachable. Is it running on " + API + "?");
    }

    const data = await res.json().catch(() => ({}));
    console.log(`[auth] /login → ${res.status}`, data);

    if (!res.ok) {
      const detail: string = data.detail ?? "Login failed";
      // 403 "not verified" — user registered but never completed email verification
      if (res.status === 403 && detail.toLowerCase().includes("not verified")) {
        const err = new Error(detail) as Error & { needsVerification: boolean };
        err.needsVerification = true;
        throw err;
      }
      throw new Error(detail);
    }

    if (data.requires_otp) {
      // 2FA: OTP sent to email — caller must call verifyLoginOtp()
      const err = new Error(data.message ?? "OTP sent to your email") as Error & { requiresOtp: boolean };
      err.requiresOtp = true;
      throw err;
    }

    // Direct token (no 2FA — future-proof)
    if (data.access_token) {
      await fetchAndStoreSession(data.access_token, email, setState);
    }
  }, []);

  // ── Login step 2: verify 2FA OTP ──────────────────────────────────────────
  const verifyLoginOtp = useCallback(async (email: string, code: string) => {
    console.log(`[auth] POST ${API}/api/v1/auth/verify-otp`);
    const res = await fetch(`${API}/api/v1/auth/verify-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, code }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail ?? "Invalid or expired OTP");
    const token: string = data.access_token;
    if (!token) throw new Error("No token in verify-otp response");
    await fetchAndStoreSession(token, email, setState);
  }, []);

  // ── Signup step 1: register account ───────────────────────────────────────
  const register = useCallback(async (
    full_name: string,
    email: string,
    password: string,
    phone?: string,
  ) => {
    const res = await fetch(`${API}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // Send phone as null (not "") — Pydantic v2 rejects empty strings for Optional[str]
      body: JSON.stringify({ full_name, email, password, phone: phone || null }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      console.error("[register] error:", data);
      throw new Error(data.detail ?? "Registration failed");
    }
    // Backend returns: { message: "Registration successful! Please check your email..." }
    return data as { message: string };
  }, []);

  // ── Signup step 2: verify email OTP ───────────────────────────────────────
  const verifyEmail = useCallback(async (email: string, code: string): Promise<string> => {
    const res = await fetch(`${API}/api/v1/auth/verify-email`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, code }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail ?? "Invalid verification code");
    const token: string = data.access_token;
    if (!token) throw new Error("No access token in verify-email response");
    // Persist token immediately so createBusiness can read it from localStorage
    localStorage.setItem("ai_token", token);
    setState((s) => ({ ...s, token }));
    return token;
  }, []);

  // ── Signup step 3: create first business ──────────────────────────────────
  const createBusiness = useCallback(async (
    name: string,
    industry: string,
    phone?: string,
    explicitToken?: string,
  ): Promise<AuthBusiness> => {
    // Prefer explicitly passed token > localStorage > React state
    // (React state can still be stale right after verifyEmail)
    const token = explicitToken || getStoredToken() || state.token;
    if (!token) {
      console.error("[createBusiness] No auth token available");
      throw new Error("Not authenticated. Please complete email verification first.");
    }
    console.log("[createBusiness] token:", token.slice(0, 20) + "...");
    const res = await fetch(`${API}/api/v1/businesses`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ name, industry, phone }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail ?? "Failed to create business");
    const business: AuthBusiness = data;
    localStorage.setItem("ai_business", JSON.stringify(business));
    setState((s) => ({ ...s, business }));
    // Refresh full session (user profile + business)
    fetchAndStoreSession(token, "", setState).catch(() => {});
    return business;
  }, [state.token]);

  // ── Helpers ───────────────────────────────────────────────────────────────
  const setActiveBusiness = useCallback((business: AuthBusiness) => {
    localStorage.setItem("ai_business", JSON.stringify(business));
    setState((s) => ({ ...s, business }));
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("ai_token");
    localStorage.removeItem("ai_user");
    localStorage.removeItem("ai_business");
    setState({ token: null, user: null, business: null, loading: false });
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        verifyLoginOtp,
        register,
        verifyEmail,
        createBusiness,
        logout,
        setActiveBusiness,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
