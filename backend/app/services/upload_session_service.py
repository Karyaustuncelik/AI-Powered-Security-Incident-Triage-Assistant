# Bu dosya yüklenen log dosyasını parse eder, incident üretir ve session olarak saklar.

from datetime import UTC, datetime
from functools import lru_cache
from uuid import uuid4

from app.models.domain import (
    EnrichedIncident,
    IncidentEventType,
    PriorityLevel,
    ReviewStatus,
    SeverityLevel,
    UploadSession,
)
from app.models.schemas import (
    FiltersOptionsResponse,
    IncidentCopilotResponse,
    IncidentCopilotRequest,
    UploadLogRequest,
    UploadSessionResponse,
)
from app.services.copilot_service import get_incident_copilot_service
from app.services.explanation_service import get_explanation_service
from app.services.incidents_service import to_detail_response, to_list_item
from app.services.log_correlation_service import get_log_correlation_service
from app.services.log_parser_service import get_log_parser_service
from app.services.review_service import get_review_service
from app.services.stats_service import StatsService
from app.services.triage_engine import get_triage_engine
from app.services.upload_session_repository import UploadSessionRepository
from app.utils.datetime_utils import normalize_optional_datetime


class UploadSessionService:
    def __init__(self) -> None:
        self.copilot_service = get_incident_copilot_service()
        self.explanation_service = get_explanation_service()
        self.log_correlation_service = get_log_correlation_service()
        self.log_parser_service = get_log_parser_service()
        self.repository = UploadSessionRepository()
        self.review_service = get_review_service()
        self.stats_service = StatsService()
        self.triage_engine = get_triage_engine()

    def create_session(self, payload: UploadLogRequest) -> UploadSessionResponse:
        upload_id = uuid4().hex[:10]
        parser_format, raw_bytes, normalized_events = self.log_parser_service.parse_upload(
            payload.filename,
            payload.content_base64,
        )
        correlated_incidents = self.log_correlation_service.correlate(upload_id, normalized_events)

        session = UploadSession(
            upload_id=upload_id,
            filename=payload.filename,
            parser_format=parser_format,
            created_at=datetime.now(UTC),
            raw_event_count=len(normalized_events),
            normalized_event_count=len(normalized_events),
            correlated_incidents=correlated_incidents,
        )
        self.repository.save_session(session, original_bytes=raw_bytes)
        return self._to_session_response(session)

    def filter_incidents(
        self,
        upload_id: str,
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
        incidents = self.list_incidents(upload_id)
        filtered_incidents: list[EnrichedIncident] = []
        normalized_start_time = normalize_optional_datetime(start_time)
        normalized_end_time = normalize_optional_datetime(end_time)

        if (
            normalized_start_time is not None
            and normalized_end_time is not None
            and normalized_start_time > normalized_end_time
        ):
            normalized_start_time, normalized_end_time = normalized_end_time, normalized_start_time

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
                    " ".join(incident.source_event_samples),
                ]
                haystack = " ".join(searchable_parts).lower()
                if normalized_search not in haystack:
                    continue

            filtered_incidents.append(incident)

        return sorted(filtered_incidents, key=lambda item: item.timestamp, reverse=True)

    def list_incidents(self, upload_id: str) -> list[EnrichedIncident]:
        session = self._get_required_session(upload_id)
        return [
            self._enrich_correlated(artifact)
            for artifact in session.correlated_incidents
        ]

    def get_incident(self, upload_id: str, incident_id: str) -> EnrichedIncident | None:
        for incident in self.list_incidents(upload_id):
            if incident.incident_id == incident_id:
                return incident
        return None

    def get_stats(self, upload_id: str, **filters: object):
        incidents = self.filter_incidents(upload_id, **filters)
        return self.stats_service.build_stats(incidents)

    def get_filter_options(self, upload_id: str) -> FiltersOptionsResponse:
        incidents = self.list_incidents(upload_id)
        return FiltersOptionsResponse(
            severity_options=list(SeverityLevel),
            priority_options=list(PriorityLevel),
            review_status_options=list(ReviewStatus),
            event_type_options=list(IncidentEventType),
            category_options=sorted(
                {incident.category for incident in incidents},
                key=lambda category: category.value,
            ),
            actor_options=sorted({incident.actor_user for incident in incidents}),
            entity_options=sorted({incident.affected_entity for incident in incidents}),
        )

    def chat_about_incident(
        self,
        upload_id: str,
        incident_id: str,
        payload: IncidentCopilotRequest,
    ) -> IncidentCopilotResponse:
        incident = self.get_incident(upload_id, incident_id)
        if incident is None:
            raise ValueError("Incident not found in upload session.")
        return self.copilot_service.chat_about_incident(incident, payload)

    def get_session_summary(self, upload_id: str) -> UploadSessionResponse:
        return self._to_session_response(self._get_required_session(upload_id))

    def _enrich_correlated(self, artifact) -> EnrichedIncident:
        incident = self.triage_engine.enrich_incident(artifact.incident)
        incident.source_event_count = artifact.source_event_count
        incident.source_event_samples = artifact.source_event_samples

        cached_explanation = self.explanation_service.get_cached_explanation(incident.incident_id)
        if cached_explanation is not None:
            incident.llm_explanation = cached_explanation

        incident.review = self.review_service.get_review(incident.incident_id)
        return incident

    def _get_required_session(self, upload_id: str) -> UploadSession:
        session = self.repository.get_session(upload_id)
        if session is None:
            raise ValueError("Upload session not found.")
        return session

    def _to_session_response(self, session: UploadSession) -> UploadSessionResponse:
        return UploadSessionResponse(
            upload_id=session.upload_id,
            filename=session.filename,
            parser_format=session.parser_format,
            created_at=session.created_at,
            raw_event_count=session.raw_event_count,
            normalized_event_count=session.normalized_event_count,
            incident_count=len(session.correlated_incidents),
        )


@lru_cache
def get_upload_session_service() -> UploadSessionService:
    return UploadSessionService()
