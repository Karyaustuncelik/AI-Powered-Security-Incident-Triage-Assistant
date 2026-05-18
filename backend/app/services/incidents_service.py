# Bu dosya incident listeleme ve detay alma işini tek yerde toplar.

from datetime import datetime, timezone
from functools import lru_cache

from app.models.domain import (
    EnrichedIncident,
    IncidentEventType,
    PriorityLevel,
    ReviewStatus,
    SeverityLevel,
)
from app.models.schemas import (
    IncidentCopilotRequest,
    IncidentCopilotResponse,
    FiltersOptionsResponse,
    IncidentDetailResponse,
    IncidentListItem,
)
from app.services.copilot_service import get_incident_copilot_service
from app.services.explanation_service import get_explanation_service
from app.services.repository import get_incident_repository
from app.services.review_service import get_review_service
from app.services.triage_engine import get_triage_engine
from app.utils.datetime_utils import normalize_optional_datetime


# EnrichedIncident modelini liste ekranı için kısa modele çevir.
def to_list_item(incident: EnrichedIncident) -> IncidentListItem:
    return IncidentListItem(
        incident_id=incident.incident_id,
        timestamp=incident.timestamp,
        event_type=incident.event_type,
        affected_entity=incident.affected_entity,
        severity=incident.severity,
        priority=incident.priority,
        review_status=incident.review.review_status if incident.review else ReviewStatus.open,
        assigned_analyst=incident.review.assigned_analyst if incident.review else None,
    )


# EnrichedIncident modelini detay cevabına çevir.
def to_detail_response(incident: EnrichedIncident) -> IncidentDetailResponse:
    return IncidentDetailResponse(
        incident_id=incident.incident_id,
        timestamp=incident.timestamp,
        event_type=incident.event_type,
        category=incident.category,
        affected_entity=incident.affected_entity,
        actor_user=incident.actor_user,
        source_system=incident.source_system,
        summary=incident.summary,
        technical_facts=incident.technical_facts,
        detected_indicators=incident.detected_indicators,
        score_breakdown=incident.score_breakdown,
        score=incident.score,
        severity=incident.severity,
        priority=incident.priority,
        suggested_action=incident.suggested_action,
        source_event_count=incident.source_event_count,
        source_event_samples=incident.source_event_samples,
        review=incident.review,
        llm_explanation=incident.llm_explanation,
    )


# Incident verisini yükleyip triage engine ile zenginleştiren servis.
class IncidentsService:
    def __init__(self) -> None:
        self.copilot_service = get_incident_copilot_service()
        self.explanation_service = get_explanation_service()
        self.repository = get_incident_repository()
        self.review_service = get_review_service()
        self.triage_engine = get_triage_engine()

    # Tüm kayıtları zenginleştirip liste halinde döndür.
    def list_incidents(self) -> list[EnrichedIncident]:
        raw_records = self.repository.list_incidents()
        incidents = self.triage_engine.enrich_many(raw_records)
        return [self._attach_cached_explanation(incident) for incident in incidents]

    # Filtre parametrelerine göre incident listesini daralt.
    def filter_incidents(
        self,
        *,
        severity: SeverityLevel | None = None,
        priority: PriorityLevel | None = None,
        event_type: IncidentEventType | None = None,
        affected_entity: str | None = None,
        actor_user: str | None = None,
        review_status: str | None = None,
        search: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[EnrichedIncident]:
        incidents = self.list_incidents()
        filtered_incidents: list[EnrichedIncident] = []
        normalized_start_time = normalize_optional_datetime(start_time)
        normalized_end_time = normalize_optional_datetime(end_time)

        if (
            normalized_start_time is not None
            and normalized_end_time is not None
            and normalized_start_time > normalized_end_time
        ):
            normalized_start_time, normalized_end_time = (
                normalized_end_time,
                normalized_start_time,
            )

        normalized_entity = affected_entity.lower() if affected_entity else None
        normalized_actor = actor_user.lower() if actor_user else None
        normalized_search = search.lower() if search else None

        for incident in incidents:
            if severity and incident.severity != severity:
                continue
            if priority and incident.priority != priority:
                continue
            if event_type and incident.event_type != event_type:
                continue
            if normalized_entity and normalized_entity not in incident.affected_entity.lower():
                continue
            if normalized_actor and normalized_actor not in incident.actor_user.lower():
                continue
            if review_status and (
                incident.review is None or incident.review.review_status.value != review_status
            ):
                continue
            if normalized_start_time and incident.timestamp < normalized_start_time:
                continue
            if normalized_end_time and incident.timestamp > normalized_end_time:
                continue
            if normalized_search:
                searchable_parts = [
                    incident.incident_id,
                    incident.affected_entity,
                    incident.actor_user,
                    incident.event_type.value,
                    incident.summary,
                ]
                haystack = " ".join(searchable_parts).lower()
                if normalized_search not in haystack:
                    continue

            filtered_incidents.append(incident)

        return sorted(
            filtered_incidents,
            key=lambda incident: incident.timestamp,
            reverse=True,
        )

    # Tek incident'i bulup zenginleştir.
    def get_incident(self, incident_id: str) -> EnrichedIncident | None:
        raw_record = self.repository.get_incident(incident_id)
        if raw_record is None:
            return None
        incident = self.triage_engine.enrich_incident(raw_record)
        return self._attach_cached_explanation(incident)

    # Return enriched incident (used by detection engineering routes).
    def get_enriched_incident(self, incident_id: str) -> EnrichedIncident | None:
        return self.get_incident(incident_id)

    # Return the raw (unenriched) record for anomaly analysis.
    def get_raw_record(self, incident_id: str):
        return self.repository.get_incident(incident_id)

    def chat_about_incident(
        self,
        incident_id: str,
        payload: IncidentCopilotRequest,
    ) -> IncidentCopilotResponse | None:
        incident = self.get_incident(incident_id)
        if incident is None:
            return None
        return self.copilot_service.chat_about_incident(incident, payload)

    # Filtre dropdown'ları için seçenekleri çıkar.
    def get_filter_options(self) -> FiltersOptionsResponse:
        incidents = self.list_incidents()
        actor_options = sorted({incident.actor_user for incident in incidents})
        entity_options = sorted({incident.affected_entity for incident in incidents})

        return FiltersOptionsResponse(
            severity_options=list(SeverityLevel),
            priority_options=list(PriorityLevel),
            review_status_options=list(ReviewStatus),
            event_type_options=list(IncidentEventType),
            category_options=sorted(
                {incident.category for incident in incidents},
                key=lambda category: category.value,
            ),
            actor_options=actor_options,
            entity_options=entity_options,
        )

    # Incident tipine ve severity'sine göre deterministik response plan üret.
    def generate_response_plan(self, incident_id: str) -> dict | None:
        incident = self.get_incident(incident_id)
        if incident is None:
            return None

        event_type = incident.event_type
        severity = incident.severity

        playbooks: dict[IncidentEventType, list[dict]] = {
            IncidentEventType.multiple_failed_login_attempts: [
                {
                    "phase": "containment",
                    "title": "Lock affected account",
                    "description": "Temporarily lock the account to prevent further unauthorized access attempts.",
                    "priority": "high",
                    "estimated_time": "5 minutes",
                },
                {
                    "phase": "investigation",
                    "title": "Review authentication logs",
                    "description": "Examine authentication logs to identify the source IPs, timing patterns, and whether the attempts are part of a broader credential stuffing campaign.",
                    "priority": "high",
                    "estimated_time": "30 minutes",
                },
                {
                    "phase": "investigation",
                    "title": "Check for credential stuffing indicators",
                    "description": "Cross-reference failed login IPs against known botnet and proxy lists. Check if multiple accounts were targeted from the same source.",
                    "priority": "medium",
                    "estimated_time": "20 minutes",
                },
                {
                    "phase": "remediation",
                    "title": "Reset credentials",
                    "description": "Force a password reset for the affected account and any other accounts that share similar patterns of failed access.",
                    "priority": "high",
                    "estimated_time": "10 minutes",
                },
                {
                    "phase": "recovery",
                    "title": "Enable enhanced monitoring",
                    "description": "Set up additional alerting on the affected account and similar accounts. Consider enforcing MFA if not already enabled.",
                    "priority": "medium",
                    "estimated_time": "15 minutes",
                },
            ],
            IncidentEventType.repeated_authentication_failures: [
                {
                    "phase": "containment",
                    "title": "Throttle authentication attempts",
                    "description": "Apply rate limiting to the affected authentication endpoint to slow down brute-force attempts.",
                    "priority": "high",
                    "estimated_time": "10 minutes",
                },
                {
                    "phase": "investigation",
                    "title": "Analyze failure patterns",
                    "description": "Review the authentication failure logs to determine if this is a targeted attack on a specific account or a spray attack across multiple accounts.",
                    "priority": "high",
                    "estimated_time": "25 minutes",
                },
                {
                    "phase": "remediation",
                    "title": "Block malicious source IPs",
                    "description": "Add identified malicious source IPs to the blocklist at the firewall or WAF level.",
                    "priority": "high",
                    "estimated_time": "15 minutes",
                },
                {
                    "phase": "recovery",
                    "title": "Verify account integrity",
                    "description": "Confirm that no accounts were successfully compromised. Reset passwords for any accounts where successful login followed repeated failures.",
                    "priority": "medium",
                    "estimated_time": "20 minutes",
                },
            ],
            IncidentEventType.risky_sign_in_pattern: [
                {
                    "phase": "containment",
                    "title": "Flag session for verification",
                    "description": "Mark the risky session for additional verification without immediately disrupting the user.",
                    "priority": "medium",
                    "estimated_time": "5 minutes",
                },
                {
                    "phase": "investigation",
                    "title": "Correlate sign-in context",
                    "description": "Analyze the sign-in device, browser fingerprint, location, and time to determine the risk level of the session.",
                    "priority": "high",
                    "estimated_time": "20 minutes",
                },
                {
                    "phase": "remediation",
                    "title": "Enforce step-up authentication",
                    "description": "Require the user to complete an additional authentication factor to continue the session.",
                    "priority": "high",
                    "estimated_time": "10 minutes",
                },
                {
                    "phase": "recovery",
                    "title": "Update risk-based authentication policies",
                    "description": "Adjust sign-in risk policies to better detect similar patterns in the future.",
                    "priority": "low",
                    "estimated_time": "30 minutes",
                },
            ],
            IncidentEventType.abnormal_access_outside_hours: [
                {
                    "phase": "containment",
                    "title": "Monitor active session",
                    "description": "Place the after-hours session under heightened monitoring to capture all activity in real time.",
                    "priority": "medium",
                    "estimated_time": "5 minutes",
                },
                {
                    "phase": "investigation",
                    "title": "Verify with the user",
                    "description": "Contact the account owner through an out-of-band channel to confirm whether the after-hours access was intentional.",
                    "priority": "high",
                    "estimated_time": "15 minutes",
                },
                {
                    "phase": "remediation",
                    "title": "Revoke session if unauthorized",
                    "description": "If the user did not initiate the access, immediately revoke the session and reset credentials.",
                    "priority": "high",
                    "estimated_time": "10 minutes",
                },
                {
                    "phase": "recovery",
                    "title": "Review access policies",
                    "description": "Evaluate whether time-based access restrictions should be implemented for sensitive resources.",
                    "priority": "low",
                    "estimated_time": "25 minutes",
                },
            ],
            IncidentEventType.impossible_travel_pattern: [
                {
                    "phase": "containment",
                    "title": "Revoke active sessions",
                    "description": "Immediately revoke all active sessions for the affected user to prevent further unauthorized access.",
                    "priority": "high",
                    "estimated_time": "5 minutes",
                },
                {
                    "phase": "investigation",
                    "title": "Verify with the user",
                    "description": "Contact the user through an out-of-band channel to confirm their current location and whether they initiated both sessions.",
                    "priority": "high",
                    "estimated_time": "15 minutes",
                },
                {
                    "phase": "investigation",
                    "title": "Check for VPN or proxy usage",
                    "description": "Determine if the geographic anomaly can be explained by VPN, proxy, or corporate network routing.",
                    "priority": "medium",
                    "estimated_time": "20 minutes",
                },
                {
                    "phase": "remediation",
                    "title": "Review access logs comprehensively",
                    "description": "Audit all access activity for the affected account in the surrounding time window to identify any data access or changes made during the suspicious session.",
                    "priority": "high",
                    "estimated_time": "30 minutes",
                },
                {
                    "phase": "recovery",
                    "title": "Reset credentials and enforce MFA",
                    "description": "Force a credential reset and ensure multi-factor authentication is enabled and properly configured.",
                    "priority": "high",
                    "estimated_time": "10 minutes",
                },
            ],
            IncidentEventType.unusual_privilege_escalation: [
                {
                    "phase": "containment",
                    "title": "Revoke elevated privileges",
                    "description": "Immediately revert the privilege escalation to restore the user to their previous access level.",
                    "priority": "high",
                    "estimated_time": "5 minutes",
                },
                {
                    "phase": "investigation",
                    "title": "Audit permission changes",
                    "description": "Review the full history of permission changes to understand how and why the escalation occurred, and whether proper approval workflows were followed.",
                    "priority": "high",
                    "estimated_time": "25 minutes",
                },
                {
                    "phase": "investigation",
                    "title": "Review admin activity",
                    "description": "Examine what actions were performed with the elevated privileges to identify any unauthorized data access or configuration changes.",
                    "priority": "high",
                    "estimated_time": "30 minutes",
                },
                {
                    "phase": "remediation",
                    "title": "Strengthen privilege management",
                    "description": "Implement or reinforce just-in-time access policies and ensure all privilege escalations require multi-party approval.",
                    "priority": "medium",
                    "estimated_time": "45 minutes",
                },
                {
                    "phase": "recovery",
                    "title": "Audit all elevated accounts",
                    "description": "Perform a comprehensive review of all accounts with elevated privileges to ensure no other unauthorized escalations exist.",
                    "priority": "medium",
                    "estimated_time": "60 minutes",
                },
            ],
            IncidentEventType.suspicious_api_activity: [
                {
                    "phase": "containment",
                    "title": "Rate limit API keys",
                    "description": "Apply strict rate limits to the affected API keys to prevent further abuse while investigation proceeds.",
                    "priority": "high",
                    "estimated_time": "5 minutes",
                },
                {
                    "phase": "investigation",
                    "title": "Review API logs",
                    "description": "Analyze API call patterns, endpoints accessed, data volumes, and timing to understand the scope and intent of the suspicious activity.",
                    "priority": "high",
                    "estimated_time": "30 minutes",
                },
                {
                    "phase": "investigation",
                    "title": "Check for data exfiltration",
                    "description": "Review response payloads and data transfer volumes to determine if sensitive data was extracted through the API.",
                    "priority": "high",
                    "estimated_time": "25 minutes",
                },
                {
                    "phase": "remediation",
                    "title": "Rotate API keys",
                    "description": "Revoke the compromised API keys and issue new ones. Update all legitimate integrations with the new credentials.",
                    "priority": "high",
                    "estimated_time": "20 minutes",
                },
                {
                    "phase": "recovery",
                    "title": "Implement API security controls",
                    "description": "Deploy enhanced API monitoring, anomaly detection, and enforce stricter authentication requirements for sensitive endpoints.",
                    "priority": "medium",
                    "estimated_time": "45 minutes",
                },
            ],
        }

        steps = playbooks.get(event_type, [
            {
                "phase": "containment",
                "title": "Isolate affected systems",
                "description": "Identify and isolate systems related to this incident to prevent further impact.",
                "priority": "high",
                "estimated_time": "15 minutes",
            },
            {
                "phase": "investigation",
                "title": "Collect and analyze evidence",
                "description": "Gather relevant logs and artifacts to determine the scope and root cause of the incident.",
                "priority": "high",
                "estimated_time": "30 minutes",
            },
            {
                "phase": "remediation",
                "title": "Apply corrective actions",
                "description": "Implement fixes to address the root cause and close the attack vector.",
                "priority": "medium",
                "estimated_time": "30 minutes",
            },
            {
                "phase": "recovery",
                "title": "Restore and monitor",
                "description": "Return systems to normal operation and implement enhanced monitoring.",
                "priority": "medium",
                "estimated_time": "20 minutes",
            },
        ])

        # Adjust priority based on severity
        if severity in (SeverityLevel.critical, SeverityLevel.high):
            for step in steps:
                if step["priority"] == "low":
                    step["priority"] = "medium"
                elif step["priority"] == "medium":
                    step["priority"] = "high"

        return {
            "incident_id": incident_id,
            "severity": severity.value,
            "event_type": event_type.value,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "phases": steps,
        }

    # Cache'te explanation varsa incident modeline ekle.
    def _attach_cached_explanation(self, incident: EnrichedIncident) -> EnrichedIncident:
        cached_explanation = self.explanation_service.get_cached_explanation(incident.incident_id)
        if cached_explanation is not None:
            incident.llm_explanation = cached_explanation
        incident.review = self.review_service.get_review(incident.incident_id)
        return incident


@lru_cache
def get_incidents_service() -> IncidentsService:
    return IncidentsService()
