# Bu dosya incident bağlamında LLM copilot chat cevabı üretir.

import json
from functools import lru_cache
from urllib import error, request

from app.core.config import get_settings
from app.models.domain import EnrichedIncident
from app.models.schemas import (
    IncidentCopilotMessage,
    IncidentCopilotRequest,
    IncidentCopilotResponse,
)
from app.services.copilot_prompt_builder import build_incident_copilot_messages


class BaseCopilotProvider:
    def chat(self, incident: EnrichedIncident, payload: IncidentCopilotRequest) -> str:
        raise NotImplementedError


class MockCopilotProvider(BaseCopilotProvider):
    def chat(self, incident: EnrichedIncident, payload: IncidentCopilotRequest) -> str:
        return (
            f"This is a mock copilot response for {incident.incident_id}. "
            f"The current severity is {incident.severity.value}, the main indicators are "
            f"{', '.join(item.value for item in incident.detected_indicators) or 'none'}, "
            f"and the next recommended action is: {incident.suggested_action}"
        )


class TemplateCopilotProvider(BaseCopilotProvider):
    def chat(self, incident: EnrichedIncident, payload: IncidentCopilotRequest) -> str:
        lowered_question = payload.question.lower()
        if "neden" in lowered_question or "why" in lowered_question:
            return (
                f"{incident.incident_id} incident was prioritized as {incident.priority.value} "
                f"because the triage engine detected "
                f"{', '.join(item.value for item in incident.detected_indicators) or 'multiple signals'}."
            )
        if "ne yap" in lowered_question or "what should" in lowered_question:
            return incident.suggested_action
        return (
            f"For {incident.incident_id}, the safest grounded summary is: {incident.summary} "
            f"Recommended next action: {incident.suggested_action}"
        )


class OpenAiCompatibleCopilotProvider(BaseCopilotProvider):
    def __init__(
        self,
        *,
        api_url: str,
        api_key: str,
        timeout_seconds: float,
        model: str | None = None,
        auth_header_name: str = "Authorization",
    ) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.model = model
        self.auth_header_name = auth_header_name

    def chat(self, incident: EnrichedIncident, payload: IncidentCopilotRequest) -> str:
        body: dict[str, object] = {
            "messages": build_incident_copilot_messages(incident, payload),
            "temperature": 0.2,
        }
        if self.model:
            body["model"] = self.model

        response_payload = self._post_json(body)
        return self._extract_message_content(response_payload)

    def _post_json(self, body: dict[str, object]) -> dict:
        serialized = json.dumps(body).encode("utf-8")
        http_request = request.Request(
            self.api_url,
            data=serialized,
            method="POST",
            headers={
                "Content-Type": "application/json",
                self.auth_header_name: self._build_auth_value(),
            },
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise RuntimeError("Copilot provider request failed.") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Copilot provider returned invalid JSON.") from exc

    def _build_auth_value(self) -> str:
        if self.auth_header_name.lower() == "authorization":
            return f"Bearer {self.api_key}"
        return self.api_key

    def _extract_message_content(self, payload: dict) -> str:
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Copilot provider response is missing content.") from exc

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            if parts:
                return "\n".join(parts).strip()

        raise RuntimeError("Copilot provider content format is unsupported.")


class IncidentCopilotService:
    def __init__(self) -> None:
        settings = get_settings()
        self.provider_name = settings.llm_provider
        self.settings = settings
        self.template_provider = TemplateCopilotProvider()
        self.provider = self._build_provider()

    def _build_provider(self) -> BaseCopilotProvider:
        if self.provider_name == "mock":
            return MockCopilotProvider()
        if self.provider_name == "openai_compatible":
            if self.settings.llm_api_url and self.settings.llm_api_key:
                return OpenAiCompatibleCopilotProvider(
                    api_url=self.settings.llm_api_url,
                    api_key=self.settings.llm_api_key,
                    model=self.settings.llm_model,
                    timeout_seconds=self.settings.llm_timeout_seconds,
                )
            return self.template_provider
        if self.provider_name == "azure_openai":
            if self.settings.llm_api_url and self.settings.llm_api_key:
                return OpenAiCompatibleCopilotProvider(
                    api_url=self.settings.llm_api_url,
                    api_key=self.settings.llm_api_key,
                    model=self.settings.llm_model,
                    timeout_seconds=self.settings.llm_timeout_seconds,
                    auth_header_name="api-key",
                )
            return self.template_provider
        return self.template_provider

    def chat_about_incident(
        self,
        incident: EnrichedIncident,
        payload: IncidentCopilotRequest,
    ) -> IncidentCopilotResponse:
        try:
            content = self.provider.chat(incident, payload)
        except Exception:
            content = self.template_provider.chat(incident, payload)

        return IncidentCopilotResponse(
            incident_id=incident.incident_id,
            answer=IncidentCopilotMessage(role="assistant", content=content),
        )


@lru_cache
def get_incident_copilot_service() -> IncidentCopilotService:
    return IncidentCopilotService()
