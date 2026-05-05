# Bu dosya incident copilot chat'i için LLM mesajlarını üretir.

from app.models.domain import EnrichedIncident
from app.models.schemas import IncidentCopilotRequest


def build_incident_copilot_messages(
    incident: EnrichedIncident,
    payload: IncidentCopilotRequest,
) -> list[dict[str, str]]:
    technical_facts = "\n".join(
        f"- {fact.label}: {fact.value}" for fact in incident.technical_facts
    )
    indicators = ", ".join(item.value for item in incident.detected_indicators) or "none"
    source_samples = "\n".join(f"- {sample}" for sample in incident.source_event_samples) or "- none"
    score_breakdown = "\n".join(
        f"- {item.indicator.value}: +{item.weight} because {item.reason}"
        for item in incident.score_breakdown
    )

    system_message = (
        "You are a security incident copilot. "
        "Answer only from the incident context you were given. "
        "Do not invent unsupported facts. "
        "Be concise, technical, and helpful."
    )

    incident_context = (
        f"Incident ID: {incident.incident_id}\n"
        f"Category: {incident.category.value}\n"
        f"Event Type: {incident.event_type.value}\n"
        f"Severity: {incident.severity.value}\n"
        f"Priority: {incident.priority.value}\n"
        f"Summary: {incident.summary}\n"
        f"Suggested Action: {incident.suggested_action}\n"
        f"Indicators: {indicators}\n"
        f"Score: {incident.score}\n"
        f"Score Breakdown:\n{score_breakdown}\n"
        f"Technical Facts:\n{technical_facts}\n"
        f"Supporting Raw Event Samples:\n{source_samples}\n"
    )

    messages = [
        {"role": "system", "content": system_message},
        {"role": "system", "content": incident_context},
    ]

    for message in payload.history[-8:]:
        messages.append({"role": message.role, "content": message.content})

    messages.append({"role": "user", "content": payload.question})
    return messages
