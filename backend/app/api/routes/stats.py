# Bu dosya dashboard istatistik endpoint'ini tanımlar.

from datetime import datetime

from fastapi import APIRouter

from app.models.domain import IncidentEventType, PriorityLevel, SeverityLevel
from app.models.schemas import StatsResponse
from app.services.incidents_service import IncidentsService
from app.services.stats_service import StatsService


router = APIRouter(tags=["stats"])

incidents_service = IncidentsService()
stats_service = StatsService()


# `/stats` endpoint'i dashboard kartları ve dağılımlar için veri döner.
@router.get("/stats", response_model=StatsResponse)
def get_stats(
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
    stats = stats_service.build_stats(incidents)
    return stats
