import unittest
from datetime import UTC, datetime

from app.services.incidents_service import IncidentsService


class IncidentsServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = IncidentsService()

    def test_naive_datetime_filters_are_normalized(self) -> None:
        incidents = self.service.filter_incidents(
            actor_user="m.chen",
            start_time=datetime(2026, 4, 9, 0, 0),
            end_time=datetime(2026, 4, 10, 23, 59),
        )

        self.assertGreater(len(incidents), 0)
        for incident in incidents:
            self.assertEqual(incident.actor_user, "m.chen")
            self.assertGreaterEqual(
                incident.timestamp,
                datetime(2026, 4, 9, 0, 0, tzinfo=UTC),
            )

    def test_results_are_sorted_from_newest_to_oldest(self) -> None:
        incidents = self.service.filter_incidents()
        timestamps = [incident.timestamp for incident in incidents]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
