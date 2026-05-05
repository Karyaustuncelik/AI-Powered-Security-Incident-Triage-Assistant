// Landing page — Apple-quality hero with scroll-triggered animations and feature showcase.

import { useEffect, useRef, useState } from "react";
import type { Route } from "./NavBar";

type Props = {
  onNavigate: (route: Route) => void;
};

// Typewriter effect hook
function useTypewriter(texts: string[], speed = 80, pause = 2000) {
  const [display, setDisplay] = useState("");
  const [textIndex, setTextIndex] = useState(0);
  const [charIndex, setCharIndex] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const current = texts[textIndex];
    const timeout = setTimeout(() => {
      if (!isDeleting) {
        setDisplay(current.slice(0, charIndex + 1));
        if (charIndex + 1 === current.length) {
          setTimeout(() => setIsDeleting(true), pause);
        } else {
          setCharIndex(charIndex + 1);
        }
      } else {
        setDisplay(current.slice(0, charIndex));
        if (charIndex === 0) {
          setIsDeleting(false);
          setTextIndex((textIndex + 1) % texts.length);
        } else {
          setCharIndex(charIndex - 1);
        }
      }
    }, isDeleting ? speed / 2 : speed);
    return () => clearTimeout(timeout);
  }, [charIndex, isDeleting, textIndex, texts, speed, pause]);

  return display;
}

// Scroll reveal hook
function useScrollReveal() {
  const ref = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(el);
        }
      },
      { threshold: 0.15 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { ref, isVisible };
}

const TYPED_WORDS = [
  "Reconnaissance",
  "Exploitation",
  "Kill Chain Analysis",
  "Threat Intelligence",
  "Incident Triage",
];

const FEATURES = [
  {
    id: "dashboard",
    route: "/dashboard" as Route,
    icon: "shield",
    title: "Incident Dashboard",
    desc: "Real-time security incident triage with rule-based risk scoring and AI-powered explanations. Prioritize threats with deterministic precision.",
    gradient: "linear-gradient(135deg, #22d3ee, #3b82f6)",
    stats: ["150+ Incident Types", "Real-time Scoring", "Auto-prioritization"],
  },
  {
    id: "nebula",
    route: "/sirius" as Route,
    icon: "terminal",
    title: "SIRIUS AI Copilot",
    desc: "Your AI-powered red team companion. Recon, exploit analysis, attack chain generation, and professional report writing — all in one terminal.",
    gradient: "linear-gradient(135deg, #a855f7, #ec4899)",
    stats: ["5 Attack Modes", "Streaming Output", "MITRE ATT&CK"],
  },
  {
    id: "attack-map",
    route: "/attack-map" as Route,
    icon: "globe",
    title: "3D Attack Map",
    desc: "Visualize attack vectors on an interactive globe. Track threat origins, correlate geolocation data, and identify impossible travel patterns.",
    gradient: "linear-gradient(135deg, #10b981, #22d3ee)",
    stats: ["Global Visualization", "Geo-correlation", "Live Tracking"],
  },
  {
    id: "kill-chain",
    route: "/kill-chain" as Route,
    icon: "layers",
    title: "Kill Chain Builder",
    desc: "Construct MITRE ATT&CK-aligned attack chains visually. Drag and drop techniques, map tooling, and generate professional reports.",
    gradient: "linear-gradient(135deg, #f59e0b, #ef4444)",
    stats: ["Visual Editor", "MITRE Mapping", "Auto Reports"],
  },
];

const STATS = [
  { value: "7+", label: "Incident Categories" },
  { value: "5", label: "Attack Modes" },
  { value: "< 100ms", label: "Triage Speed" },
  { value: "24/7", label: "Monitoring" },
];

function FeatureIcon({ type }: { type: string }) {
  const icons: Record<string, JSX.Element> = {
    shield: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </svg>
    ),
    terminal: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
      </svg>
    ),
    globe: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
      </svg>
    ),
    layers: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>
      </svg>
    ),
  };
  return icons[type] || null;
}

export function LandingPage({ onNavigate }: Props) {
  const typedText = useTypewriter(TYPED_WORDS, 70, 1800);
  const heroReveal = useScrollReveal();
  const featuresReveal = useScrollReveal();
  const statsReveal = useScrollReveal();
  const ctaReveal = useScrollReveal();

  return (
    <div className="landing">
      {/* Hero Section */}
      <section className="landing-hero" ref={heroReveal.ref}>
        <div className={`landing-hero-content ${heroReveal.isVisible ? "revealed" : ""}`}>
          <div className="landing-eyebrow">
            <span className="landing-eyebrow-dot" />
            <span className="section-label">Next-Gen Security Operations Platform</span>
          </div>

          <h1 className="landing-title">
            <span className="landing-title-line">Offensive Security,</span>
            <span className="landing-title-line">
              <span className="text-gradient">Redefined.</span>
            </span>
          </h1>

          <div className="landing-typed-wrapper">
            <span className="landing-typed-prefix">{">"}</span>
            <span className="landing-typed-text">{typedText}</span>
            <span className="landing-cursor">|</span>
          </div>

          <p className="landing-subtitle">
            AI-powered incident triage, red team copilot, and attack visualization —
            all in one platform built for security professionals who demand precision.
          </p>

          <div className="landing-cta-group">
            <button className="btn btn-primary landing-cta-main" onClick={() => onNavigate("/dashboard")}>
              <span>Enter Dashboard</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </button>
            <button className="btn landing-cta-secondary" onClick={() => onNavigate("/sirius")}>
              <span className="nb-cta-pulse" />
              Launch SIRIUS AI
            </button>
          </div>
        </div>

        {/* Orbital decoration */}
        <div className="landing-hero-visual">
          <div className="orbital-system">
            <div className="orbital-ring orbital-ring-1" />
            <div className="orbital-ring orbital-ring-2" />
            <div className="orbital-ring orbital-ring-3" />
            <div className="orbital-core">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="url(#shieldGrad)"/>
                <defs>
                  <linearGradient id="shieldGrad" x1="4" y1="2" x2="20" y2="22">
                    <stop offset="0%" stopColor="#22d3ee"/>
                    <stop offset="100%" stopColor="#a855f7"/>
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <div className="orbital-dot orbital-dot-1" />
            <div className="orbital-dot orbital-dot-2" />
            <div className="orbital-dot orbital-dot-3" />
          </div>
        </div>
      </section>

      {/* Glow separator */}
      <div className="glow-line" style={{ margin: "0 auto", maxWidth: 600 }} />

      {/* Stats bar */}
      <section className="landing-stats" ref={statsReveal.ref}>
        {STATS.map((stat, i) => (
          <div
            key={stat.label}
            className={`landing-stat ${statsReveal.isVisible ? "revealed" : ""}`}
            style={{ animationDelay: `${i * 100}ms` }}
          >
            <span className="landing-stat-value">{stat.value}</span>
            <span className="landing-stat-label">{stat.label}</span>
          </div>
        ))}
      </section>

      {/* Features */}
      <section className="landing-features" ref={featuresReveal.ref}>
        <div className="landing-section-header">
          <span className="section-label">Capabilities</span>
          <h2 className="landing-section-title">Everything a red team needs.</h2>
          <p className="landing-section-desc">
            From automated incident triage to AI-powered attack planning —
            purpose-built tools that don't exist anywhere else.
          </p>
        </div>

        <div className="landing-features-grid">
          {FEATURES.map((feature, i) => (
            <button
              key={feature.id}
              className={`landing-feature-card glass-card ${featuresReveal.isVisible ? "revealed" : ""}`}
              style={{ animationDelay: `${i * 120}ms` }}
              onClick={() => onNavigate(feature.route)}
            >
              <div className="landing-feature-icon" style={{ background: feature.gradient }}>
                <FeatureIcon type={feature.icon} />
              </div>
              <h3 className="landing-feature-title">{feature.title}</h3>
              <p className="landing-feature-desc">{feature.desc}</p>
              <div className="landing-feature-stats">
                {feature.stats.map((s) => (
                  <span key={s} className="landing-feature-stat">{s}</span>
                ))}
              </div>
              <div className="landing-feature-arrow">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M5 12h14M12 5l7 7-7 7"/>
                </svg>
              </div>
            </button>
          ))}
        </div>
      </section>

      {/* CTA section */}
      <section className="landing-bottom-cta" ref={ctaReveal.ref}>
        <div className={`landing-bottom-cta-content ${ctaReveal.isVisible ? "revealed" : ""}`}>
          <h2 className="landing-bottom-title">
            Ready to operate at <span className="text-gradient">a higher level</span>?
          </h2>
          <p className="landing-bottom-desc">
            Start with the incident dashboard or jump straight into SIRIUS AI.
          </p>
          <div className="landing-cta-group" style={{ justifyContent: "center" }}>
            <button className="btn btn-primary landing-cta-main" onClick={() => onNavigate("/dashboard")}>
              Open Dashboard
            </button>
            <button className="btn" onClick={() => onNavigate("/sirius")}>
              Try SIRIUS AI
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="glow-line" />
        <div className="landing-footer-content">
          <span className="landing-footer-brand">SIRIUS<span style={{ color: "var(--cyan-glow)" }}>AI</span></span>
          <span className="landing-footer-text">AI-Powered Security Operations Platform</span>
        </div>
      </footer>
    </div>
  );
}
