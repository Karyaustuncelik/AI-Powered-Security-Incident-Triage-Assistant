# Bu dosya incident için insan diliyle açıklama üreten servis katmanıdır.

# JSON parse ve HTTP isteği için standart kütüphane araçları.
import json
# `lru_cache` aynı servis örneğini tekrar kullanmak için.
from functools import lru_cache
from urllib import error, request

# Ayarları okuyup hangi provider modunda olduğumuzu görebilmek için.
from app.core.config import get_settings
# Domain modelleri burada explanation üretmek için kullanılacak.
from app.models.domain import EnrichedIncident, ExplanationSource, IncidentExplanation
from app.services.prompt_builder import build_explanation_messages


# Provider sınıfları aynı isimle tek bir metod sunacak.
class BaseExplanationProvider:
    # Bu metod alt sınıflar tarafından doldurulacak.
    def generate(self, incident: EnrichedIncident) -> IncidentExplanation:
        raise NotImplementedError


# Şimdilik güvenilir çalışan fallback/template provider.
class TemplateExplanationProvider(BaseExplanationProvider):
    def generate(self, incident: EnrichedIncident) -> IncidentExplanation:
        indicator_text = ", ".join(
            indicator.value.replace("_", " ") for indicator in incident.detected_indicators
        )
        if not indicator_text:
            indicator_text = "backend heuristic signals"
        facts = ", ".join(
            f"{fact.label}: {fact.value}" for fact in incident.technical_facts[:4]
        )

        return IncidentExplanation(
            short_explanation=(
                f"{incident.summary} The triage engine assigned a {incident.severity.value} "
                f"severity score based on observed signals such as {indicator_text}."
            ),
            why_risky=(
                f"This incident is considered risky because the backend detected "
                f"{indicator_text}. Supporting facts include {facts}."
            ),
            recommended_action=incident.suggested_action,
            source=ExplanationSource.fallback,
        )


# İleride gerçek LLM provider eklemek için yer bırakan sınıf.
class MockLlmExplanationProvider(BaseExplanationProvider):
    def generate(self, incident: EnrichedIncident) -> IncidentExplanation:
        return IncidentExplanation(
            short_explanation=(
                f"{incident.summary} A mock explanation provider is active, so this "
                f"response simulates a structured analyst summary."
            ),
            why_risky=(
                f"The incident has a score of {incident.score} with indicators "
                f"{', '.join(indicator.value for indicator in incident.detected_indicators)}."
            ),
            recommended_action=incident.suggested_action,
            source=ExplanationSource.llm,
        )


# OpenAI-compatible veya Azure OpenAI endpoint'lerine istek atabilen provider.
class OpenAiCompatibleExplanationProvider(BaseExplanationProvider):
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

    def generate(self, incident: EnrichedIncident) -> IncidentExplanation:
        body: dict[str, object] = {
            "messages": build_explanation_messages(incident),
            "temperature": 0.2,
        }
        if self.model:
            body["model"] = self.model

        response_payload = self._post_json(body)
        content = self._extract_message_content(response_payload)
        parsed_explanation = self._parse_explanation_json(content)

        return IncidentExplanation(
            short_explanation=parsed_explanation["short_explanation"],
            why_risky=parsed_explanation["why_risky"],
            recommended_action=parsed_explanation["recommended_action"],
            source=ExplanationSource.llm,
        )

    def _post_json(self, body: dict[str, object]) -> dict:
        payload = json.dumps(body).encode("utf-8")
        http_request = request.Request(
            self.api_url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                self.auth_header_name: self._build_auth_header_value(),
            },
        )

        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise RuntimeError("LLM provider request failed.") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("LLM provider returned invalid JSON.") from exc

    def _build_auth_header_value(self) -> str:
        if self.auth_header_name.lower() == "authorization":
            return f"Bearer {self.api_key}"
        return self.api_key

    def _extract_message_content(self, payload: dict) -> str:
        try:
            message_content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("LLM provider response is missing message content.") from exc

        if isinstance(message_content, str):
            return message_content

        if isinstance(message_content, list):
            text_fragments: list[str] = []
            for part in message_content:
                if isinstance(part, dict):
                    if "text" in part and isinstance(part["text"], str):
                        text_fragments.append(part["text"])
                    elif part.get("type") == "output_text" and isinstance(
                        part.get("text"), str
                    ):
                        text_fragments.append(part["text"])
            if text_fragments:
                return "\n".join(text_fragments)

        raise RuntimeError("LLM provider response content format is unsupported.")

    def _parse_explanation_json(self, content: str) -> dict[str, str]:
        cleaned_content = content.strip()

        if cleaned_content.startswith("```"):
            cleaned_content = cleaned_content.strip("`")
            cleaned_content = cleaned_content.removeprefix("json").strip()

        first_brace = cleaned_content.find("{")
        last_brace = cleaned_content.rfind("}")
        if first_brace != -1 and last_brace != -1:
            cleaned_content = cleaned_content[first_brace : last_brace + 1]

        try:
            parsed = json.loads(cleaned_content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("LLM explanation content is not valid JSON.") from exc

        required_fields = {
            "short_explanation",
            "why_risky",
            "recommended_action",
        }
        missing_fields = [
            field_name for field_name in required_fields if field_name not in parsed
        ]
        if missing_fields:
            raise RuntimeError(
                f"LLM explanation is missing required fields: {', '.join(missing_fields)}"
            )

        return {
            "short_explanation": str(parsed["short_explanation"]).strip(),
            "why_risky": str(parsed["why_risky"]).strip(),
            "recommended_action": str(parsed["recommended_action"]).strip(),
        }


# Bu servis explanation üretir ve memory cache tutar.
class ExplanationService:
    def __init__(self) -> None:
        settings = get_settings()
        self.provider_name = settings.llm_provider
        self.settings = settings
        self.cache: dict[str, IncidentExplanation] = {}
        self.template_provider = TemplateExplanationProvider()
        self.provider = self._build_provider()

    # Ayardaki provider adına göre hangi açıklama üreticisinin kullanılacağını seç.
    def _build_provider(self) -> BaseExplanationProvider:
        if self.provider_name == "mock":
            return MockLlmExplanationProvider()
        if self.provider_name == "openai_compatible":
            if self.settings.llm_api_url and self.settings.llm_api_key:
                return OpenAiCompatibleExplanationProvider(
                    api_url=self.settings.llm_api_url,
                    api_key=self.settings.llm_api_key,
                    model=self.settings.llm_model,
                    timeout_seconds=self.settings.llm_timeout_seconds,
                )
            return self.template_provider
        if self.provider_name == "azure_openai":
            if self.settings.llm_api_url and self.settings.llm_api_key:
                return OpenAiCompatibleExplanationProvider(
                    api_url=self.settings.llm_api_url,
                    api_key=self.settings.llm_api_key,
                    model=self.settings.llm_model,
                    timeout_seconds=self.settings.llm_timeout_seconds,
                    auth_header_name="api-key",
                )
            return self.template_provider
        return self.template_provider

    # Incident için explanation üret; hata olursa fallback'e dön.
    def explain_incident(self, incident: EnrichedIncident) -> IncidentExplanation:
        try:
            explanation = self.provider.generate(incident)
        except Exception:
            explanation = self.template_provider.generate(incident)

        self.cache[incident.incident_id] = explanation
        return explanation

    # Daha önce explanation üretildiyse cache'ten getir.
    def get_cached_explanation(self, incident_id: str) -> IncidentExplanation | None:
        return self.cache.get(incident_id)


# Servisi tek noktadan almak için helper.
@lru_cache
def get_explanation_service() -> ExplanationService:
    return ExplanationService()
