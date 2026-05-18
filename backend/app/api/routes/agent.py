"""API routes for the AI Security Agent.

Provides SSE-streaming endpoint for real-time agent execution
and a one-shot endpoint for quick assessments.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.agent.engine import get_security_agent

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    target: str = Field(..., min_length=3, description="Target URL or domain to assess")
    goal: str | None = Field(default=None, description="Optional specific assessment goal")


@router.post("/run")
def run_agent(body: AgentRunRequest) -> StreamingResponse:
    """Run the AI security agent. Streams SSE events with tool calls, findings, and summary."""
    agent = get_security_agent()
    return StreamingResponse(
        agent.run(target=body.target, goal=body.goal),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/tools")
def list_tools() -> list[dict]:
    """Return the list of available security tools the agent can use."""
    from app.services.agent.tools import TOOL_REGISTRY
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        }
        for tool in TOOL_REGISTRY.values()
    ]
