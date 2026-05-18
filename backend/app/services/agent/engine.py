"""ReAct-pattern AI Security Agent engine.

Implements an autonomous agent loop:
  Thought → Action (tool call) → Observation → Thought → ... → Final Answer

Supports three execution modes:
  1. LLM-powered (OpenAI-compatible with function calling)
  2. Deterministic fallback (always works, zero config)

Results are streamed as SSE events with types:
  - thought: Agent's reasoning text
  - tool_call: Which tool the agent decided to use and why
  - tool_result: Output from the tool execution
  - finding: A structured security finding
  - summary: Final assessment summary
  - progress: Step counter update
  - error: Error encountered
  - done: Stream complete
"""

from __future__ import annotations

import json
import time
import traceback
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from urllib import error, request

from app.core.config import get_settings
from app.services.agent.tools import TOOL_REGISTRY, SecurityTool


# ── SSE helpers ───────────────────────────────────────────────────────────────

def _sse(event_type: str, data: dict) -> str:
    payload = {"type": event_type, **data}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class AgentStep:
    step: int
    thought: str
    tool_name: str | None = None
    tool_params: dict | None = None
    observation: str | None = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()


@dataclass
class SecurityFinding:
    title: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str  # header, ssl, path, cve, tech, dns, etc.
    description: str
    recommendation: str
    evidence: str = ""


@dataclass
class AgentResult:
    target: str
    steps: list[AgentStep] = field(default_factory=list)
    findings: list[SecurityFinding] = field(default_factory=list)
    summary: str = ""
    overall_risk: str = "UNKNOWN"
    duration_seconds: float = 0.0


# ── Deterministic fallback agent ──────────────────────────────────────────────

def _fallback_agent_stream(target: str, goal: str | None) -> Iterator[str]:
    """Run tools in a fixed order without an LLM and produce structured results."""
    start = time.time()
    steps: list[AgentStep] = []
    findings: list[SecurityFinding] = []
    step_num = 0

    tool_plan = [
        ("http_probe", {"url": target}, "Probing HTTP endpoint for status, headers, and technologies"),
        ("header_analysis", {"url": target}, "Analyzing security headers against OWASP standards"),
        ("dns_lookup", {"domain": target}, "Resolving DNS records and checking configuration"),
        ("ssl_check", {"host": target}, "Inspecting TLS certificate and cipher configuration"),
        ("subdomain_enum", {"domain": target}, "Enumerating subdomains via Certificate Transparency"),
        ("path_discovery", {"url": target}, "Probing common paths for sensitive endpoints"),
        ("whois_lookup", {"domain": target}, "Looking up domain registration details"),
    ]

    total_steps = len(tool_plan)

    for tool_name, params, thought_text in tool_plan:
        step_num += 1
        yield _sse("progress", {"step": step_num, "total": total_steps})
        yield _sse("thought", {"content": f"**Step {step_num}/{total_steps}:** {thought_text}"})

        tool = TOOL_REGISTRY.get(tool_name)
        if not tool:
            continue

        yield _sse("tool_call", {
            "tool": tool_name,
            "params": params,
            "description": tool.description,
        })

        try:
            observation = tool.func(params)
            obs_data = json.loads(observation)
        except Exception as e:
            observation = json.dumps({"error": str(e)[:200]})
            obs_data = {"error": str(e)[:200]}

        yield _sse("tool_result", {
            "tool": tool_name,
            "result": obs_data,
        })

        step = AgentStep(
            step=step_num,
            thought=thought_text,
            tool_name=tool_name,
            tool_params=params,
            observation=observation,
        )
        steps.append(step)

        # Extract findings from tool results
        tool_findings = _extract_findings(tool_name, obs_data)
        for f in tool_findings:
            findings.append(f)
            yield _sse("finding", {
                "title": f.title,
                "severity": f.severity,
                "category": f.category,
                "description": f.description,
                "recommendation": f.recommendation,
                "evidence": f.evidence,
            })

    # Build summary
    duration = time.time() - start
    crit_count = sum(1 for f in findings if f.severity == "CRITICAL")
    high_count = sum(1 for f in findings if f.severity == "HIGH")
    med_count = sum(1 for f in findings if f.severity == "MEDIUM")
    low_count = sum(1 for f in findings if f.severity in ("LOW", "INFO"))

    if crit_count > 0:
        risk = "CRITICAL"
    elif high_count >= 2:
        risk = "HIGH"
    elif high_count > 0 or med_count >= 3:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    summary_text = (
        f"## Security Assessment Summary\n\n"
        f"**Target:** {target}\n"
        f"**Overall Risk:** {risk}\n"
        f"**Duration:** {duration:.1f}s\n"
        f"**Findings:** {len(findings)} total "
        f"({crit_count} Critical, {high_count} High, {med_count} Medium, {low_count} Low/Info)\n\n"
        f"### Key Findings\n\n"
    )
    for f in findings:
        icon = {"CRITICAL": "☢", "HIGH": "⚠", "MEDIUM": "⚡", "LOW": "ℹ", "INFO": "ℹ"}.get(f.severity, "•")
        summary_text += f"- {icon} **[{f.severity}]** {f.title}\n"

    summary_text += (
        f"\n### Recommendations\n\n"
        f"1. Address all CRITICAL and HIGH findings immediately\n"
        f"2. Implement missing security headers (CSP, HSTS, X-Frame-Options)\n"
        f"3. Remove or restrict access to sensitive exposed paths\n"
        f"4. Update vulnerable software components to latest versions\n"
        f"5. Schedule follow-up assessment after remediation\n"
    )

    yield _sse("summary", {
        "content": summary_text,
        "risk_level": risk,
        "finding_counts": {
            "critical": crit_count,
            "high": high_count,
            "medium": med_count,
            "low": low_count,
        },
        "duration": round(duration, 1),
    })

    yield _sse("done", {})


def _extract_findings(tool_name: str, data: dict) -> list[SecurityFinding]:
    """Extract structured security findings from a tool's output."""
    findings: list[SecurityFinding] = []

    if tool_name == "header_analysis":
        for item in data.get("findings", []):
            findings.append(SecurityFinding(
                title=item.get("finding", "Header issue")[:80],
                severity=item.get("severity", "MEDIUM"),
                category="header",
                description=item.get("finding", ""),
                recommendation="Implement the missing header per OWASP Secure Headers guidelines.",
                evidence=f"Grade: {data.get('grade', 'N/A')} | Score: {data.get('security_score', 'N/A')}/100",
            ))

    elif tool_name == "http_probe":
        headers = data.get("security_headers", {})
        missing = [k for k, v in headers.items() if v == "MISSING"]
        if len(missing) >= 3:
            findings.append(SecurityFinding(
                title=f"{len(missing)} security headers missing",
                severity="HIGH",
                category="header",
                description=f"Missing headers: {', '.join(missing)}",
                recommendation="Add all recommended security headers to HTTP responses.",
            ))
        techs = data.get("detected_technologies", [])
        if techs:
            findings.append(SecurityFinding(
                title=f"Technology fingerprint: {', '.join(techs[:5])}",
                severity="INFO",
                category="tech",
                description=f"Detected technologies: {', '.join(techs)}. Each should be checked for known vulnerabilities.",
                recommendation="Search CVE databases for each detected technology version.",
            ))
        if data.get("form_count", 0) > 0:
            findings.append(SecurityFinding(
                title=f"{data['form_count']} form(s) detected — potential injection surface",
                severity="MEDIUM",
                category="input",
                description=f"Found {data['form_count']} HTML forms with {data.get('input_field_count', 0)} input fields. These are potential vectors for XSS, SQLi, and CSRF.",
                recommendation="Test all form inputs for injection vulnerabilities. Ensure CSRF tokens are present.",
            ))

    elif tool_name == "ssl_check":
        if data.get("error"):
            findings.append(SecurityFinding(
                title="TLS/SSL connection failed",
                severity="CRITICAL",
                category="ssl",
                description=f"Could not establish TLS connection: {data['error']}",
                recommendation="Verify SSL certificate is properly configured and not expired.",
            ))
        if data.get("expiry_warning"):
            findings.append(SecurityFinding(
                title=f"SSL certificate expiring in {data.get('days_until_expiry', '?')} days",
                severity="HIGH",
                category="ssl",
                description="Certificate is near expiry. Failure to renew will cause browser trust warnings.",
                recommendation="Renew the TLS certificate immediately. Consider automated renewal via Let's Encrypt.",
            ))
        for warn in data.get("security_warnings", []):
            findings.append(SecurityFinding(
                title=warn,
                severity="HIGH",
                category="ssl",
                description=warn,
                recommendation="Upgrade TLS configuration to use TLSv1.2+ with strong cipher suites.",
            ))

    elif tool_name == "path_discovery":
        summary = data.get("summary", {})
        for path in summary.get("sensitive_findings", []):
            findings.append(SecurityFinding(
                title=f"Sensitive path accessible: {path}",
                severity="CRITICAL" if path in ("/.env", "/.git/HEAD") else "HIGH",
                category="path",
                description=f"The path {path} is publicly accessible and may expose sensitive data or configuration.",
                recommendation=f"Immediately restrict access to {path}. Configure web server to deny access to sensitive files.",
                evidence=f"HTTP 200 on {data.get('base_url', '')}{path}",
            ))
        accessible = summary.get("accessible_paths", [])
        non_sensitive = [p for p in accessible if p not in summary.get("sensitive_findings", [])]
        if non_sensitive:
            findings.append(SecurityFinding(
                title=f"{len(non_sensitive)} additional paths accessible",
                severity="LOW",
                category="path",
                description=f"Accessible paths: {', '.join(non_sensitive[:10])}",
                recommendation="Review each accessible path and restrict if not intentionally public.",
            ))

    elif tool_name == "subdomain_enum":
        count = data.get("unique_subdomains", 0)
        if count > 20:
            findings.append(SecurityFinding(
                title=f"Large subdomain footprint: {count} subdomains",
                severity="MEDIUM",
                category="dns",
                description=f"Found {count} unique subdomains via Certificate Transparency. Large surface area increases attack vectors.",
                recommendation="Review all subdomains. Decommission unused ones. Ensure each has proper security controls.",
                evidence=f"Sample: {', '.join(data.get('subdomains', [])[:5])}",
            ))
        elif count > 0:
            findings.append(SecurityFinding(
                title=f"Subdomain enumeration: {count} found",
                severity="INFO",
                category="dns",
                description=f"Subdomains: {', '.join(data.get('subdomains', [])[:10])}",
                recommendation="Verify all subdomains are intended to be public.",
            ))

    elif tool_name == "cve_search":
        for cve in data.get("cves", []):
            sev = (cve.get("severity") or "MEDIUM").upper()
            score = cve.get("cvss_score")
            findings.append(SecurityFinding(
                title=f"{cve['cve_id']} (CVSS {score or '?'})",
                severity=sev,
                category="cve",
                description=cve.get("description", "")[:200],
                recommendation=f"Check if the target is affected by {cve['cve_id']} and apply patches.",
                evidence=f"Published: {cve.get('published', 'N/A')}",
            ))

    return findings


# ── LLM-powered agent (OpenAI function calling) ──────────────────────────────

def _llm_agent_stream(target: str, goal: str | None, settings: object) -> Iterator[str]:
    """Run the agent with real LLM reasoning and function calling."""
    start = time.time()
    tool_schemas = [t.as_schema() for t in TOOL_REGISTRY.values()]

    system_prompt = (
        "You are SIRIUS, an expert AI security agent performing an automated security assessment. "
        "You have access to real security tools that make actual network requests. "
        "Your task is to methodically assess the target's security posture.\n\n"
        "APPROACH:\n"
        "1. Start with passive reconnaissance (DNS, WHOIS, SSL)\n"
        "2. Probe the HTTP endpoint (headers, technologies)\n"
        "3. Enumerate subdomains and paths\n"
        "4. Search for known CVEs based on detected technologies\n"
        "5. Compile a comprehensive assessment\n\n"
        "RULES:\n"
        "- Call tools one at a time, analyze each result before deciding the next step\n"
        "- Be thorough — use at least 5 different tools\n"
        "- After gathering enough data, provide your final assessment\n"
        "- Classify each finding as CRITICAL, HIGH, MEDIUM, LOW, or INFO\n"
        "- Always provide specific, actionable recommendations\n"
    )

    user_msg = f"Assess the security of: {target}"
    if goal:
        user_msg += f"\nSpecific goal: {goal}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    max_iterations = 10
    step_num = 0
    all_findings: list[SecurityFinding] = []

    for iteration in range(max_iterations):
        step_num += 1
        yield _sse("progress", {"step": step_num, "total": max_iterations})

        # Call LLM
        body: dict = {
            "messages": messages,
            "tools": tool_schemas,
            "tool_choice": "auto",
            "temperature": 0.1,
        }
        if hasattr(settings, "llm_model") and settings.llm_model:
            body["model"] = settings.llm_model

        try:
            resp = _post_llm(body, settings)
        except Exception as e:
            yield _sse("error", {"content": f"LLM call failed: {e}"})
            break

        choice = resp.get("choices", [{}])[0]
        message = choice.get("message", {})
        finish_reason = choice.get("finish_reason", "")

        # If the model wants to call a tool
        tool_calls = message.get("tool_calls", [])
        if tool_calls:
            # Stream the assistant's content (thought) if present
            if message.get("content"):
                yield _sse("thought", {"content": message["content"]})

            messages.append(message)

            for tc in tool_calls:
                fn = tc.get("function", {})
                tool_name = fn.get("name", "")
                try:
                    tool_params = json.loads(fn.get("arguments", "{}"))
                except json.JSONDecodeError:
                    tool_params = {}

                yield _sse("tool_call", {
                    "tool": tool_name,
                    "params": tool_params,
                    "description": TOOL_REGISTRY.get(tool_name, SecurityTool(name="", description="unknown tool", parameters={}, func=lambda p: "{}")).description,
                })

                # Execute tool
                tool = TOOL_REGISTRY.get(tool_name)
                if tool:
                    try:
                        observation = tool.func(tool_params)
                        obs_data = json.loads(observation)
                    except Exception as e:
                        observation = json.dumps({"error": str(e)[:200]})
                        obs_data = {"error": str(e)[:200]}
                else:
                    observation = json.dumps({"error": f"Unknown tool: {tool_name}"})
                    obs_data = {"error": f"Unknown tool: {tool_name}"}

                yield _sse("tool_result", {"tool": tool_name, "result": obs_data})

                # Extract findings
                tool_findings = _extract_findings(tool_name, obs_data)
                for f in tool_findings:
                    all_findings.append(f)
                    yield _sse("finding", {
                        "title": f.title,
                        "severity": f.severity,
                        "category": f.category,
                        "description": f.description,
                        "recommendation": f.recommendation,
                        "evidence": f.evidence,
                    })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": observation[:3000],
                })

        elif message.get("content"):
            # Final answer — no more tool calls
            yield _sse("thought", {"content": message["content"]})

            duration = time.time() - start
            crit = sum(1 for f in all_findings if f.severity == "CRITICAL")
            high = sum(1 for f in all_findings if f.severity == "HIGH")
            med = sum(1 for f in all_findings if f.severity == "MEDIUM")
            low = sum(1 for f in all_findings if f.severity in ("LOW", "INFO"))
            risk = "CRITICAL" if crit > 0 else "HIGH" if high >= 2 else "MEDIUM" if high > 0 or med >= 3 else "LOW"

            yield _sse("summary", {
                "content": message["content"],
                "risk_level": risk,
                "finding_counts": {"critical": crit, "high": high, "medium": med, "low": low},
                "duration": round(duration, 1),
            })
            break

        if finish_reason == "stop" and not tool_calls:
            break

    yield _sse("done", {})


def _post_llm(body: dict, settings: object) -> dict:
    api_url = getattr(settings, "llm_api_url", "")
    api_key = getattr(settings, "llm_api_key", "")
    provider = getattr(settings, "llm_provider", "mock")
    timeout = getattr(settings, "llm_timeout_seconds", 30)

    auth_header = "api-key" if provider == "azure_openai" else "Authorization"
    auth_value = api_key if provider == "azure_openai" else f"Bearer {api_key}"

    payload = json.dumps(body).encode("utf-8")
    req = request.Request(
        api_url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            auth_header: auth_value,
        },
    )
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── Service facade ────────────────────────────────────────────────────────────

class SecurityAgent:
    def __init__(self) -> None:
        self._settings = get_settings()

    def run(self, target: str, goal: str | None = None) -> Iterator[str]:
        """Run an autonomous security assessment, yielding SSE frames."""
        has_llm = (
            self._settings.llm_provider in ("openai_compatible", "azure_openai")
            and self._settings.llm_api_url
            and self._settings.llm_api_key
        )
        if has_llm:
            try:
                yield from _llm_agent_stream(target, goal, self._settings)
                return
            except Exception:
                # Fall through to deterministic agent
                pass

        yield from _fallback_agent_stream(target, goal)


@lru_cache
def get_security_agent() -> SecurityAgent:
    return SecurityAgent()
