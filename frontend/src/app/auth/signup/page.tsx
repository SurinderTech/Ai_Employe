"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { Bot, Mail, Lock, User, Phone, Eye, EyeOff, ArrowRight, CheckCircle, ShieldCheck } from "lucide-react";

const INDUSTRIES = [
  "Real Estate", "Healthcare / Clinic", "Automotive", "Education",
  "Retail / E-commerce", "Financial Services", "Hospitality", "Legal", "Other",
];

type Step = 1 | 2 | 3; // 1=account, 2=verify email OTP, 3=business

export default function SignupPage() {
  const router = useRouter();
  const { register, verifyEmail, createBusiness } = useAuth();

  const [step, setStep] = useState<Step>(1);
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Step 1 fields
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");

  // Step 2 field
  const [otpCode, setOtpCode] = useState("");
  // Token from verify-email, passed directly to createBusiness
  const [verifiedToken, setVerifiedToken] = useState<string | null>(null);

  // Step 3 fields
  const [bizName, setBizName] = useState("");
  const [industry, setIndustry] = useState(INDUSTRIES[0]);
  const [bizPhone, setBizPhone] = useState("");

  // ── Step 1: create account ───────────────────────────────────────────────
  const handleStep1 = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) { setError("Password must be at least 8 characters"); return; }
    setLoading(true);
    try {
      await register(name, email, password, phone);
      // Backend sends OTP to email — move to verification step
      setStep(2);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  // ── Step 2: verify email OTP ─────────────────────────────────────────────
  const handleStep2 = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const token = await verifyEmail(email, otpCode.trim());
      setVerifiedToken(token);
      setStep(3);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  };

  // ── Step 3: create business ──────────────────────────────────────────────
  const handleStep3 = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      // Pass the verified token directly — no stale-state risk
      await createBusiness(bizName, industry, bizPhone || undefined, verifiedToken ?? undefined);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create business");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: "100%", paddingLeft: 38, paddingRight: 14, paddingTop: 11, paddingBottom: 11,
    background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)",
    borderRadius: 12, color: "#fff", fontSize: "0.875rem", outline: "none", fontFamily: "inherit",
  };

  const STEPS = [
    { label: "Your Account" },
    { label: "Verify Email" },
    { label: "Your Business" },
  ];

  return (
    <div className="auth-bg">
      <div className="auth-card fade-in" style={{ maxWidth: 460 }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 28 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 13,
            background: "linear-gradient(135deg, #4361ee, #2f4acb)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 8px 24px rgba(67,97,238,0.4)",
          }}>
            <Bot size={20} color="#fff" />
          </div>
          <p style={{ fontWeight: 800, fontSize: "1rem", color: "#fff" }}>VoxAI</p>
        </div>

        {/* Steps indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 24 }}>
          {STEPS.map((s, i) => {
            const n = (i + 1) as Step;
            return (
              <div key={n} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{
                  width: 28, height: 28, borderRadius: "50%",
                  background: n <= step ? "linear-gradient(135deg, #4361ee, #2f4acb)" : "rgba(255,255,255,0.08)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "0.7rem", fontWeight: 700,
                  color: n <= step ? "#fff" : "rgba(255,255,255,0.4)",
                  transition: "all 0.3s",
                }}>
                  {n < step ? <CheckCircle size={14} /> : n}
                </div>
                <span style={{ fontSize: "0.72rem", color: n === step ? "rgba(255,255,255,0.8)" : "rgba(255,255,255,0.35)" }}>
                  {s.label}
                </span>
                {i < STEPS.length - 1 && (
                  <div style={{ width: 24, height: 1, background: "rgba(255,255,255,0.12)" }} />
                )}
              </div>
            );
          })}
        </div>

        {/* ── Step 1: Account ── */}
        {step === 1 && (
          <>
            <h1 style={{ fontSize: "1.4rem", fontWeight: 700, color: "#fff", marginBottom: 4 }}>
              Create your account
            </h1>
            <p style={{ fontSize: "0.82rem", color: "rgba(255,255,255,0.45)", marginBottom: 24 }}>
              Start your AI Employee — free for 14 days
            </p>

            <form onSubmit={handleStep1} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ position: "relative" }}>
                <User size={14} style={{ position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)", color: "rgba(255,255,255,0.3)" }} />
                <input id="signup-name" type="text" placeholder="Full name" value={name} onChange={e => setName(e.target.value)} required style={inputStyle} />
              </div>
              <div style={{ position: "relative" }}>
                <Mail size={14} style={{ position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)", color: "rgba(255,255,255,0.3)" }} />
                <input id="signup-email" type="email" placeholder="Email address" value={email} onChange={e => setEmail(e.target.value)} required style={inputStyle} />
              </div>
              <div style={{ position: "relative" }}>
                <Phone size={14} style={{ position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)", color: "rgba(255,255,255,0.3)" }} />
                <input id="signup-phone" type="tel" placeholder="Phone number (optional)" value={phone} onChange={e => setPhone(e.target.value)} style={inputStyle} />
              </div>
              <div style={{ position: "relative" }}>
                <Lock size={14} style={{ position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)", color: "rgba(255,255,255,0.3)" }} />
                <input id="signup-password" type={showPass ? "text" : "password"} placeholder="Password (min 8 chars)" value={password} onChange={e => setPassword(e.target.value)} required style={{ ...inputStyle, paddingRight: 40 }} />
                <button type="button" onClick={() => setShowPass(!showPass)} style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "rgba(255,255,255,0.35)" }}>
                  {showPass ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>

              {error && (
                <div style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 10, padding: "10px 14px", fontSize: "0.8rem", color: "#fca5a5" }}>
                  ⚠ {error}
                </div>
              )}

              <button id="btn-signup" type="submit" disabled={loading}
                style={{ width: "100%", padding: "13px 0", borderRadius: 12, border: "none", cursor: loading ? "not-allowed" : "pointer", background: "linear-gradient(135deg, #4361ee, #2f4acb)", color: "#fff", fontWeight: 700, fontSize: "0.9rem", fontFamily: "inherit", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, boxShadow: "0 8px 24px rgba(67,97,238,0.35)", marginTop: 4 }}>
                {loading ? "Creating account..." : <><span>Continue</span> <ArrowRight size={16} /></>}
              </button>
            </form>
          </>
        )}

        {/* ── Step 2: Verify Email OTP ── */}
        {step === 2 && (
          <>
            <h1 style={{ fontSize: "1.4rem", fontWeight: 700, color: "#fff", marginBottom: 4 }}>
              Verify your email 📧
            </h1>
            <p style={{ fontSize: "0.82rem", color: "rgba(255,255,255,0.45)", marginBottom: 24 }}>
              We sent a 6-digit code to <strong style={{ color: "rgba(255,255,255,0.7)" }}>{email}</strong>. Enter it below to continue.
            </p>

            <form onSubmit={handleStep2} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ position: "relative" }}>
                <ShieldCheck size={14} style={{ position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)", color: "rgba(255,255,255,0.3)" }} />
                <input
                  id="otp-code"
                  type="text"
                  placeholder="6-digit verification code"
                  value={otpCode}
                  onChange={e => setOtpCode(e.target.value)}
                  required
                  maxLength={6}
                  style={{ ...inputStyle, letterSpacing: "0.2em", textAlign: "center", paddingLeft: 14 }}
                />
              </div>

              {error && (
                <div style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 10, padding: "10px 14px", fontSize: "0.8rem", color: "#fca5a5" }}>
                  ⚠ {error}
                </div>
              )}

              <button id="btn-verify-email" type="submit" disabled={loading}
                style={{ width: "100%", padding: "13px 0", borderRadius: 12, border: "none", cursor: loading ? "not-allowed" : "pointer", background: "linear-gradient(135deg, #4361ee, #2f4acb)", color: "#fff", fontWeight: 700, fontSize: "0.9rem", fontFamily: "inherit", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, boxShadow: "0 8px 24px rgba(67,97,238,0.35)", marginTop: 4 }}>
                {loading ? "Verifying..." : <><span>Verify Email</span> <ArrowRight size={16} /></>}
              </button>

              <button type="button" onClick={() => setStep(1)}
                style={{ background: "none", border: "none", color: "rgba(255,255,255,0.4)", fontSize: "0.8rem", cursor: "pointer", marginTop: 4 }}>
                ← Back to account details
              </button>
            </form>
          </>
        )}

        {/* ── Step 3: Business setup ── */}
        {step === 3 && (
          <>
            <h1 style={{ fontSize: "1.4rem", fontWeight: 700, color: "#fff", marginBottom: 4 }}>
              Set up your business 🏢
            </h1>
            <p style={{ fontSize: "0.82rem", color: "rgba(255,255,255,0.45)", marginBottom: 24 }}>
              Your AI Employee will work exclusively for this business
            </p>

            <form onSubmit={handleStep3} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ position: "relative" }}>
                <span style={{ position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)", fontSize: "1rem" }}>🏢</span>
                <input id="biz-name" type="text" placeholder="Business name (e.g. ABC Realty)" value={bizName} onChange={e => setBizName(e.target.value)} required style={{ ...inputStyle, paddingLeft: 38 }} />
              </div>

              <div style={{ position: "relative" }}>
                <span style={{ position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)", fontSize: "0.95rem" }}>🏭</span>
                <select id="biz-industry" value={industry} onChange={e => setIndustry(e.target.value)}
                  style={{ ...inputStyle, paddingLeft: 38, cursor: "pointer", appearance: "none" }}>
                  {INDUSTRIES.map(i => <option key={i} value={i} style={{ background: "#1e1b4b" }}>{i}</option>)}
                </select>
              </div>

              <div style={{ position: "relative" }}>
                <Phone size={14} style={{ position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)", color: "rgba(255,255,255,0.3)" }} />
                <input id="biz-phone" type="tel" placeholder="Business phone (optional)" value={bizPhone} onChange={e => setBizPhone(e.target.value)} style={inputStyle} />
              </div>

              {/* Feature bullets */}
              <div style={{ background: "rgba(67,97,238,0.1)", border: "1px solid rgba(67,97,238,0.2)", borderRadius: 12, padding: "12px 14px", display: "flex", flexDirection: "column", gap: 6 }}>
                {["AI answers every call 24/7", "Auto-qualifies leads, books appointments", "Updates CRM & sends WhatsApp"].map(f => (
                  <div key={f} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.78rem", color: "rgba(255,255,255,0.7)" }}>
                    <CheckCircle size={13} color="#10b981" /> {f}
                  </div>
                ))}
              </div>

              {error && (
                <div style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 10, padding: "10px 14px", fontSize: "0.8rem", color: "#fca5a5" }}>
                  ⚠ {error}
                </div>
              )}

              <button id="btn-create-business" type="submit" disabled={loading}
                style={{ width: "100%", padding: "13px 0", borderRadius: 12, border: "none", cursor: loading ? "not-allowed" : "pointer", background: "linear-gradient(135deg, #4361ee, #2f4acb)", color: "#fff", fontWeight: 700, fontSize: "0.9rem", fontFamily: "inherit", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, boxShadow: "0 8px 24px rgba(67,97,238,0.35)", marginTop: 4 }}>
                {loading ? "Setting up..." : <><span>Launch my AI Employee 🚀</span></>}
              </button>
            </form>
          </>
        )}

        <div style={{ textAlign: "center", marginTop: 20 }}>
          <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.4)" }}>
            Already have an account?{" "}
            <Link href="/auth/login" style={{ color: "#818cf8", fontWeight: 600, textDecoration: "none" }}>Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
