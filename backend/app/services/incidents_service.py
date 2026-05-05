# Bu dosya incident listeleme ve detay alma işini tek yerde toplar.

from datetime import datetime

from app.models.domain import (
    EnrichedIncident,
    IncidentEventType,
    PriorityLevel,
    ReviewStatus,
    SeverityLevel,
)
from app.models.schemas import (
    IncidentCopilotRequest,
    IncidentCopilotResponse,
    FiltersOptionsResponse,
    IncidentDetailResponse,
    IncidentListItem,
)
from app.services.copilot_service import get_incident_copilot_service
from app.services.explanation_service import get_explanation_service
from app.services.repository import get_incident_repository
from app.services.review_service import get_review_service
from app.services.triage_engine import get_triage_engine
from app.utils.datetime_utils import normalize_optional_datetime


# EnrichedIncident modelini liste ekranı için kısa modele çevir.
def to_list_item(incident: EnrichedIncident) -> IncidentListItem:
    return IncidentListItem(
        incident_id=incident.incident_id,
        timestamp=incident.timestamp,
        event_type=incident.event_type,
        affected_entity=incident.affected_entity,
        severity=incident.severity,
        priority=incident.priority,
        review_status=incident.review.review_status if incident.review else ReviewStatus.open,
        assigned_analyst=incident.review.assigned_analyst if incident.review else None,
    )


# EnrichedIncident modelini detay cevabına çevir.
def to_detail_response(incident: EnrichedIncident) -> IncidentDetailResponse:
    return IncidentDetailResponse(
        incident_id=incident.incident_id,
        timestamp=incident.timestamp,
        event_type=incident.event_type,
        category=incident.category,
        affected_entity=incident.affected_entity,
        actor_user=incident.actor_user,
        source_system=incident.source_system,
        summary=incident.summary,
        technical_facts=incident.technical_facts,
        detected_indicators=incident.detected_indicators,
        score_breakdown=incident.score_breakdown,
        score=incident.score,
        severity=incident.severity,
        priority=incident.priority,
        suggested_action=incident.suggested_action,
        source_event_count=incident.source_event_count,
        source_event_samples=incident.source_event_samples,
        review=incident.review,
        llm_explanation=incident.llm_explanation,
    )


# Incident verisini yükleyip triage engine ile zenginleştiren servis.
class IncidentsService:
    def __init__(self) -> None:
        self.copilot_service = get_incident_copilot_service()
        self.explanation_service = get_explanation_service()
        self.repository = get_incident_repository()
        self.review_service = get_review_service()
        self.triage_engine = get_triage_engine()

    # Tüm kayıtları zenginleştirip liste halinde döndür.
    def list_incidents(self) -> list[EnrichedIncident]:
        raw_records = self.repository.list_incidents()
        incidents = self.triage_engine.enrich_many(raw_records)
        return [self._attach_cached_explanation(incident) for incident in incidents]

    # Filtre parametrelerine göre incident listesini daralt.
    def filter_incidents(
        self,
        *,
        severity: SeverityLevel | None = None,
        priority: PriorityLevel | None = None,
        event_type: IncidentEventType | None = None,
        affected_entity: str | None = None,
        actor_user: str | None = None,
        review_status: str | None = None,
        search: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[EnrichedIncident]:
        incidents = self.list_incidents()
        filtered_incidents: list[EnrichedIncident] = []
        normalized_start_time = normalize_optional_datetime(start_time)
        normalized_end_time = normalize_optional_datetime(end_time)

        if (
            normalized_start_time is not None
            and normalized_end_time is not None
            and normalized_start_time > normalized_end_time
        ):
            normalized_start_time, normalized_end_time = (
                normalized_end_time,
                normalized_start_time,
            )

        normalized_entity = affected_entity.lower() if affected_entity else None
        normalized_actor = actor_user.lower() if actor_user else None
        normalized_search = search.lower() if search else None

        for incident in incidents:
            if severity and incident.severity != severity:
                continue
            if priority and incident.priority != priority:
                continue
            if event_type and incident.event_type != event_type:
                continue
            if normalized_entity and normalized_entity not in incident.affected_entity.lower():
                continue
            if normalized_actor and normalized_actor not in incident.actor_user.lower():
                continue
            if review_status and (
                incident.review is None or incident.review.review_status.value != review_status
            ):
                continue
            if normalized_start_time and incident.timestamp < normalized_start_time:
                continue
            if normalized_end_time and incident.timestamp > normalized_end_time:
                continue
            if normalized_search:
                searchable_parts = [
                    incident.incident_id,
                    incident.affected_entity,
                    incident.actor_user,
                    incident.event_type.value,
                    incident.summary,
                ]
                haystack = " ".join(searchable_parts).lower()
                if normalized_search not in haystack:
                    continue

            filtered_incidents.append(incident)

        return sorted(
            filtered_incidents,
            key=lambda incident: incident.timestamp,
            reverse=True,
        )

    # Tek incident'i bulup zenginleştir.
    def get_incident(self, incident_id: str) -> EnrichedIncident | None:
        raw_record = self.repository.get_incident(incident_id)
        if raw_record is None:
            return None
        incident = self.triage_engine.enrich_incident(raw_record)
        return self._attach_cached_explanation(incident)

    def chat_about_incident(
        self,
        incident_id: str,
        payload: IncidentCopilotRequest,
    ) -> IncidentCopilotResponse | None:
        incident = self.get_incident(incident_id)
        if incident is None:
            return None
        return self.copilot_service.chat_about_incident(incident, payload)

    # Filtre dropdown'ları için seçenekleri çıkar.
    def get_filter_options(self) -> FiltersOptionsResponse:
        incidents = self.list_incidents()
        actor_options = sorted({incident.actor_user for incident in incidents})
        entity_options = sorted({incident.affected_entity for incident in incidents})

        return FiltersOptionsResponse(
            severity_options=list(SeverityLevel),
            priority_options=list(PriorityLevel),
            review_status_options=list(ReviewStatus),
            event_type_options=list(IncidentEventType),
            category_options=sorted(
                {incident.category for incident in incidents},
                key=lambda category: category.value,
            ),
            actor_options=actor_options,
            entity_options=entity_options,
        )

    # Cache'te explanation varsa incident modeline ekle.
    def _attach_cached_explanation(self, incident: EnrichedIncident) -> EnrichedIncident:
        cached_explanation = self.explanation_service.get_cached_explanation(incident.incident_id)
        if cached_explanation is not None:
            incident.llm_explanation = cached_explanation
        incident.review = self.review_service.get_review(incident.incident_id)
        return incident
