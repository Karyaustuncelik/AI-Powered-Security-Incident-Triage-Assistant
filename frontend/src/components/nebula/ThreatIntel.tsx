// Threat Intelligence Feed — Live CVE/exploit dashboard with trend analysis.

import { useEffect, useState, useMemo } from "react";

type CVEEntry = {
  id: string;
  cveId: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low";
  cvss: number;
  vendor: string;
  product: string;
  publishedDate: string;
  exploitAvailable: boolean;
  tags: string[];
};

const VENDORS = ["Microsoft", "Apache", "Google", "Linux", "Cisco", "VMware", "Adobe", "Oracle", "Fortinet", "Palo Alto", "Ivanti", "Atlassian", "Citrix", "F5", "SolarWinds"];
const PRODUCTS: Record<string, string[]> = {
  Microsoft: ["Exchange Server", "Windows", "Office 365", "Azure AD", "SharePoint", "IIS"],
  Apache: ["Log4j", "Struts", "Tomcat", "HTTP Server", "Kafka"],
  Google: ["Chrome", "Android", "Kubernetes", "Cloud Platform"],
  Linux: ["Kernel", "systemd", "sudo", "OpenSSH", "glibc"],
  Cisco: ["IOS", "ASA", "WebEx", "AnyConnect"],
  VMware: ["vCenter", "ESXi", "Workspace ONE", "Horizon"],
  Adobe: ["Acrobat", "ColdFusion", "Commerce", "Creative Cloud"],
  Oracle: ["WebLogic", "Java SE", "MySQL", "Database"],
  Fortinet: ["FortiOS", "FortiGate", "FortiManager", "FortiAnalyzer"],
  "Palo Alto": ["PAN-OS", "GlobalProtect", "Cortex XDR"],
  Ivanti: ["Connect Secure", "Policy Secure", "EPMM"],
  Atlassian: ["Confluence", "Jira", "Bitbucket", "Bamboo"],
  Citrix: ["NetScaler", "ADC", "Gateway", "XenDesktop"],
  F5: ["BIG-IP", "BIG-IQ", "NGINX"],
  SolarWinds: ["Orion", "Serv-U", "Access Rights Manager"],
};
const VULN_TYPES = ["Remote Code Execution", "SQL Injection", "Authentication Bypass", "Privilege Escalation", "XSS", "SSRF", "Path Traversal", "Buffer Overflow", "Deserialization", "Command Injection", "XXE", "CSRF", "Information Disclosure", "Denial of Service", "Memory Corruption"];
const TAGS = ["zero-day", "actively-exploited", "wormable", "ransomware", "apt", "poc-available", "patch-available", "critical-infrastructure"];

function generateCVE(index: number): CVEEntry {
  const year = 2024 + Math.floor(Math.random() * 2);
  const num = 20000 + Math.floor(Math.random() * 30000);
  const vendor = VENDORS[Math.floor(Math.random() * VENDORS.length)];
  const products = PRODUCTS[vendor] || ["Unknown"];
  const product = products[Math.floor(Math.random() * products.length)];
  const vulnType = VULN_TYPES[Math.floor(Math.random() * VULN_TYPES.length)];

  const sevRoll = Math.random();
  let severity: CVEEntry["severity"], cvss: number;
  if (sevRoll < 0.15) { severity = "critical"; cvss = 9.0 + Math.random() * 1.0; }
  else if (sevRoll < 0.4) { severity = "high"; cvss = 7.0 + Math.random() * 2.0; }
  else if (sevRoll < 0.75) { severity = "medium"; cvss = 4.0 + Math.random() * 3.0; }
  else { severity = "low"; cvss = 1.0 + Math.random() * 3.0; }

  const exploitAvailable = Math.random() < 0.35;
  const numTags = Math.floor(Math.random() * 3);
  const tags: string[] = [];
  for (let i = 0; i < numTags; i++) {
    const tag = TAGS[Math.floor(Math.random() * TAGS.length)];
    if (!tags.includes(tag)) tags.push(tag);
  }
  if (exploitAvailable && !tags.includes("poc-available")) tags.push("poc-available");

  const daysAgo = index * 0.5 + Math.random() * 2;
  const date = new Date(Date.now() - daysAgo * 86400000);

  return {
    id: `cve-${index}`,
    cveId: `CVE-${year}-${num}`,
    title: `${vendor} ${product} ${vulnType}`,
    description: `A ${vulnType.toLowerCase()} vulnerability was discovered in ${vendor} ${product} that could allow ${
      severity === "critical" || severity === "high"
        ? "an unauthenticated remote attacker to execute arbitrary code"
        : "an authenticated attacker to access sensitive information"
    } on affected systems.`,
    severity,
    cvss: Math.round(cvss * 10) / 10,
    vendor,
    product,
    publishedDate: date.toISOString().split("T")[0],
    exploitAvailable,
    tags,
  };
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f59e0b",
  medium: "#3b82f6",
  low: "#10b981",
};

export function ThreatIntel() {
  const [cves] = useState<CVEEntry[]>(() => {
    const items: CVEEntry[] = [];
    for (let i = 0; i < 40; i++) items.push(generateCVE(i));
    return items;
  });

  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [exploitFilter, setExploitFilter] = useState(false);
  const [selectedCve, setSelectedCve] = useState<CVEEntry | null>(null);
  const [currentTime, setCurrentTime] = useState(Date.now());

  useEffect(() => {
    const interval = setInterval(() => setCurrentTime(Date.now()), 30000);
    return () => clearInterval(interval);
  }, []);

  const filtered = useMemo(() => {
    return cves.filter((c) => {
      if (severityFilter !== "all" && c.severity !== severityFilter) return false;
      if (exploitFilter && !c.exploitAvailable) return false;
      if (search) {
        const q = search.toLowerCase();
        return (
          c.cveId.toLowerCase().includes(q) ||
          c.title.toLowerCase().includes(q) ||
          c.vendor.toLowerCase().includes(q) ||
          c.product.toLowerCase().includes(q) ||
          c.tags.some((t) => t.includes(q))
        );
      }
      return true;
    });
  }, [cves, search, severityFilter, exploitFilter]);

  const stats = useMemo(() => ({
    total: cves.length,
    critical: cves.filter((c) => c.severity === "critical").length,
    high: cves.filter((c) => c.severity === "high").length,
    exploited: cves.filter((c) => c.exploitAvailable).length,
    _now: currentTime, // force re-render
  }), [cves, currentTime]);

  // Severity distribution for mini chart
  const sevDist = useMemo(() => {
    const dist = { critical: 0, high: 0, medium: 0, low: 0 };
    cves.forEach((c) => dist[c.severity]++);
    const max = Math.max(...Object.values(dist), 1);
    return Object.entries(dist).map(([sev, count]) => ({
      severity: sev,
      count,
      pct: (count / max) * 100,
    }));
  }, [cves]);

  // Top vendors
  const topVendors = useMemo(() => {
    const map: Record<string, number> = {};
    cves.forEach((c) => { map[c.vendor] = (map[c.vendor] || 0) + 1; });
    return Object.entries(map)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 6);
  }, [cves]);

  return (
    <div className="threat-container">
      {/* Stats overview */}
      <div className="threat-stats">
        <div className="threat-stat-card">
          <div className="threat-stat-value">{stats.total}</div>
          <div className="threat-stat-label">Total CVEs</div>
        </div>
        <div className="threat-stat-card">
          <div className="threat-stat-value" style={{ color: SEVERITY_COLORS.critical }}>{stats.critical}</div>
          <div className="threat-stat-label">Critical</div>
        </div>
        <div className="threat-stat-card">
          <div className="threat-stat-value" style={{ color: SEVERITY_COLORS.high }}>{stats.high}</div>
          <div className="threat-stat-label">High</div>
        </div>
        <div className="threat-stat-card">
          <div className="threat-stat-value" style={{ color: "#ec4899" }}>{stats.exploited}</div>
          <div className="threat-stat-label">Exploited</div>
        </div>

        {/* Mini severity chart */}
        <div className="threat-mini-chart">
          <div className="threat-mini-chart-title">Severity Distribution</div>
          <div className="threat-mini-bars">
            {sevDist.map((d) => (
              <div key={d.severity} className="threat-mini-bar-wrap">
                <div className="threat-mini-bar-track">
                  <div
                    className="threat-mini-bar-fill"
                    style={{
                      width: `${d.pct}%`,
                      background: SEVERITY_COLORS[d.severity],
                    }}
                  />
                </div>
                <span className="threat-mini-bar-label">{d.severity.slice(0, 4)}</span>
                <span className="threat-mini-bar-count">{d.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Top vendors */}
        <div className="threat-top-vendors">
          <div className="threat-mini-chart-title">Top Affected Vendors</div>
          <div className="threat-vendor-list">
            {topVendors.map(([vendor, count]) => (
              <div key={vendor} className="threat-vendor-item">
                <span>{vendor}</span>
                <span className="threat-vendor-count">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="threat-filters">
        <input
          className="input threat-search"
          placeholder="Search CVE, vendor, product, tag..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="input threat-select"
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
        >
          <option value="all">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <label className="threat-exploit-toggle">
          <input
            type="checkbox"
            checked={exploitFilter}
            onChange={(e) => setExploitFilter(e.target.checked)}
          />
          <span>Exploit Available Only</span>
        </label>
        <span className="threat-result-count">{filtered.length} results</span>
      </div>

      {/* CVE list + Detail split */}
      <div className="threat-content">
        <div className="threat-list">
          {filtered.map((cve) => (
            <button
              key={cve.id}
              className={`threat-cve-card ${selectedCve?.id === cve.id ? "active" : ""}`}
              onClick={() => setSelectedCve(cve)}
            >
              <div className="threat-cve-top">
                <span className="threat-cve-id">{cve.cveId}</span>
                <span className={`badge badge-${cve.severity}`}>{cve.severity}</span>
              </div>
              <div className="threat-cve-title">{cve.title}</div>
              <div className="threat-cve-meta">
                <span>CVSS: {cve.cvss}</span>
                <span>{cve.publishedDate}</span>
                {cve.exploitAvailable && <span className="threat-exploit-badge">EXPLOIT</span>}
              </div>
              {cve.tags.length > 0 && (
                <div className="threat-cve-tags">
                  {cve.tags.map((tag) => (
                    <span key={tag} className="threat-tag">{tag}</span>
                  ))}
                </div>
              )}
            </button>
          ))}
        </div>

        {/* Detail panel */}
        <div className="threat-detail">
          {selectedCve ? (
            <div className="threat-detail-content">
              <div className="threat-detail-header">
                <div>
                  <span className="threat-cve-id" style={{ fontSize: "1rem" }}>{selectedCve.cveId}</span>
                  <h3 className="threat-detail-title">{selectedCve.title}</h3>
                </div>
                <span className={`badge badge-${selectedCve.severity}`} style={{ fontSize: "0.85rem", padding: "6px 14px" }}>
                  {selectedCve.severity.toUpperCase()}
                </span>
              </div>

              <div className="threat-detail-scores">
                <div className="threat-score-card">
                  <span className="threat-score-label">CVSS Score</span>
                  <span className="threat-score-value" style={{ color: SEVERITY_COLORS[selectedCve.severity] }}>
                    {selectedCve.cvss}
                  </span>
                </div>
                <div className="threat-score-card">
                  <span className="threat-score-label">Exploit</span>
                  <span className="threat-score-value" style={{ color: selectedCve.exploitAvailable ? "#ef4444" : "var(--text-muted)" }}>
                    {selectedCve.exploitAvailable ? "Available" : "None"}
                  </span>
                </div>
                <div className="threat-score-card">
                  <span className="threat-score-label">Published</span>
                  <span className="threat-score-value">{selectedCve.publishedDate}</span>
                </div>
              </div>

              <div className="threat-detail-section">
                <div className="threat-detail-section-title">Description</div>
                <p className="threat-detail-desc">{selectedCve.description}</p>
              </div>

              <div className="threat-detail-section">
                <div className="threat-detail-section-title">Affected Software</div>
                <div className="threat-detail-software">
                  <span className="threat-detail-vendor">{selectedCve.vendor}</span>
                  <span className="threat-detail-product">{selectedCve.product}</span>
                </div>
              </div>

              {selectedCve.tags.length > 0 && (
                <div className="threat-detail-section">
                  <div className="threat-detail-section-title">Tags</div>
                  <div className="threat-cve-tags">
                    {selectedCve.tags.map((tag) => (
                      <span key={tag} className="threat-tag threat-tag-lg">{tag}</span>
                    ))}
                  </div>
                </div>
              )}

              <div className="threat-detail-section">
                <div className="threat-detail-section-title">Recommendations</div>
                <div className="threat-recommendations">
                  <div className="threat-rec-item">
                    <span className="threat-rec-icon">1</span>
                    <span>Apply vendor patches immediately if available</span>
                  </div>
                  <div className="threat-rec-item">
                    <span className="threat-rec-icon">2</span>
                    <span>Monitor for indicators of compromise (IOCs)</span>
                  </div>
                  <div className="threat-rec-item">
                    <span className="threat-rec-icon">3</span>
                    <span>Implement network segmentation to limit exposure</span>
                  </div>
                  {selectedCve.exploitAvailable && (
                    <div className="threat-rec-item threat-rec-urgent">
                      <span className="threat-rec-icon">!</span>
                      <span>Active exploit detected — prioritize remediation</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="killchain-empty">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.3">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                <path d="M9 12l2 2 4-4"/>
              </svg>
              <p>Select a CVE from the list to view detailed threat intelligence.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
