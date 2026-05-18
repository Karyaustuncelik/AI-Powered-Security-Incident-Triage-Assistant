# Bu dosya incident listeleme ve detay endpoint'lerini tanımlar.

from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.models.domain import IncidentEventType, PriorityLevel, SeverityLevel
from app.models.schemas import (
    IncidentCopilotRequest,
    IncidentCopilotResponse,
    IncidentDetailResponse,
    IncidentListItem,
)
from app.services.incidents_service import IncidentsService, to_detail_response, to_list_item


# Bu router incident işlemlerini tek başlık altında toplar.
router = APIRouter(tags=["incidents"])

# Şimdilik service'i burada oluşturuyoruz; ileride dependency injection ekleyebiliriz.
incidents_service = IncidentsService()


# `/incidents` endpoint'i incident listesini döner.
@router.get("/incidents", response_model=list[IncidentListItem])
def list_incidents(
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
    incidents = incidents_service.filter_incidents(
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
    return [to_list_item(incident) for incident in incidents]


# `/incidents/{incident_id}` endpoint'i tek incident detayını döner.
@router.get("/incidents/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(incident_id: str) -> IncidentDetailResponse:
    incident = incidents_service.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return to_detail_response(incident)


@router.post("/incidents/{incident_id}/chat", response_model=IncidentCopilotResponse)
def chat_about_incident(
    incident_id: str,
    payload: IncidentCopilotRequest,
) -> IncidentCopilotResponse:
    response = incidents_service.chat_about_incident(incident_id, payload)
    if response is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return response


@router.get("/incidents/{incident_id}/related")
def get_related_incidents(incident_id: str) -> list[IncidentListItem]:
    target = incidents_service.get_incident(incident_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    all_incidents = incidents_service.list_incidents()
    related = [
        incident
        for incident in all_incidents
        if incident.incident_id != incident_id
        and (
            incident.actor_user == target.actor_user
            or incident.affected_entity == target.affected_entity
        )
    ]

    related.sort(key=lambda incident: incident.score, reverse=True)
    related = related[:10]

    return [to_list_item(incident) for incident in related]


@router.get("/incidents/{incident_id}/response-plan")
def get_response_plan(incident_id: str) -> dict:
    plan = incidents_service.generate_response_plan(incident_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return plan
