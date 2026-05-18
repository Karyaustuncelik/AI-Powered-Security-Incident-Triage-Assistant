"""AI Security Agent — ReAct-pattern tool-calling agent for automated security assessment.

The agent follows the Reasoning + Acting (ReAct) paradigm:
  1. Observe the current state
  2. Think about what to do next
  3. Select and call a security tool
  4. Incorporate the observation
  5. Repeat until a final assessment is ready

All tool executions and reasoning steps are streamed via SSE so the
frontend can render the agent's chain-of-thought in real time.
"""

from app.services.agent.engine import SecurityAgent, get_security_agent
from app.services.agent.tools import TOOL_REGISTRY, SecurityTool

__all__ = ["SecurityAgent", "get_security_agent", "TOOL_REGISTRY", "SecurityTool"]
