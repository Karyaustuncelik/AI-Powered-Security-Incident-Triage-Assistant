# Streaming red team copilot service.
#
# Yields chunks compatible with Server-Sent Events (SSE).
# Supports three modes of providers:
#   - OpenAI-compatible streaming (primary)
#   - Azure OpenAI streaming (reuses OpenAI wire format)
#   - Local template fallback (always works, zero-config)
#
# The backend never asks the LLM to decide ethics — the system prompt in
# red_team_prompt_builder.py defines the guardrails. If the LLM provider is
# unavailable, we stream a useful templated answer so the UI never stalls.

import json
from collections.abc import Iterator
from functools import lru_cache
from urllib import error, request

from app.core.config import get_settings
from app.models.red_team import (
    AttackChainResponse,
    AttackChainStep,
    MitreTechnique,
    RedTeamStreamRequest,
)
from app.services.red_team_prompt_builder import build_red_team_messages


# ---------------------------------------------------------------------------
# Streaming primitives
# ---------------------------------------------------------------------------


def _sse_data(payload: dict) -> str:
    """Format a Server-Sent Events `data:` frame."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _fallback_stream(payload: RedTeamStreamRequest) -> Iterator[str]:
    """Deterministic, provider-free stream so the UI always works."""
    intro = _template_intro(payload)
    body = _template_body(payload)
    outro = "\n\n_(Template fallback — connect a real LLM in `.env` to stream live responses.)_"
    for chunk in _fake_chunks(intro + body + outro):
        yield _sse_data({"type": "delta", "content": chunk})
    yield _sse_data({"type": "done"})


def _fake_chunks(text: str, size: int = 24) -> Iterator[str]:
    """Split text into small chunks so the template feels like streaming."""
    for i in range(0, len(text), size):
        yield text[i : i + size]


def _template_intro(payload: RedTeamStreamRequest) -> str:
    target_line = f" against `{payload.target}`" if payload.target else ""
    return f"**NEBULA · {payload.mode.upper()} MODE**{target_line}\n\n"


def _template_body(payload: RedTeamStreamRequest) -> str:
    mode = payload.mode
    if mode == "recon":
        return (
            "### Passive sources\n"
            "- crt.sh certificate transparency sweep\n"
            "- Shodan / Censys banner pivot\n"
            "- GitHub dorking for leaked secrets\n\n"
            "### Likely attack surface\n"
            "- Web front (80/443)\n"
            "- Remote access (22/3389)\n"
            "- SMB / RDP on internal ranges\n\n"
            "### Quick wins\n"
            "- Default credentials on admin portals\n"
            "- Outdated CMS plugins\n"
            "- Exposed `.git` / `.env` files"
        )
    if mode == "exploit":
        return (
            "### Likely vectors\n"
            "- Input injection surfaces (SQLi, SSTI, command injection)\n"
            "- Auth weaknesses (JWT `none`, missing sig verification)\n"
            "- Deserialization / prototype pollution\n\n"
            "### PoC skeleton\n"
            "```bash\n"
            "# Replace <TARGET> and <PAYLOAD> with scoped values\n"
            "curl -sS '<TARGET>' --data '<PAYLOAD>'\n"
            "```\n\n"
            "⚠️ WARNING: always confirm scope before firing."
        )
    if mode == "attack_chain":
        return (
            "STAGE 1 · Reconnaissance\n"
            "Goal: enumerate external surface.\n"
            "Tooling: amass, subfinder, httpx\n"
            "MITRE: T1595, T1590\n---\n"
            "STAGE 2 · Initial Access\n"
            "Goal: gain first foothold.\n"
            "Tooling: gophish, evilginx, metasploit\n"
            "MITRE: T1566.001, T1190\n---\n"
            "STAGE 3 · Execution\n"
            "Goal: run operator code.\n"
            "Tooling: powershell, python, sliver\n"
            "MITRE: T1059.001\n---\n"
            "STAGE 4 · Privilege Escalation\n"
            "Goal: become SYSTEM/root.\n"
            "Tooling: winpeas, linpeas, bloodhound\n"
            "MITRE: T1068\n---\n"
            "STAGE 5 · Lateral Movement\n"
            "Goal: pivot to high-value asset.\n"
            "Tooling: impacket, crackmapexec\n"
            "MITRE: T1021.002\n---\n"
            "STAGE 6 · Exfiltration\n"
            "Goal: stage proof of compromise.\n"
            "Tooling: rclone, custom channel\n"
            "MITRE: T1041"
        )
    if mode == "report":
        return (
            "# Executive Summary\n"
            "During the engagement, the team identified a critical finding "
            "that allows unauthenticated access to sensitive data.\n\n"
            "# Risk Rating\n"
            "**High**\n\n"
            "# Reproduction Steps\n"
            "1. ...\n2. ...\n3. ...\n\n"
            "# Remediation\n"
            "- Apply upstream patch\n"
            "- Add WAF rule\n"
            "- Rotate secrets"
        )
    return (
        "Drop me a target, a command you just ran, or a finding. "
        "I will respond like a senior offensive engineer would: "
        "concrete commands, real tool names, no hand-waving."
    )


# ---------------------------------------------------------------------------
# OpenAI-compatible streaming provider
# ---------------------------------------------------------------------------


class OpenAiStreamingProvider:
    def __init__(
        self,
        *,
        api_url: str,
        api_key: str,
        timeout_seconds: float,
        model: str | None,
        auth_header_name: str = "Authorization",
    ) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.model = model
        self.auth_header_name = auth_header_name

    def stream(self, payload: RedTeamStreamRequest) -> Iterator[str]:
        body: dict[str, object] = {
            "messages": build_red_team_messages(payload),
            "temperature": 0.35,
            "stream": True,
        }
        if self.model:
            body["model"] = self.model

        serialized = json.dumps(body).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            self.auth_header_name: (
                f"Bearer {self.api_key}"
                if self.auth_header_name.lower() == "authorization"
                else self.api_key
            ),
        }
        http_request = request.Request(
            self.api_url,
            data=serialized,
            method="POST",
            headers=headers,
        )

        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        yield _sse_data({"type": "done"})
                        return
                    try:
                        parsed = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = (
                        parsed.get("choices", [{}])[0]
                        .get("delta", {})
                        .get("content")
                    )
                    if delta:
                        yield _sse_data({"type": "delta", "content": delta})
                yield _sse_data({"type": "done"})
        except error.URLError as exc:
            yield _sse_data(
                {
                    "type": "error",
                    "content": f"LLM provider unreachable: {exc.reason}",
                }
            )


# ---------------------------------------------------------------------------
# Service facade
# ---------------------------------------------------------------------------


class RedTeamCopilotService:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.provider_name = settings.llm_provider
        self.provider = self._build_provider()

    def _build_provider(self) -> OpenAiStreamingProvider | None:
        if self.provider_name in {"openai_compatible", "azure_openai"}:
            if self.settings.llm_api_url and self.settings.llm_api_key:
                auth_header = (
                    "api-key"
                    if self.provider_name == "azure_openai"
                    else "Authorization"
                )
                return OpenAiStreamingProvider(
                    api_url=self.settings.llm_api_url,
                    api_key=self.settings.llm_api_key,
                    model=self.settings.llm_model,
                    timeout_seconds=self.settings.llm_timeout_seconds,
                    auth_header_name=auth_header,
                )
        return None

    def stream(self, payload: RedTeamStreamRequest) -> Iterator[str]:
        if self.provider is None:
            yield from _fallback_stream(payload)
            return

        emitted = False
        try:
            for frame in self.provider.stream(payload):
                emitted = True
                yield frame
        except Exception as exc:  # noqa: BLE001
            yield _sse_data(
                {"type": "error", "content": f"provider exception: {exc}"}
            )

        if not emitted:
            yield from _fallback_stream(payload)

    # -- Deterministic attack-chain scaffold (non-LLM) --------------------
    def build_attack_chain_scaffold(self, target: str) -> AttackChainResponse:
        """Return a ready-to-render MITRE-aligned chain even without an LLM."""
        steps = [
            AttackChainStep(
                stage="Reconnaissance",
                description=f"Map the external attack surface of {target or 'the target'}.",
                tooling=["amass", "subfinder", "httpx", "shodan"],
                mitre=[
                    MitreTechnique(technique_id="T1595", name="Active Scanning", tactic="Reconnaissance"),
                    MitreTechnique(technique_id="T1590", name="Gather Victim Network Info", tactic="Reconnaissance"),
                ],
            ),
            AttackChainStep(
                stage="Initial Access",
                description="Phish a tier-1 user or hit an exposed service.",
                tooling=["gophish", "evilginx2", "metasploit"],
                mitre=[
                    MitreTechnique(technique_id="T1566.001", name="Spearphishing Attachment", tactic="Initial Access"),
                    MitreTechnique(technique_id="T1190", name="Exploit Public-Facing Application", tactic="Initial Access"),
                ],
            ),
            AttackChainStep(
                stage="Execution",
                description="Run operator code on the foothold.",
                tooling=["powershell", "python", "sliver"],
                mitre=[
                    MitreTechnique(technique_id="T1059.001", name="PowerShell", tactic="Execution"),
                ],
            ),
            AttackChainStep(
                stage="Privilege Escalation",
                description="Elevate to SYSTEM / root and collect creds.",
                tooling=["winpeas", "linpeas", "bloodhound"],
                mitre=[
                    MitreTechnique(technique_id="T1068", name="Exploit for Privilege Escalation", tactic="Privilege Escalation"),
                ],
            ),
            AttackChainStep(
                stage="Lateral Movement",
                description="Pivot to high-value assets across the domain.",
                tooling=["impacket", "crackmapexec", "rubeus"],
                mitre=[
                    MitreTechnique(technique_id="T1021.002", name="SMB/Windows Admin Shares", tactic="Lateral Movement"),
                ],
            ),
            AttackChainStep(
                stage="Exfiltration",
                description="Stage and transfer proof of compromise.",
                tooling=["rclone", "custom C2"],
                mitre=[
                    MitreTechnique(technique_id="T1041", name="Exfiltration Over C2 Channel", tactic="Exfiltration"),
                ],
            ),
        ]
        return AttackChainResponse(target=target or "scoped-target.example", steps=steps)


@lru_cache
def get_red_team_service() -> RedTeamCopilotService:
    return RedTeamCopilotService()
