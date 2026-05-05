// NEBULA AI — Red Team Copilot Terminal
// Retro-futuristic hacker terminal with streaming SSE, mode selection, and typing effects.

import { useEffect, useRef, useState } from "react";

type RedTeamMode = "recon" | "exploit" | "attack_chain" | "report" | "general";

type Message = {
  role: "user" | "assistant" | "system";
  content: string;
  mode?: RedTeamMode;
  timestamp: number;
};

const MODES: { id: RedTeamMode; label: string; icon: string; desc: string; color: string }[] = [
  { id: "recon", label: "RECON", icon: "🔍", desc: "OSINT & Passive Reconnaissance", color: "#22d3ee" },
  { id: "exploit", label: "EXPLOIT", icon: "⚡", desc: "Exploitation Vector Analysis", color: "#ef4444" },
  { id: "attack_chain", label: "ATTACK CHAIN", icon: "🔗", desc: "MITRE ATT&CK Kill Chains", color: "#f59e0b" },
  { id: "report", label: "REPORT", icon: "📄", desc: "Pentest Report Writing", color: "#10b981" },
  { id: "general", label: "GENERAL", icon: "🛡️", desc: "Senior Red Team Advice", color: "#a855f7" },
];

const QUICK_PROMPTS: Record<RedTeamMode, string[]> = {
  recon: [
    "Enumerate subdomains for target",
    "Find open ports and services",
    "OSINT techniques for email harvesting",
    "Certificate transparency logs analysis",
  ],
  exploit: [
    "Common web app attack vectors",
    "SQL injection payload examples",
    "Privilege escalation on Linux",
    "Post-exploitation persistence methods",
  ],
  attack_chain: [
    "Build a full kill chain for a web app",
    "APT-style attack chain with lateral movement",
    "Ransomware delivery chain",
    "Supply chain attack methodology",
  ],
  report: [
    "Executive summary template",
    "Write findings for SQL injection",
    "Risk rating methodology section",
    "Remediation recommendations template",
  ],
  general: [
    "Best practices for red team ops",
    "How to scope a pentest engagement",
    "Evasion techniques overview",
    "Red team vs pentest differences",
  ],
};

const API_BASE = "http://127.0.0.1:8000";

export function NebulaCopilot() {
  const [mode, setMode] = useState<RedTeamMode>("general");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "system",
      content: "SIRIUS AI // Red Team Copilot initialized.\nMode: GENERAL | Status: OPERATIONAL\n\nWelcome, operator. Select a mode and describe your target or question.\nAll operations assume authorized scope with signed ROE.",
      timestamp: Date.now(),
    },
  ]);
  const [input, setInput] = useState("");
  const [target, setTarget] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [showModePanel, setShowModePanel] = useState(false);
  const [showTargetInput, setShowTargetInput] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [isStreaming]);

  const currentMode = MODES.find((m) => m.id === mode)!;

  async function handleSend(text?: string) {
    const question = text || input.trim();
    if (!question || isStreaming) return;

    const userMsg: Message = { role: "user", content: question, mode, timestamp: Date.now() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);
    setStreamingText("");

    try {
      const history = messages
        .filter((m) => m.role !== "system")
        .slice(-10)
        .map((m) => ({ role: m.role, content: m.content }));

      const response = await fetch(`${API_BASE}/red-team/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode,
          question,
          target: target || null,
          context: null,
          history,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullText = "";

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6);
              if (data === "[DONE]") break;
              try {
                const parsed = JSON.parse(data);
                const token = parsed.choices?.[0]?.delta?.content || parsed.token || parsed.text || data;
                if (typeof token === "string") {
                  fullText += token;
                  setStreamingText(fullText);
                }
              } catch {
                // Plain text SSE
                fullText += data;
                setStreamingText(fullText);
              }
            }
          }
        }
      }

      if (!fullText) {
        fullText = generateFallbackResponse(mode, question);
      }

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: fullText, mode, timestamp: Date.now() },
      ]);
    } catch {
      // Fallback when backend isn't running
      const fallback = generateFallbackResponse(mode, question);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: fallback, mode, timestamp: Date.now() },
      ]);
    } finally {
      setIsStreaming(false);
      setStreamingText("");
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function clearChat() {
    setMessages([
      {
        role: "system",
        content: `SIRIUS AI // Session cleared.\nMode: ${currentMode.label} | Status: READY\n\nAwaiting new directives, operator.`,
        timestamp: Date.now(),
      },
    ]);
  }

  return (
    <div className="nebula-terminal">
      {/* Terminal header */}
      <div className="nebula-header">
        <div className="nebula-header-left">
          <div className="nebula-header-dots">
            <span className="dot-red" />
            <span className="dot-yellow" />
            <span className="dot-green" />
          </div>
          <span className="nebula-header-title">SIRIUS AI // {currentMode.label}</span>
        </div>
        <div className="nebula-header-right">
          <button
            className="nebula-header-btn"
            onClick={() => setShowTargetInput(!showTargetInput)}
            title="Set target"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
            </svg>
          </button>
          <button
            className="nebula-header-btn"
            onClick={() => setShowModePanel(!showModePanel)}
            title="Switch mode"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
              <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
            </svg>
          </button>
          <button className="nebula-header-btn" onClick={clearChat} title="Clear session">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>
      </div>

      {/* Target input bar */}
      {showTargetInput && (
        <div className="nebula-target-bar">
          <span className="nebula-target-label">TARGET:</span>
          <input
            className="nebula-target-input"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="e.g. example.com, 10.0.0.0/24, Corp Web App"
          />
        </div>
      )}

      {/* Mode selection panel */}
      {showModePanel && (
        <div className="nebula-mode-panel">
          {MODES.map((m) => (
            <button
              key={m.id}
              className={`nebula-mode-card ${mode === m.id ? "active" : ""}`}
              onClick={() => {
                setMode(m.id);
                setShowModePanel(false);
                setMessages((prev) => [
                  ...prev,
                  {
                    role: "system",
                    content: `Mode switched: ${m.label}\n${m.desc}`,
                    timestamp: Date.now(),
                  },
                ]);
              }}
              style={{ "--mode-color": m.color } as React.CSSProperties}
            >
              <span className="nebula-mode-icon">{m.icon}</span>
              <div>
                <div className="nebula-mode-name">{m.label}</div>
                <div className="nebula-mode-desc">{m.desc}</div>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Mode bar */}
      <div className="nebula-mode-bar">
        {MODES.map((m) => (
          <button
            key={m.id}
            className={`nebula-mode-tab ${mode === m.id ? "active" : ""}`}
            onClick={() => setMode(m.id)}
            style={{ "--mode-color": m.color } as React.CSSProperties}
          >
            <span className="nebula-mode-tab-dot" />
            {m.label}
          </button>
        ))}
      </div>

      {/* Messages area */}
      <div className="nebula-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`nebula-msg nebula-msg-${msg.role}`}>
            {msg.role === "system" && (
              <div className="nebula-msg-label">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
                SYSTEM
              </div>
            )}
            {msg.role === "user" && (
              <div className="nebula-msg-label nebula-msg-label-user">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
                </svg>
                OPERATOR
                {msg.mode && <span className="nebula-msg-mode">{msg.mode.toUpperCase()}</span>}
              </div>
            )}
            {msg.role === "assistant" && (
              <div className="nebula-msg-label nebula-msg-label-ai">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>
                </svg>
                NEBULA
              </div>
            )}
            <div className="nebula-msg-content">
              <pre>{msg.content}</pre>
            </div>
            <div className="nebula-msg-time">
              {new Date(msg.timestamp).toLocaleTimeString("en-US", { hour12: false })}
            </div>
          </div>
        ))}

        {/* Streaming indicator */}
        {isStreaming && (
          <div className="nebula-msg nebula-msg-assistant">
            <div className="nebula-msg-label nebula-msg-label-ai">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>
              </svg>
              NEBULA
              <span className="nebula-streaming-dot" />
            </div>
            <div className="nebula-msg-content">
              <pre>{streamingText || "Processing..."}</pre>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick prompts */}
      <div className="nebula-quick-prompts">
        {QUICK_PROMPTS[mode].map((prompt, i) => (
          <button
            key={i}
            className="nebula-quick-btn"
            onClick={() => handleSend(prompt)}
            disabled={isStreaming}
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input area */}
      <div className="nebula-input-area">
        <div className="nebula-input-prefix">
          <span style={{ color: currentMode.color }}>nebula</span>
          <span style={{ color: "var(--text-muted)" }}>:</span>
          <span style={{ color: "var(--purple-glow)" }}>{mode}</span>
          <span style={{ color: "var(--text-muted)" }}> $</span>
        </div>
        <textarea
          ref={inputRef}
          className="nebula-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter your directive..."
          disabled={isStreaming}
          rows={1}
        />
        <button
          className="nebula-send-btn"
          onClick={() => handleSend()}
          disabled={isStreaming || !input.trim()}
        >
          {isStreaming ? (
            <span className="nebula-spinner" />
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}

// Deterministic fallback when backend is not available
function generateFallbackResponse(mode: RedTeamMode, question: string): string {
  const q = question.toLowerCase();
  const responses: Record<RedTeamMode, string> = {
    recon: `## Reconnaissance Analysis

**Target Query:** ${question}

### Recommended OSINT Approach:
1. **Passive DNS** — Query historical DNS records via SecurityTrails, DNSDumpster
2. **Subdomain Enumeration** — Use tools: subfinder, amass, assetfinder
3. **Certificate Transparency** — Query crt.sh for SSL/TLS certificates
4. **Web Archive** — Check Wayback Machine for historical snapshots
5. **Search Engine Dorking** — Google/Shodan/Censys for exposed services

### Common Ports to Investigate:
- 80/443 (HTTP/HTTPS), 22 (SSH), 21 (FTP)
- 3306 (MySQL), 5432 (PostgreSQL), 27017 (MongoDB)
- 8080/8443 (Alt HTTP), 3389 (RDP)

### OSINT Tools:
\`theHarvester\`, \`recon-ng\`, \`maltego\`, \`spiderfoot\`

> ⚠️ All reconnaissance must be within authorized scope.`,

    exploit: `## Exploitation Vector Analysis

**Query:** ${question}

### Attack Surface Assessment:
${q.includes("sql") ? `**SQL Injection Vectors:**
- Classic: \`' OR 1=1--\`
- Union-based: \`' UNION SELECT null,null,table_name FROM information_schema.tables--\`
- Blind (Boolean): \`' AND 1=1--\` vs \`' AND 1=2--\`
- Time-based: \`' AND SLEEP(5)--\`
- Tools: sqlmap, Burp Suite, manual testing` :
q.includes("xss") ? `**XSS Vectors:**
- Reflected: \`<script>alert(1)</script>\`
- Stored: payload persistence in DB
- DOM-based: document.location manipulation
- Filter bypass: \`<img src=x onerror=alert(1)>\`
- Tools: XSStrike, Burp Suite, DalFox` :
`**General Exploitation Approach:**
1. Identify technology stack and version
2. Search for known CVEs (NVD, exploit-db)
3. Test authentication mechanisms
4. Check for misconfigurations
5. Attempt privilege escalation paths`}

### Post-Exploitation:
- Persistence mechanisms
- Lateral movement opportunities
- Data exfiltration paths
- Credential harvesting

> ⚠️ Only test systems you have explicit authorization to attack.`,

    attack_chain: `## MITRE ATT&CK Kill Chain

**Objective:** ${question}

### Stage 1: Reconnaissance (TA0043)
- T1595 — Active Scanning
- T1592 — Gather Victim Host Information
- **Tooling:** nmap, masscan, Shodan

### Stage 2: Resource Development (TA0042)
- T1583 — Acquire Infrastructure
- T1587 — Develop Capabilities
- **Tooling:** Custom C2, Cobalt Strike

### Stage 3: Initial Access (TA0001)
- T1566 — Phishing
- T1190 — Exploit Public-Facing Application
- **Tooling:** GoPhish, Metasploit

### Stage 4: Execution (TA0002)
- T1059 — Command and Scripting Interpreter
- T1204 — User Execution
- **Tooling:** PowerShell, Python

### Stage 5: Persistence (TA0003)
- T1053 — Scheduled Task/Job
- T1547 — Boot or Logon Autostart Execution

### Stage 6: Impact (TA0040)
- T1486 — Data Encrypted for Impact
- T1489 — Service Stop

> Each stage maps to MITRE ATT&CK framework for compliance reporting.`,

    report: `## Pentest Report Section

**Topic:** ${question}

---

### Finding: [Title]

**Severity:** High | **CVSS:** 7.5 | **Status:** Open

#### Description
A vulnerability was identified during testing that could allow an attacker to [describe impact]. This finding affects [scope/component].

#### Steps to Reproduce
1. Navigate to [URL/endpoint]
2. [Specific action]
3. Observe [result]

#### Evidence
\`\`\`
[Proof of concept output]
\`\`\`

#### Impact
- Confidentiality: [High/Medium/Low]
- Integrity: [High/Medium/Low]
- Availability: [High/Medium/Low]

#### Remediation
- **Short-term:** [Immediate fix]
- **Long-term:** [Architectural improvement]

#### References
- OWASP: [relevant category]
- CWE: [weakness ID]
- CVE: [if applicable]`,

    general: `## Red Team Advisory

**Query:** ${question}

### Analysis:
This is a common consideration in offensive security operations. Here's the structured approach:

**Planning Phase:**
- Define scope and rules of engagement (ROE)
- Identify critical assets and crown jewels
- Establish communication protocols
- Set up secure C2 infrastructure

**Execution Phase:**
- Start with passive reconnaissance
- Progress to active testing methodically
- Document every step for reproducibility
- Maintain operational security (OPSEC)

**Key Principles:**
1. Always operate within authorized scope
2. Minimize collateral impact
3. Prioritize stealth over speed
4. Document findings in real-time
5. Have rollback plans for every action

**Recommended Resources:**
- PTES (Penetration Testing Execution Standard)
- OWASP Testing Guide
- MITRE ATT&CK Framework
- NIST SP 800-115

> Remember: The goal is to improve security posture, not cause damage.`,
  };

  return responses[mode];
}
