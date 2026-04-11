import unittest

from app.api.routes.explain import explain_incident
from app.api.routes.filters import get_filter_options
from app.api.routes.health import health_check
from app.api.routes.incidents import get_incident, list_incidents
from app.api.routes.stats import get_stats


class ApiTests(unittest.TestCase):
    def test_health_endpoint(self) -> None:
        payload = health_check()

        self.assertEqual(payload["status"], "ok")
        self.assertIn("service", payload)

    def test_incidents_endpoint_returns_queue_items(self) -> None:
        payload = list_incidents()

        self.assertGreater(len(payload), 0)
        self.assertTrue(hasattr(payload[0], "incident_id"))
        self.assertTrue(hasattr(payload[0], "priority"))

    def test_incident_detail_endpoint_returns_rich_payload(self) -> None:
        payload = get_incident("INC-1005")

        self.assertEqual(payload.incident_id, "INC-1005")
        self.assertGreater(payload.score, 0)
        self.assertGreater(len(payload.detected_indicators), 0)

    def test_stats_endpoint_returns_dashboard_payload(self) -> None:
        payload = get_stats()

        self.assertGreaterEqual(payload.total_incidents, 1)
        self.assertIsInstance(payload.recent_incidents, list)

    def test_filters_options_endpoint_returns_actor_options(self) -> None:
        payload = get_filter_options()

        self.assertGreater(len(payload.actor_options), 0)
        self.assertGreater(len(payload.entity_options), 0)

    def test_explain_endpoint_returns_structured_explanation(self) -> None:
        payload = explain_incident("INC-1005")

        self.assertEqual(payload.incident_id, "INC-1005")
        self.assertGreater(len(payload.explanation.short_explanation), 10)

    def test_review_endpoint_updates_incident_review(self) -> None:
        from app.api.routes.review import update_incident_review
        from app.models.schemas import IncidentReviewUpdateRequest

        payload = update_incident_review(
            "INC-1005",
            IncidentReviewUpdateRequest(
                review_status="resolved",
                assigned_analyst="sec.ops",
                review_notes="User confirmed travel and the case was closed.",
            ),
        )

        self.assertEqual(payload.incident_id, "INC-1005")
        self.assertEqual(payload.review.review_status.value, "resolved")
