import base64
import json
import unittest

from app.api.routes.uploads import (
    chat_about_uploaded_incident,
    get_uploaded_incident,
    get_uploaded_stats,
    list_uploaded_incidents,
    upload_logs,
)
from app.models.schemas import IncidentCopilotRequest, UploadLogRequest


def build_upload_payload() -> UploadLogRequest:
    records = []

    for minute in range(8):
        records.append(
            {
                "timestamp": f"2026-04-11T08:{minute:02d}:00Z",
                "user": "analyst.demo",
                "source_ip": "10.20.30.40",
                "country": "US",
                "event_type": "login",
                "status": "failure",
                "message": "authentication failed for analyst.demo",
                "host": "vpn-portal",
                "product": "okta",
            }
        )

    records.extend(
        [
            {
                "timestamp": "2026-04-11T09:10:00Z",
                "user": "analyst.demo",
                "source_ip": "10.20.30.40",
                "country": "US",
                "event_type": "login",
                "status": "success",
                "message": "successful sign-in for analyst.demo",
                "host": "vpn-portal",
                "product": "okta",
            },
            {
                "timestamp": "2026-04-11T11:00:00Z",
                "user": "analyst.demo",
                "source_ip": "44.55.66.77",
                "country": "SG",
                "event_type": "login",
                "status": "success",
                "message": "successful sign-in for analyst.demo from new region",
                "host": "vpn-portal",
                "product": "okta",
            },
        ]
    )

    encoded_content = base64.b64encode(json.dumps(records).encode("utf-8")).decode("utf-8")
    return UploadLogRequest(filename="okta_realistic_sample.json", content_base64=encoded_content)


class UploadRoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.session = upload_logs(build_upload_payload())

    def test_upload_creates_correlated_session(self) -> None:
        self.assertEqual(self.session.parser_format, "json")
        self.assertGreaterEqual(self.session.raw_event_count, 10)
        self.assertGreaterEqual(self.session.incident_count, 2)

    def test_uploaded_incidents_and_detail_are_available(self) -> None:
        incidents = list_uploaded_incidents(self.session.upload_id)

        self.assertGreaterEqual(len(incidents), 2)

        detail = get_uploaded_incident(self.session.upload_id, incidents[0].incident_id)

        self.assertEqual(detail.incident_id, incidents[0].incident_id)
        self.assertGreater(detail.source_event_count, 0)
        self.assertGreater(len(detail.source_event_samples), 0)

    def test_uploaded_stats_reflect_session_results(self) -> None:
        stats = get_uploaded_stats(self.session.upload_id)

        self.assertGreaterEqual(stats.total_incidents, 2)
        self.assertGreaterEqual(len(stats.recent_incidents), 1)

    def test_uploaded_incident_chat_returns_grounded_answer(self) -> None:
        incidents = list_uploaded_incidents(self.session.upload_id)
        response = chat_about_uploaded_incident(
            self.session.upload_id,
            incidents[0].incident_id,
            IncidentCopilotRequest(
                question="Why was this incident flagged?",
                history=[],
            ),
        )

        self.assertEqual(response.incident_id, incidents[0].incident_id)
        self.assertEqual(response.answer.role, "assistant")
        self.assertGreater(len(response.answer.content), 20)
