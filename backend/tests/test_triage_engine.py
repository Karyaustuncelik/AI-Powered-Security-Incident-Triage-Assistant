import unittest
from datetime import UTC, datetime

from app.models.domain import IncidentEventType, PriorityLevel, SeverityLevel
from app.models.domain import LoginTimeBucket, RawIncidentRecord
from app.services.triage_engine import TriageEngine


def build_record(**overrides: object) -> RawIncidentRecord:
    payload = {
        "incident_id": "INC-TEST-1",
        "timestamp": datetime(2026, 4, 10, 12, 0, tzinfo=UTC),
        "source_system": "okta",
        "affected_entity": "finance-data-lake",
        "actor_user": "m.chen",
        "actor_ip": "10.0.0.10",
        "actor_country": "US",
        "target_country": None,
        "event_type": IncidentEventType.multiple_failed_login_attempts,
        "failed_login_count": 0,
        "privilege_change_count": 0,
        "api_request_count": 0,
        "login_time_bucket": LoginTimeBucket.business_hours,
        "is_admin_action": False,
        "geo_distance_km": 0,
        "impossible_travel_flag": False,
        "after_hours_flag": False,
        "notes": None,
    }
    payload.update(overrides)
    return RawIncidentRecord.model_validate(payload)


class TriageEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = TriageEngine()

    def test_impossible_travel_incident_is_high_severity(self) -> None:
        record = build_record(
            event_type=IncidentEventType.impossible_travel_pattern,
            failed_login_count=3,
            geo_distance_km=10500,
            impossible_travel_flag=True,
            after_hours_flag=True,
            login_time_bucket=LoginTimeBucket.after_hours,
        )

        enriched = self.engine.enrich_incident(record)

        self.assertEqual(enriched.severity, SeverityLevel.high)
        self.assertIn("geo_anomaly", [item.value for item in enriched.detected_indicators])
        self.assertGreaterEqual(enriched.score, 55)

    def test_privilege_abuse_escalates_priority(self) -> None:
        record = build_record(
            event_type=IncidentEventType.unusual_privilege_escalation,
            privilege_change_count=6,
            is_admin_action=True,
            after_hours_flag=True,
            login_time_bucket=LoginTimeBucket.after_hours,
        )

        enriched = self.engine.enrich_incident(record)

        self.assertEqual(enriched.severity, SeverityLevel.critical)
        self.assertEqual(enriched.priority, PriorityLevel.immediate_attention)
        self.assertIn("privilege_abuse", [item.value for item in enriched.detected_indicators])
