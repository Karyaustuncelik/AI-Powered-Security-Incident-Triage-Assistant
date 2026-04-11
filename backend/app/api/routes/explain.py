# Bu dosya tek bir incident için explanation üretme endpoint'ini tanımlar.

from fastapi import APIRouter, HTTPException

from app.models.schemas import ExplanationResponse
from app.services.explanation_service import get_explanation_service
from app.services.incidents_service import IncidentsService


router = APIRouter(tags=["explain"])

incidents_service = IncidentsService()
explanation_service = get_explanation_service()


# `/explain/{incident_id}` endpoint'i seçilen incident için açıklama üretir.
@router.post("/explain/{incident_id}", response_model=ExplanationResponse)
def explain_incident(incident_id: str) -> ExplanationResponse:
    incident = incidents_service.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    explanation = explanation_service.explain_incident(incident)
    response = ExplanationResponse(
        incident_id=incident_id,
        explanation=explanation,
    )
    return response
