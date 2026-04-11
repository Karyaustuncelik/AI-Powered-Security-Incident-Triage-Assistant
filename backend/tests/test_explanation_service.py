import unittest

from app.models.domain import IncidentExplanation
from app.services.explanation_service import BaseExplanationProvider, ExplanationService
from app.services.incidents_service import IncidentsService


class BrokenProvider(BaseExplanationProvider):
    def generate(self, incident):  # type: ignore[override]
        raise RuntimeError("provider failure")


class ExplanationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.incidents_service = IncidentsService()
        self.incident = self.incidents_service.get_incident("INC-1005")

    def test_fallback_is_used_when_provider_fails(self) -> None:
        if self.incident is None:
            self.fail("Fixture incident was not found.")

        service = ExplanationService()
        service.provider = BrokenProvider()

        explanation = service.explain_incident(self.incident)

        self.assertIsInstance(explanation, IncidentExplanation)
        self.assertEqual(explanation.source.value, "fallback")
        self.assertIn("incident", explanation.why_risky.lower())
