# Bu dosya incident review güncelleme endpoint'ini tanımlar.

from fastapi import APIRouter, HTTPException

from app.models.schemas import IncidentReviewResponse, IncidentReviewUpdateRequest
from app.services.incidents_service import IncidentsService
from app.services.review_service import get_review_service


router = APIRouter(tags=["review"])

incidents_service = IncidentsService()
review_service = get_review_service()


@router.put("/incidents/{incident_id}/review", response_model=IncidentReviewResponse)
def update_incident_review(
    incident_id: str,
    payload: IncidentReviewUpdateRequest,
) -> IncidentReviewResponse:
    incident = incidents_service.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    review = review_service.upsert_review(incident_id, payload)
    return IncidentReviewResponse(incident_id=incident_id, review=review)
