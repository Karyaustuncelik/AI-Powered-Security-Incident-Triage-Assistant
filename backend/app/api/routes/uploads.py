# Bu dosya yüklenen log dosyaları için upload, incident ve copilot endpoint'lerini tanımlar.

from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.models.domain import IncidentEventType, PriorityLevel, SeverityLevel
from app.models.schemas import (
    FiltersOptionsResponse,
    IncidentCopilotRequest,
    IncidentCopilotResponse,
    IncidentDetailResponse,
    IncidentListItem,
    StatsResponse,
    UploadLogRequest,
    UploadSessionResponse,
)
from app.services.incidents_service import to_detail_response, to_list_item
from app.services.upload_session_service import get_upload_session_service


router = APIRouter(tags=["uploads"])

upload_session_service = get_upload_session_service()


@router.post("/uploads/logs", response_model=UploadSessionResponse)
def upload_logs(payload: UploadLogRequest) -> UploadSessionResponse:
    return upload_session_service.create_session(payload)


@router.get("/uploads/{upload_id}/incidents", response_model=list[IncidentListItem])
def list_uploaded_incidents(
    upload_id: str,
    severity: SeverityLevel | None = None,
    priority: PriorityLevel | None = None,
    event_type: IncidentEventType | None = None,
    affected_entity: str | None = None,
    actor_user: str | None = None,
    review_status: str | None = None,
    search: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[IncidentListItem]:
    try:
        incidents = upload_session_service.filter_incidents(
            upload_id,
            severity=severity,
            priority=priority,
            event_type=event_type,
            affected_entity=affected_entity,
            actor_user=actor_user,
            review_status=review_status,
            search=search,
            start_time=start_time,
            end_time=end_time,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return [to_list_item(incident) for incident in incidents]


@router.get(
    "/uploads/{upload_id}/incidents/{incident_id}",
    response_model=IncidentDetailResponse,
)
def get_uploaded_incident(
    upload_id: str,
    incident_id: str,
) -> IncidentDetailResponse:
    try:
        incident = upload_session_service.get_incident(upload_id, incident_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found in upload session")
    return to_detail_response(incident)


@router.get("/uploads/{upload_id}/stats", response_model=StatsResponse)
def get_uploaded_stats(
    upload_id: str,
    severity: SeverityLevel | None = None,
    priority: PriorityLevel | None = None,
    event_type: IncidentEventType | None = None,
    affected_entity: str | None = None,
    actor_user: str | None = None,
    review_status: str | None = None,
    search: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> StatsResponse:
    try:
        return upload_session_service.get_stats(
            upload_id,
            severity=severity,
            priority=priority,
            event_type=event_type,
            affected_entity=affected_entity,
            actor_user=actor_user,
            review_status=review_status,
            search=search,
            start_time=start_time,
            end_time=end_time,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/uploads/{upload_id}/filters/options", response_model=FiltersOptionsResponse)
def get_uploaded_filter_options(upload_id: str) -> FiltersOptionsResponse:
    try:
        return upload_session_service.get_filter_options(upload_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/uploads/{upload_id}/incidents/{incident_id}/chat",
    response_model=IncidentCopilotResponse,
)
def chat_about_uploaded_incident(
    upload_id: str,
    incident_id: str,
    payload: IncidentCopilotRequest,
) -> IncidentCopilotResponse:
    try:
        return upload_session_service.chat_about_incident(upload_id, incident_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
