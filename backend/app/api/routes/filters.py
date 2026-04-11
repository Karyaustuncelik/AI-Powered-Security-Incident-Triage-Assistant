# Bu dosya filtre seçeneklerini dönen endpoint'i tanımlar.

from fastapi import APIRouter

from app.models.schemas import FiltersOptionsResponse
from app.services.incidents_service import IncidentsService


router = APIRouter(tags=["filters"])

incidents_service = IncidentsService()


# `/filters/options` endpoint'i dropdown seçeneklerini döner.
@router.get("/filters/options", response_model=FiltersOptionsResponse)
def get_filter_options() -> FiltersOptionsResponse:
    options = incidents_service.get_filter_options()
    return options
