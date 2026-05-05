# Red team / pentester copilot API routes.
#
# /red-team/stream       POST   Server-Sent Events streaming chat
# /red-team/attack-chain GET    Deterministic MITRE-aligned attack chain

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.models.red_team import AttackChainResponse, RedTeamStreamRequest
from app.services.red_team_service import (
    RedTeamCopilotService,
    get_red_team_service,
)


router = APIRouter(prefix="/red-team", tags=["red-team"])


@router.post("/stream")
def stream_red_team_chat(
    payload: RedTeamStreamRequest,
    service: RedTeamCopilotService = Depends(get_red_team_service),
) -> StreamingResponse:
    """Stream a red team copilot response as Server-Sent Events."""
    return StreamingResponse(
        service.stream(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/attack-chain", response_model=AttackChainResponse)
def get_attack_chain_scaffold(
    target: str = "",
    service: RedTeamCopilotService = Depends(get_red_team_service),
) -> AttackChainResponse:
    """Return a deterministic MITRE-aligned kill chain — works without LLM."""
    return service.build_attack_chain_scaffold(target)
