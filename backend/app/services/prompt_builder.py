# Bu dosya LLM'e gidecek structured incident özetini üretir.

import json

from app.models.domain import EnrichedIncident


# Incident'i LLM'e yollamadan önce düzenli bir sözlüğe çevir.
def build_explanation_payload(incident: EnrichedIncident) -> dict:
    return {
        "incident_id": incident.incident_id,
        "timestamp": incident.timestamp.isoformat(),
        "event_type": incident.event_type.value,
        "category": incident.category.value,
        "severity": incident.severity.value,
        "priority": incident.priority.value,
        "score": incident.score,
        "affected_entity": incident.affected_entity,
        "actor_user": incident.actor_user,
        "source_system": incident.source_system,
        "summary": incident.summary,
        "detected_indicators": [
            indicator.value for indicator in incident.detected_indicators
        ],
        "technical_facts": [
            {"label": fact.label, "value": fact.value}
            for fact in incident.technical_facts
        ],
        "score_breakdown": [
            {
                "indicator": contribution.indicator.value,
                "weight": contribution.weight,
                "reason": contribution.reason,
            }
            for contribution in incident.score_breakdown
        ],
        "suggested_action": incident.suggested_action,
    }


# OpenAI-compatible chat completions biçiminde mesaj listesi oluştur.
def build_explanation_messages(incident: EnrichedIncident) -> list[dict[str, str]]:
    payload = json.dumps(build_explanation_payload(incident), indent=2)

    system_message = (
        "You are a senior security analyst assistant. "
        "Explain incidents in calm, professional language for a SOC dashboard. "
        "Return JSON only with the keys short_explanation, why_risky, recommended_action. "
        "Keep each field concise and grounded in the supplied facts."
    )

    user_message = (
        "Generate an analyst-ready explanation for the following security incident.\n"
        "Use only the provided data and do not invent facts.\n\n"
        f"{payload}"
    )

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]
