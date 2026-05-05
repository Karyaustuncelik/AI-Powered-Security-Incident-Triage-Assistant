// Kill Chain Builder — Visual MITRE ATT&CK kill chain editor with technique cards.

import { useState } from "react";

type Technique = {
  id: string;
  name: string;
  tactic: string;
  description: string;
};

type ChainStep = {
  id: string;
  tactic: string;
  techniques: Technique[];
};

const TACTICS = [
  { id: "reconnaissance", name: "Reconnaissance", color: "#94a3b8", code: "TA0043" },
  { id: "resource_dev", name: "Resource Dev", color: "#a855f7", code: "TA0042" },
  { id: "initial_access", name: "Initial Access", color: "#ef4444", code: "TA0001" },
  { id: "execution", name: "Execution", color: "#f59e0b", code: "TA0002" },
  { id: "persistence", name: "Persistence", color: "#ec4899", code: "TA0003" },
  { id: "priv_escalation", name: "Priv Escalation", color: "#f97316", code: "TA0004" },
  { id: "defense_evasion", name: "Defense Evasion", color: "#14b8a6", code: "TA0005" },
  { id: "credential_access", name: "Credential Access", color: "#8b5cf6", code: "TA0006" },
  { id: "discovery", name: "Discovery", color: "#3b82f6", code: "TA0007" },
  { id: "lateral_movement", name: "Lateral Movement", color: "#06b6d4", code: "TA0008" },
  { id: "collection", name: "Collection", color: "#10b981", code: "TA0009" },
  { id: "exfiltration", name: "Exfiltration", color: "#22d3ee", code: "TA0010" },
  { id: "impact", name: "Impact", color: "#ef4444", code: "TA0040" },
];

const TECHNIQUES_DB: Record<string, Technique[]> = {
  reconnaissance: [
    { id: "T1595", name: "Active Scanning", tactic: "reconnaissance", description: "Scan target infrastructure for vulnerabilities" },
    { id: "T1592", name: "Gather Victim Host Info", tactic: "reconnaissance", description: "Collect information about victim hosts" },
    { id: "T1589", name: "Gather Victim Identity", tactic: "reconnaissance", description: "Gather identity information about the victim" },
    { id: "T1590", name: "Gather Victim Network Info", tactic: "reconnaissance", description: "Collect information about victim networks" },
    { id: "T1591", name: "Gather Victim Org Info", tactic: "reconnaissance", description: "Research target organization structure" },
    { id: "T1598", name: "Phishing for Information", tactic: "reconnaissance", description: "Send phishing messages to gather info" },
  ],
  resource_dev: [
    { id: "T1583", name: "Acquire Infrastructure", tactic: "resource_dev", description: "Purchase or rent infrastructure for operations" },
    { id: "T1587", name: "Develop Capabilities", tactic: "resource_dev", description: "Build or acquire custom tools and malware" },
    { id: "T1584", name: "Compromise Infrastructure", tactic: "resource_dev", description: "Compromise third-party infrastructure" },
    { id: "T1585", name: "Establish Accounts", tactic: "resource_dev", description: "Create accounts for use in operations" },
  ],
  initial_access: [
    { id: "T1566", name: "Phishing", tactic: "initial_access", description: "Send phishing messages with malicious attachments" },
    { id: "T1190", name: "Exploit Public-Facing App", tactic: "initial_access", description: "Exploit vulnerabilities in internet-facing applications" },
    { id: "T1133", name: "External Remote Services", tactic: "initial_access", description: "Leverage external-facing remote services (VPN, RDP)" },
    { id: "T1199", name: "Trusted Relationship", tactic: "initial_access", description: "Abuse trusted third-party relationships" },
    { id: "T1078", name: "Valid Accounts", tactic: "initial_access", description: "Use valid credentials for initial access" },
    { id: "T1195", name: "Supply Chain Compromise", tactic: "initial_access", description: "Manipulate products or mechanisms prior to delivery" },
  ],
  execution: [
    { id: "T1059", name: "Command & Scripting", tactic: "execution", description: "Abuse command and script interpreters" },
    { id: "T1204", name: "User Execution", tactic: "execution", description: "Rely on user interaction for execution" },
    { id: "T1203", name: "Exploitation for Client Exec", tactic: "execution", description: "Exploit client application vulnerabilities" },
    { id: "T1053", name: "Scheduled Task/Job", tactic: "execution", description: "Abuse task scheduling for execution" },
  ],
  persistence: [
    { id: "T1547", name: "Boot/Logon Autostart", tactic: "persistence", description: "Configure to execute during system boot" },
    { id: "T1136", name: "Create Account", tactic: "persistence", description: "Create new accounts for persistent access" },
    { id: "T1543", name: "Create/Modify System Process", tactic: "persistence", description: "Create or modify system-level processes" },
    { id: "T1546", name: "Event Triggered Execution", tactic: "persistence", description: "Use event-triggered execution mechanisms" },
  ],
  priv_escalation: [
    { id: "T1548", name: "Abuse Elevation Control", tactic: "priv_escalation", description: "Bypass elevation control mechanisms" },
    { id: "T1134", name: "Access Token Manipulation", tactic: "priv_escalation", description: "Manipulate access tokens" },
    { id: "T1068", name: "Exploitation for Priv Esc", tactic: "priv_escalation", description: "Exploit vulnerabilities for privilege escalation" },
  ],
  defense_evasion: [
    { id: "T1070", name: "Indicator Removal", tactic: "defense_evasion", description: "Remove indicators of compromise" },
    { id: "T1036", name: "Masquerading", tactic: "defense_evasion", description: "Manipulate features to appear legitimate" },
    { id: "T1027", name: "Obfuscated Files", tactic: "defense_evasion", description: "Encrypt or obfuscate malicious content" },
    { id: "T1562", name: "Impair Defenses", tactic: "defense_evasion", description: "Disable or modify security tools" },
  ],
  credential_access: [
    { id: "T1110", name: "Brute Force", tactic: "credential_access", description: "Use brute force to access accounts" },
    { id: "T1003", name: "OS Credential Dumping", tactic: "credential_access", description: "Dump credentials from operating system" },
    { id: "T1558", name: "Steal/Forge Kerberos Tix", tactic: "credential_access", description: "Steal or forge Kerberos tickets" },
  ],
  discovery: [
    { id: "T1087", name: "Account Discovery", tactic: "discovery", description: "Enumerate system and domain accounts" },
    { id: "T1046", name: "Network Service Discovery", tactic: "discovery", description: "Scan for running network services" },
    { id: "T1057", name: "Process Discovery", tactic: "discovery", description: "List running processes on a system" },
  ],
  lateral_movement: [
    { id: "T1021", name: "Remote Services", tactic: "lateral_movement", description: "Use remote services to move laterally" },
    { id: "T1570", name: "Lateral Tool Transfer", tactic: "lateral_movement", description: "Transfer tools between systems" },
    { id: "T1550", name: "Use Alternate Auth Material", tactic: "lateral_movement", description: "Use stolen authentication material" },
  ],
  collection: [
    { id: "T1560", name: "Archive Collected Data", tactic: "collection", description: "Archive collected data for exfiltration" },
    { id: "T1005", name: "Data from Local System", tactic: "collection", description: "Collect data from the local system" },
    { id: "T1114", name: "Email Collection", tactic: "collection", description: "Collect data from email sources" },
  ],
  exfiltration: [
    { id: "T1041", name: "Exfil Over C2 Channel", tactic: "exfiltration", description: "Exfiltrate data over the C2 channel" },
    { id: "T1567", name: "Exfil Over Web Service", tactic: "exfiltration", description: "Exfiltrate data to cloud storage" },
    { id: "T1048", name: "Exfil Over Alternative Protocol", tactic: "exfiltration", description: "Use non-standard protocols for exfiltration" },
  ],
  impact: [
    { id: "T1486", name: "Data Encrypted for Impact", tactic: "impact", description: "Encrypt data on target systems" },
    { id: "T1489", name: "Service Stop", tactic: "impact", description: "Stop or disable services" },
    { id: "T1529", name: "System Shutdown/Reboot", tactic: "impact", description: "Shutdown or reboot target systems" },
  ],
};

export function KillChainBuilder() {
  const [chain, setChain] = useState<ChainStep[]>([]);
  const [selectedTactic, setSelectedTactic] = useState<string | null>(null);
  const [chainName, setChainName] = useState("Untitled Kill Chain");

  function addTechniqueToChain(technique: Technique) {
    setChain((prev) => {
      const existing = prev.find((s) => s.tactic === technique.tactic);
      if (existing) {
        if (existing.techniques.some((t) => t.id === technique.id)) return prev;
        return prev.map((s) =>
          s.tactic === technique.tactic
            ? { ...s, techniques: [...s.techniques, technique] }
            : s
        );
      }
      return [...prev, { id: Math.random().toString(36).slice(2), tactic: technique.tactic, techniques: [technique] }];
    });
  }

  function removeTechnique(tacticId: string, techId: string) {
    setChain((prev) => {
      const updated = prev.map((s) => {
        if (s.tactic !== tacticId) return s;
        return { ...s, techniques: s.techniques.filter((t) => t.id !== techId) };
      }).filter((s) => s.techniques.length > 0);
      return updated;
    });
  }

  function clearChain() {
    setChain([]);
  }

  // Sort chain by MITRE tactic order
  const sortedChain = [...chain].sort((a, b) => {
    const aIdx = TACTICS.findIndex((t) => t.id === a.tactic);
    const bIdx = TACTICS.findIndex((t) => t.id === b.tactic);
    return aIdx - bIdx;
  });

  const tacticInfo = selectedTactic ? TACTICS.find((t) => t.id === selectedTactic) : null;
  const techniques = selectedTactic ? TECHNIQUES_DB[selectedTactic] || [] : [];

  return (
    <div className="killchain-container">
      {/* Chain header */}
      <div className="killchain-header">
        <div className="killchain-header-left">
          <input
            className="killchain-name-input"
            value={chainName}
            onChange={(e) => setChainName(e.target.value)}
            placeholder="Kill Chain Name"
          />
          <span className="killchain-badge">{sortedChain.length} Tactics</span>
          <span className="killchain-badge">
            {sortedChain.reduce((acc, s) => acc + s.techniques.length, 0)} Techniques
          </span>
        </div>
        <div className="killchain-header-right">
          <button className="btn" onClick={clearChain}>Clear Chain</button>
        </div>
      </div>

      {/* Kill chain visualization */}
      {sortedChain.length > 0 && (
        <div className="killchain-visual">
          <div className="killchain-flow">
            {sortedChain.map((step, i) => {
              const tactic = TACTICS.find((t) => t.id === step.tactic);
              if (!tactic) return null;
              return (
                <div key={step.id} className="killchain-flow-step">
                  {i > 0 && (
                    <div className="killchain-flow-arrow">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
                        <path d="M5 12h14M12 5l7 7-7 7"/>
                      </svg>
                    </div>
                  )}
                  <div className="killchain-flow-card" style={{ borderColor: tactic.color + "40" }}>
                    <div className="killchain-flow-tactic" style={{ color: tactic.color }}>
                      {tactic.name}
                    </div>
                    <div className="killchain-flow-code">{tactic.code}</div>
                    <div className="killchain-flow-techs">
                      {step.techniques.map((tech) => (
                        <div key={tech.id} className="killchain-flow-tech">
                          <span className="killchain-flow-tech-id">{tech.id}</span>
                          <span>{tech.name}</span>
                          <button
                            className="killchain-flow-tech-remove"
                            onClick={() => removeTechnique(step.tactic, tech.id)}
                            title="Remove"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Editor */}
      <div className="killchain-editor">
        {/* Tactics list */}
        <div className="killchain-tactics">
          <div className="killchain-section-title">MITRE ATT&CK Tactics</div>
          <div className="killchain-tactics-list">
            {TACTICS.map((tactic) => {
              const inChain = chain.some((s) => s.tactic === tactic.id);
              return (
                <button
                  key={tactic.id}
                  className={`killchain-tactic-btn ${selectedTactic === tactic.id ? "active" : ""} ${inChain ? "in-chain" : ""}`}
                  onClick={() => setSelectedTactic(selectedTactic === tactic.id ? null : tactic.id)}
                  style={{ "--tactic-color": tactic.color } as React.CSSProperties}
                >
                  <span className="killchain-tactic-dot" />
                  <div className="killchain-tactic-info">
                    <span className="killchain-tactic-name">{tactic.name}</span>
                    <span className="killchain-tactic-code">{tactic.code}</span>
                  </div>
                  {inChain && <span className="killchain-tactic-check">✓</span>}
                </button>
              );
            })}
          </div>
        </div>

        {/* Techniques panel */}
        <div className="killchain-techniques">
          {selectedTactic && tacticInfo ? (
            <>
              <div className="killchain-section-title" style={{ color: tacticInfo.color }}>
                {tacticInfo.name} — Techniques
              </div>
              <div className="killchain-techniques-grid">
                {techniques.map((tech) => {
                  const isAdded = chain.some((s) =>
                    s.tactic === tech.tactic && s.techniques.some((t) => t.id === tech.id)
                  );
                  return (
                    <button
                      key={tech.id}
                      className={`killchain-tech-card ${isAdded ? "added" : ""}`}
                      onClick={() => !isAdded && addTechniqueToChain(tech)}
                      disabled={isAdded}
                      style={{ "--tactic-color": tacticInfo.color } as React.CSSProperties}
                    >
                      <div className="killchain-tech-header">
                        <span className="killchain-tech-id">{tech.id}</span>
                        {isAdded && <span className="killchain-tech-added-badge">Added</span>}
                      </div>
                      <div className="killchain-tech-name">{tech.name}</div>
                      <div className="killchain-tech-desc">{tech.description}</div>
                    </button>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="killchain-empty">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.3">
                <polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>
              </svg>
              <p>Select a tactic from the left panel to browse and add techniques to your kill chain.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
