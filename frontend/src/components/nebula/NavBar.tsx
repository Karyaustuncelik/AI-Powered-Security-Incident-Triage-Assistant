// Top navigation — glassmorphism navbar with animated brand and glow effects.

import { useEffect, useState } from "react";

type Route = "/" | "/dashboard" | "/sirius" | "/attack-map" | "/kill-chain" | "/threat-intel" | "/pentest" | "/agent";

type Props = {
  active: Route;
  onNavigate: (route: Route) => void;
};

const NAV_ITEMS: { route: Route; label: string; icon: string }[] = [
  { route: "/", label: "Home", icon: "01" },
  { route: "/dashboard", label: "Dashboard", icon: "02" },
  { route: "/sirius", label: "SIRIUS AI", icon: "03" },
  { route: "/attack-map", label: "Attack Map", icon: "04" },
  { route: "/kill-chain", label: "Kill Chain", icon: "05" },
  { route: "/threat-intel", label: "Threat Intel", icon: "06" },
  { route: "/pentest", label: "Pentest", icon: "07" },
  { route: "/agent", label: "AI Agent", icon: "08" },
];

export function NavBar({ active, onNavigate }: Props) {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <nav className={`nb-nav ${scrolled ? "nb-nav--scrolled" : ""}`}>
      <div className="nb-nav-inner">
        {/* Brand */}
        <button
          className="nb-brand"
          onClick={() => onNavigate("/")}
        >
          <div className="nb-brand-icon">
            <div className="nb-brand-ring" />
            <div className="nb-brand-core" />
          </div>
          <span className="nb-brand-text">SIRIUS</span>
          <span className="nb-brand-tag">AI</span>
        </button>

        {/* Navigation links */}
        <div className={`nb-nav-links ${menuOpen ? "nb-nav-links--open" : ""}`}>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.route}
              className={`nb-nav-link ${active === item.route ? "is-active" : ""}`}
              onClick={() => {
                onNavigate(item.route);
                setMenuOpen(false);
              }}
            >
              <span className="nb-nav-link-id">{item.icon}</span>
              <span>{item.label}</span>
              {active === item.route && <span className="nb-nav-link-dot" />}
            </button>
          ))}
        </div>

        {/* CTA */}
        <div className="nb-nav-actions">
          <div className="nb-status-dot" />
          <button
            className="nb-nav-cta"
            onClick={() => onNavigate("/sirius")}
          >
            <span className="nb-cta-pulse" />
            Launch SIRIUS
          </button>
        </div>

        {/* Mobile menu toggle */}
        <button
          className="nb-menu-toggle"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle menu"
        >
          <span className={`nb-menu-bar ${menuOpen ? "open" : ""}`} />
          <span className={`nb-menu-bar ${menuOpen ? "open" : ""}`} />
          <span className={`nb-menu-bar ${menuOpen ? "open" : ""}`} />
        </button>
      </div>
    </nav>
  );
}

export type { Route };
