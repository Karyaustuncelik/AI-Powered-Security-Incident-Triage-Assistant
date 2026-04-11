# Bu dosya analyst review workflow mantığını taşır.

from functools import lru_cache

from app.models.domain import IncidentReview
from app.models.schemas import IncidentReviewUpdateRequest
from app.services.review_repository import get_review_repository


class ReviewService:
    def __init__(self) -> None:
        self.repository = get_review_repository()

    def get_review(self, incident_id: str) -> IncidentReview | None:
        return self.repository.get_review(incident_id)

    def upsert_review(
        self,
        incident_id: str,
        payload: IncidentReviewUpdateRequest,
    ) -> IncidentReview:
        review = IncidentReview(
            incident_id=incident_id,
            review_status=payload.review_status,
            assigned_analyst=payload.assigned_analyst,
            review_notes=payload.review_notes,
        )
        return self.repository.save_review(review)


@lru_cache
def get_review_service() -> ReviewService:
    return ReviewService()
