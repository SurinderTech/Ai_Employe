"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { Bot, Mail, Lock, Eye, EyeOff, ArrowRight, Sparkles, ShieldCheck } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login, verifyLoginOtp, verifyEmail } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  // OTP step (2FA after login)
  const [needsOtp, setNeedsOtp] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  // Email-not-verified step
  const [needsVerification, setNeedsVerification] = useState(false);
  const [verifyCode, setVerifyCode] = useState("");
  const [resendLoading, setResendLoading] = useState(false);
  const [resendMsg, setResendMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: unknown) {
      const e2 = err as Error & { requiresOtp?: boolean; needsVerification?: boolean };
      if (e2.requiresOtp) {
        setNeedsOtp(true);
        setError("");
      } else if (e2.needsVerification) {
        // Account exists but email not verified — show email OTP form
        setNeedsVerification(true);
        setError("");
        // Auto-send a fresh OTP so they don't have to click "resend" first
        setTimeout(() => handleResendVerify(), 300);
      } else {
        setError(e2.message ?? "Login failed");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await verifyLoginOtp(email, otpCode.trim());
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid OTP");
    } finally {
      setLoading(false);
    }
  };

  // Handle email verification for users who registered but never verified
  const handleEmailVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await verifyEmail(email, verifyCode.trim());
      // After verifying, complete login by logging in again
      await login(email, password);
      router.push("/dashboard");
    } catch (err: unknown) {
      const e2 = err as Error & { requiresOtp?: boolean };
      if (e2.requiresOtp) {
        // Now they need the 2FA OTP — email is verified, redirect to OTP step
        setNeedsVerification(false);
        setNeedsOtp(true);
        setError("");
      } else {
        setError(err instanceof Error ? err.message : "Verification failed");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResendVerify = async () => {
    setResendLoading(true);
    setResendMsg("");
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/auth/resend-otp`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, purpose: "email_verify" }),
        }
      );
      const data = await res.json().catch(() => ({}));
      setResendMsg(data.message ?? "Code resent!");
    } catch {
      setResendMsg("Failed to resend. Try again.");
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="auth-bg">
      {/* Floating orbs */}
      <div style={{ position: "absolute", width: 300, height: 300, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(67,97,238,0.18) 0%, transparent 70%)",
        top: "10%", right: "15%", pointerEvents: "none" }} />
      <div style={{ position: "absolute", width: 200, height: 200, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(16,185,129,0.12) 0%, transparent 70%)",
        bottom: "20%", left: "10%", pointerEvents: "none" }} />

      <div className="auth-card fade-in">
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 32 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 14,
            background: "linear-gradient(135deg, #4361ee, #2f4acb)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 8px 24px rgba(67,97,238,0.4)",
          }}>
            <Bot size={22} color="#fff" />
          </div>
          <div>
            <p style={{ fontWeight: 800, fontSize: "1.1rem", color: "#fff", letterSpacing: "-0.02em" }}>VoxAI</p>
            <p style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.45)" }}>AI Business Employee</p>
          </div>
        </div>

        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#fff", marginBottom: 6 }}>
          {needsVerification ? "Verify your email 📧" : needsOtp ? "Check your email 📧" : "Welcome back 👋"}
        </h1>
        <p style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.5)", marginBottom: 28 }}>
          {needsVerification
            ? <>
                Your account isn&apos;t verified yet. We&apos;ve resent a code to{" "}
                <strong style={{ color: "rgba(255,255,255,0.7)" }}>{email}</strong>.
              </>
            : needsOtp
            ? <>A login code was sent to <strong style={{ color: "rgba(255,255,255,0.7)" }}>{email}</strong></>
            : "Sign in to your AI Employee dashboard"
          }
        </p>

        {needsVerification ? (
          /* ── Email verification OTP (user registered but never verified) ── */
          <form onSubmit={handleEmailVerify} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ position: "relative" }}>
              <ShieldCheck size={15} style={{ position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)", color: "rgba(255,255,255,0.3)", pointerEvents: "none" }} />
              <input
                id="login-verify-code"
                type="text"
                placeholder="6-digit verification code"
                value={verifyCode}
                onChange={e => setVerifyCode(e.target.value)}
                required
                maxLength={6}
                autoFocus
                style={{
                  width: "100%", paddingLeft: 38, paddingRight: 14, paddingTop: 11, paddingBottom: 11,
                  background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: 12, color: "#fff", fontSize: "0.875rem", outline: "none",
                  fontFamily: "inherit", letterSpacing: "0.2em", textAlign: "center",
                }}
              />
            </div>

            {error && (
              <div style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 10, padding: "10px 14px", fontSize: "0.8rem", color: "#fca5a5" }}>
                ⚠ {error}
              </div>
            )}
            {resendMsg && (
              <p style={{ fontSize: "0.78rem", color: "#6ee7b7", textAlign: "center", margin: 0 }}>✓ {resendMsg}</p>
            )}

            <button id="btn-verify-email" type="submit" disabled={loading}
              style={{ width: "100%", padding: "13px 0", borderRadius: 12, border: "none", cursor: loading ? "not-allowed" : "pointer",
                background: loading ? "rgba(67,97,238,0.5)" : "linear-gradient(135deg, #4361ee, #2f4acb)",
                color: "#fff", fontWeight: 700, fontSize: "0.9rem", fontFamily: "inherit",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                boxShadow: "0 8px 24px rgba(67,97,238,0.35)", marginTop: 4 }}
            >
              {loading ? "Verifying..." : <>Verify & Sign In <ArrowRight size={16} /></>}
            </button>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <button type="button" onClick={() => { setNeedsVerification(false); setVerifyCode(""); setError(""); }}
                style={{ background: "none", border: "none", color: "rgba(255,255,255,0.4)", fontSize: "0.8rem", cursor: "pointer" }}>
                ← Back
              </button>
              <button type="button" onClick={handleResendVerify} disabled={resendLoading}
                style={{ background: "none", border: "none", color: "#818cf8", fontSize: "0.8rem", cursor: "pointer", fontWeight: 600 }}>
                {resendLoading ? "Sending..." : "Resend code"}
              </button>
            </div>
          </form>
        ) : needsOtp ? (
          /* ── OTP input ── */
          <form onSubmit={handleOtp} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ position: "relative" }}>
              <ShieldCheck size={15} style={{ position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)", color: "rgba(255,255,255,0.3)", pointerEvents: "none" }} />
              <input
                id="login-otp"
                type="text"
                placeholder="6-digit code"
                value={otpCode}
                onChange={e => setOtpCode(e.target.value)}
                required
                maxLength={6}
                autoFocus
                style={{
                  width: "100%", paddingLeft: 38, paddingRight: 14, paddingTop: 11, paddingBottom: 11,
                  background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: 12, color: "#fff", fontSize: "0.875rem", outline: "none",
                  fontFamily: "inherit", letterSpacing: "0.2em", textAlign: "center",
                }}
              />
            </div>

            {error && (
              <div style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 10, padding: "10px 14px", fontSize: "0.8rem", color: "#fca5a5" }}>
                ⚠ {error}
              </div>
            )}

            <button id="btn-verify-otp" type="submit" disabled={loading}
              style={{ width: "100%", padding: "13px 0", borderRadius: 12, border: "none", cursor: loading ? "not-allowed" : "pointer",
                background: loading ? "rgba(67,97,238,0.5)" : "linear-gradient(135deg, #4361ee, #2f4acb)",
                color: "#fff", fontWeight: 700, fontSize: "0.9rem", fontFamily: "inherit",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                boxShadow: "0 8px 24px rgba(67,97,238,0.35)", marginTop: 4 }}
            >
              {loading ? "Verifying..." : <>Verify & Sign In <ArrowRight size={16} /></>}
            </button>

            <button type="button" onClick={() => { setNeedsOtp(false); setOtpCode(""); setError(""); }}
              style={{ background: "none", border: "none", color: "rgba(255,255,255,0.4)", fontSize: "0.8rem", cursor: "pointer" }}>
              ← Back
            </button>
          </form>
        ) : (
          /* ── Credentials form ── */
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {/* Email */}
            <div style={{ position: "relative" }}>
              <Mail size={15} style={{ position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)", color: "rgba(255,255,255,0.3)", pointerEvents: "none" }} />
              <input
                id="login-email"
                type="email"
                placeholder="Email address"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                style={{
                  width: "100%", paddingLeft: 38, paddingRight: 14, paddingTop: 11, paddingBottom: 11,
                  background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: 12, color: "#fff", fontSize: "0.875rem", outline: "none",
                  fontFamily: "inherit", transition: "border-color 0.15s",
                }}
              />
            </div>

            {/* Password */}
            <div style={{ position: "relative" }}>
              <Lock size={15} style={{ position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)", color: "rgba(255,255,255,0.3)", pointerEvents: "none" }} />
              <input
                id="login-password"
                type={showPass ? "text" : "password"}
                placeholder="Password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                style={{
                  width: "100%", paddingLeft: 38, paddingRight: 40, paddingTop: 11, paddingBottom: 11,
                  background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: 12, color: "#fff", fontSize: "0.875rem", outline: "none",
                  fontFamily: "inherit",
                }}
              />
              <button type="button" onClick={() => setShowPass(!showPass)}
                style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "rgba(255,255,255,0.35)" }}>
                {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>

            {error && (
              <div style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 10, padding: "10px 14px", fontSize: "0.8rem", color: "#fca5a5" }}>
                ⚠ {error}
              </div>
            )}

            <button
              id="btn-login"
              type="submit"
              disabled={loading}
              style={{
                width: "100%", padding: "13px 0", borderRadius: 12, border: "none", cursor: loading ? "not-allowed" : "pointer",
                background: loading ? "rgba(67,97,238,0.5)" : "linear-gradient(135deg, #4361ee, #2f4acb)",
                color: "#fff", fontWeight: 700, fontSize: "0.9rem", fontFamily: "inherit",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                boxShadow: "0 8px 24px rgba(67,97,238,0.35)", transition: "all 0.2s",
                marginTop: 4,
              }}
            >
              {loading ? (
                <><span style={{ width: 16, height: 16, borderRadius: "50%", border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "#fff", animation: "spin 0.8s linear infinite" }} /> Signing in...</>
              ) : (
                <>Sign In <ArrowRight size={16} /></>
              )}
            </button>

            {/* Demo login hint */}
            <p style={{ textAlign: "center", fontSize: "0.72rem", color: "rgba(255,255,255,0.3)", marginTop: -4 }}>
              Backend running? Use your registered email + password.
            </p>
          </form>
        )}

        <div style={{ textAlign: "center", marginTop: 24 }}>
          <p style={{ fontSize: "0.82rem", color: "rgba(255,255,255,0.45)" }}>
            Don't have an account?{" "}
            <Link href="/auth/signup" style={{ color: "#818cf8", fontWeight: 600, textDecoration: "none" }}>
              Create one free
            </Link>
          </p>
        </div>

        {/* Feature strip */}
        <div style={{ marginTop: 28, display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ height: 1, background: "rgba(255,255,255,0.08)" }} />
          <div style={{ display: "flex", justifyContent: "center", gap: 20, paddingTop: 8 }}>
            {["AI Calls 24/7", "Auto Lead Qualify", "CRM Sync"].map(f => (
              <div key={f} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.68rem", color: "rgba(255,255,255,0.35)" }}>
                <Sparkles size={9} />
                {f}
              </div>
            ))}
          </div>
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
