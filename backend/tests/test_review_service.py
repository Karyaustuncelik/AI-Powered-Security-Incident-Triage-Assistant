import unittest

from app.models.schemas import IncidentReviewUpdateRequest
from app.services.review_service import get_review_service


class ReviewServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = get_review_service()

    def test_review_can_be_saved_and_loaded(self) -> None:
        saved_review = self.service.upsert_review(
            "INC-1005",
            IncidentReviewUpdateRequest(
                review_status="in_progress",
                assigned_analyst="security.analyst",
                review_notes="Investigating impossible travel activity.",
            ),
        )

        loaded_review = self.service.get_review("INC-1005")

        self.assertEqual(saved_review.review_status.value, "in_progress")
        self.assertIsNotNone(loaded_review)
        self.assertEqual(loaded_review.assigned_analyst, "security.analyst")
