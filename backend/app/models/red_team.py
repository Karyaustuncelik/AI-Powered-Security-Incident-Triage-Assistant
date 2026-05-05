# Red team / pentester copilot domain models.

from typing import Literal

from pydantic import BaseModel, Field


RedTeamMode = Literal["recon", "exploit", "attack_chain", "report", "general"]


class RedTeamMessage(BaseModel):
    """A single message exchanged with the red team copilot."""

    role: Literal["system", "user", "assistant"]
    content: str = Field(..., min_length=1)


class RedTeamStreamRequest(BaseModel):
    """Request body for a streaming red team copilot chat turn."""

    mode: RedTeamMode = "general"
    question: str = Field(..., min_length=1, max_length=8000)
    target: str | None = Field(default=None, max_length=512)
    context: str | None = Field(default=None, max_length=16000)
    history: list[RedTeamMessage] = Field(default_factory=list)


class MitreTechnique(BaseModel):
    """Lightweight MITRE ATT&CK technique reference for UI chips."""

    technique_id: str
    name: str
    tactic: str


class AttackChainStep(BaseModel):
    """Single stage of a generated attack chain."""

    stage: str
    description: str
    tooling: list[str] = Field(default_factory=list)
    mitre: list[MitreTechnique] = Field(default_factory=list)


class AttackChainResponse(BaseModel):
    """Deterministic attack chain skeleton used by the UI."""

    target: str
    steps: list[AttackChainStep] = Field(default_factory=list)
