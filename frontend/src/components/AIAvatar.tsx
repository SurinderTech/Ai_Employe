"use client";
/**
 * AIAvatar — Animated realistic AI receptionist.
 * Modes: idle (breathing + float), speaking (glow + waveform + nod), listening.
 * Uses CSS animations — no external library needed.
 */
import Image from "next/image";
import { useState, useEffect } from "react";

interface AIAvatarProps {
  mode?: "idle" | "speaking" | "listening";
  size?: number;
  showWaveform?: boolean;
  showRings?: boolean;
  label?: string;
}

export default function AIAvatar({
  mode = "idle",
  size = 120,
  showRings = true,
  label,
}: AIAvatarProps) {
  const [currentPhrase, setCurrentPhrase] = useState(0);
  const PHRASES = [
    "Hello! How can I help you today?",
    "I'm checking available slots for you...",
    "Let me look that up right away!",
    "Sure, I can schedule a visit for you.",
  ];

  useEffect(() => {
    if (mode !== "speaking") return;
    const t = setInterval(() => {
      setCurrentPhrase((p) => (p + 1) % PHRASES.length);
    }, 2800);
    return () => clearInterval(t);
  }, [mode]);

  const ringColors = ["rgba(67,97,238,0.35)", "rgba(67,97,238,0.2)", "rgba(67,97,238,0.1)"];
  const ringDelays = [0, 0.7, 1.4];

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
      {/* Avatar with rings */}
      <div style={{ position: "relative", width: size + 32, height: size + 32, display: "flex", alignItems: "center", justifyContent: "center" }}>

        {/* Pulse rings (speaking) */}
        {showRings && mode === "speaking" && ringColors.map((color, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              width: size + 8 + i * 12,
              height: size + 8 + i * 12,
              borderRadius: "50%",
              border: `2px solid ${color}`,
              animationName: "ringPulse",
              animationDuration: "2s",
              animationTimingFunction: "ease-out",
              animationIterationCount: "infinite",
              animationDelay: `${ringDelays[i]}s`,
            }}
          />
        ))}

        {/* Static ring (idle/listening) */}
        {mode !== "speaking" && (
          <div style={{
            position: "absolute",
            width: size + 8,
            height: size + 8,
            borderRadius: "50%",
            border: "2px solid rgba(67,97,238,0.2)",
          }} />
        )}

        {/* Avatar image */}
        <div style={{
          width: size,
          height: size,
          borderRadius: "50%",
          overflow: "hidden",
          border: "3px solid #fff",
          boxShadow: mode === "speaking"
            ? "0 0 0 0 rgba(67,97,238,0), 0 8px 32px rgba(67,97,238,0.3)"
            : "0 4px 20px rgba(15,23,42,0.15)",
          animationName: mode === "speaking" ? "speakGlow" : mode === "idle" ? "breathe" : "breathe",
          animationDuration: mode === "speaking" ? "1.2s" : "4s",
          animationTimingFunction: "ease-in-out",
          animationIterationCount: "infinite",
          position: "relative",
          zIndex: 1,
          flexShrink: 0,
        }}>
          <div style={{
            animationName: mode === "speaking" ? "nod" : "breathe",
            animationDuration: mode === "speaking" ? "3s" : "6s",
            animationTimingFunction: "ease-in-out",
            animationIterationCount: "infinite",
            width: "100%",
            height: "100%",
          }}>
            <Image
              src="/ai-avatar.jpg"
              alt="AI Receptionist"
              width={size}
              height={size}
              style={{ objectFit: "cover", objectPosition: "top center", width: "100%", height: "100%" }}
              priority
            />
          </div>
        </div>

        {/* Status dot */}
        <div style={{
          position: "absolute",
          bottom: 16, right: 14,
          width: 14, height: 14,
          borderRadius: "50%",
          background: mode === "speaking" ? "#10b981" : mode === "listening" ? "#f59e0b" : "#10b981",
          border: "2.5px solid #fff",
          zIndex: 2,
          animationName: "livePulse",
          animationDuration: "1.5s",
          animationTimingFunction: "ease-in-out",
          animationIterationCount: "infinite",
        }} />
      </div>

      {/* Speaking subtitle */}
      {mode === "speaking" && (
        <div style={{
          background: "linear-gradient(135deg, #4361ee, #2f4acb)",
          color: "#fff",
          borderRadius: 20,
          padding: "6px 14px",
          fontSize: "0.72rem",
          fontWeight: 500,
          maxWidth: 200,
          textAlign: "center",
          animationName: "fadeInUp",
          animationDuration: "0.3s",
          boxShadow: "0 4px 12px rgba(67,97,238,0.3)",
        }}>
          &ldquo;{PHRASES[currentPhrase]}&rdquo;
        </div>
      )}

      {/* Waveform (speaking) */}
      {mode === "speaking" && (
        <div className="waveform" style={{ justifyContent: "center" }}>
          {Array.from({ length: 8 }).map((_, i) => (
            <span key={i} style={{ background: "var(--primary)" }} />
          ))}
        </div>
      )}

      {label && (
        <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-2)", textAlign: "center" }}>
          {label}
        </p>
      )}
    </div>
  );
}
