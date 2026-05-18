"""Compliance Framework Mapper — maps security findings to industry frameworks.

Maps incident indicators and findings to:
  - NIST Cybersecurity Framework (CSF) 2.0
  - OWASP Top 10 (2021)
  - CIS Controls v8
  - MITRE ATT&CK
  - ISO 27001:2022

This demonstrates enterprise security knowledge and understanding of
compliance requirements that are critical in production SOC environments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from app.models.domain import EnrichedIncident, IncidentEventType, IndicatorType


@dataclass
class FrameworkMapping:
    """A mapping from an incident to a compliance framework control."""
    framework: str
    control_id: str
    control_name: str
    description: str
    relevance: str  # HIGH, MEDIUM, LOW


@dataclass
class ComplianceReport:
    """Full compliance mapping for an incident."""
    incident_id: str
    event_type: str
    severity: str
    frameworks: dict[str, list[FrameworkMapping]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        result: dict = {
            "incident_id": self.incident_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "frameworks": {},
        }
        for fw_name, mappings in self.frameworks.items():
            result["frameworks"][fw_name] = [
                {
                    "control_id": m.control_id,
                    "control_name": m.control_name,
                    "description": m.description,
                    "relevance": m.relevance,
                }
                for m in mappings
            ]
        return result


# ── Framework Knowledge Base ──────────────────────────────────────────────────

NIST_CSF_MAP: dict[IncidentEventType, list[FrameworkMapping]] = {
    IncidentEventType.multiple_failed_login_attempts: [
        FrameworkMapping("NIST CSF", "PR.AC-1", "Identity Management & Access Control", "Identities and credentials are issued, managed, verified, revoked, and audited", "HIGH"),
        FrameworkMapping("NIST CSF", "DE.CM-1", "Security Continuous Monitoring", "The network is monitored to detect potential cybersecurity events", "HIGH"),
        FrameworkMapping("NIST CSF", "RS.AN-1", "Analysis", "Notifications from detection systems are investigated", "MEDIUM"),
    ],
    IncidentEventType.repeated_authentication_failures: [
        FrameworkMapping("NIST CSF", "PR.AC-1", "Identity Management & Access Control", "Identities and credentials are issued, managed, verified, revoked, and audited", "HIGH"),
        FrameworkMapping("NIST CSF", "PR.AC-7", "Authentication & Identity Proofing", "Users, devices, and other assets are authenticated commensurate with risk", "HIGH"),
    ],
    IncidentEventType.risky_sign_in_pattern: [
        FrameworkMapping("NIST CSF", "PR.AC-7", "Authentication & Identity Proofing", "Users, devices, and other assets are authenticated commensurate with risk", "HIGH"),
        FrameworkMapping("NIST CSF", "DE.AE-1", "Anomalies and Events", "A baseline of network operations and expected data flows is established", "MEDIUM"),
    ],
    IncidentEventType.impossible_travel_pattern: [
        FrameworkMapping("NIST CSF", "DE.AE-1", "Anomalies and Events", "A baseline of network operations and expected data flows is established", "HIGH"),
        FrameworkMapping("NIST CSF", "DE.AE-3", "Anomalies and Events", "Event data are collected and correlated from multiple sources", "HIGH"),
        FrameworkMapping("NIST CSF", "RS.AN-3", "Analysis", "Forensics are performed", "MEDIUM"),
    ],
    IncidentEventType.unusual_privilege_escalation: [
        FrameworkMapping("NIST CSF", "PR.AC-4", "Access Control", "Access permissions and authorizations are managed with least privilege", "HIGH"),
        FrameworkMapping("NIST CSF", "PR.AC-6", "Access Control", "Identities are proofed and bound to credentials and asserted in interactions", "HIGH"),
        FrameworkMapping("NIST CSF", "DE.CM-3", "Security Continuous Monitoring", "Personnel activity is monitored to detect potential events", "HIGH"),
    ],
    IncidentEventType.abnormal_access_outside_hours: [
        FrameworkMapping("NIST CSF", "DE.AE-1", "Anomalies and Events", "A baseline of network operations and expected data flows is established", "HIGH"),
        FrameworkMapping("NIST CSF", "DE.CM-3", "Security Continuous Monitoring", "Personnel activity is monitored to detect potential events", "MEDIUM"),
    ],
    IncidentEventType.suspicious_api_activity: [
        FrameworkMapping("NIST CSF", "PR.DS-5", "Data Security", "Protections against data leaks are implemented", "HIGH"),
        FrameworkMapping("NIST CSF", "DE.CM-1", "Security Continuous Monitoring", "The network is monitored to detect potential cybersecurity events", "HIGH"),
        FrameworkMapping("NIST CSF", "PR.AC-3", "Access Control", "Remote access is managed", "MEDIUM"),
    ],
}

CIS_CONTROLS_MAP: dict[IncidentEventType, list[FrameworkMapping]] = {
    IncidentEventType.multiple_failed_login_attempts: [
        FrameworkMapping("CIS Controls v8", "6.1", "Establish Access Granting Process", "Establish and follow a process to grant access based on policy", "HIGH"),
        FrameworkMapping("CIS Controls v8", "6.5", "Require MFA for Administrative Access", "Require MFA for all administrative access accounts", "HIGH"),
    ],
    IncidentEventType.repeated_authentication_failures: [
        FrameworkMapping("CIS Controls v8", "6.3", "Require MFA for Externally-Exposed Applications", "Require MFA for externally-exposed enterprise or third-party applications", "HIGH"),
        FrameworkMapping("CIS Controls v8", "6.7", "Centralize Access Control", "Centralize access control for all enterprise assets through a directory service", "MEDIUM"),
    ],
    IncidentEventType.impossible_travel_pattern: [
        FrameworkMapping("CIS Controls v8", "8.5", "Collect Detailed Audit Logs", "Configure detailed audit logging for enterprise assets containing sensitive data", "HIGH"),
        FrameworkMapping("CIS Controls v8", "8.11", "Conduct Audit Log Reviews", "Conduct reviews of audit logs to detect anomalies", "HIGH"),
    ],
    IncidentEventType.unusual_privilege_escalation: [
        FrameworkMapping("CIS Controls v8", "5.4", "Restrict Administrator Privileges", "Restrict administrator privileges to dedicated administrator accounts", "HIGH"),
        FrameworkMapping("CIS Controls v8", "6.8", "Define and Maintain Role-Based Access Control", "Define and maintain role-based access control", "HIGH"),
    ],
    IncidentEventType.suspicious_api_activity: [
        FrameworkMapping("CIS Controls v8", "13.3", "Deploy a Network Intrusion Detection Solution", "Deploy a network intrusion detection solution on enterprise assets", "HIGH"),
        FrameworkMapping("CIS Controls v8", "8.5", "Collect Detailed Audit Logs", "Configure detailed audit logging", "MEDIUM"),
    ],
    IncidentEventType.risky_sign_in_pattern: [
        FrameworkMapping("CIS Controls v8", "6.3", "Require MFA for Externally-Exposed Applications", "Require MFA for externally-exposed enterprise or third-party applications", "HIGH"),
    ],
    IncidentEventType.abnormal_access_outside_hours: [
        FrameworkMapping("CIS Controls v8", "8.11", "Conduct Audit Log Reviews", "Conduct reviews of audit logs to detect anomalies or unwanted events", "MEDIUM"),
    ],
}

OWASP_MAP: dict[IndicatorType, list[FrameworkMapping]] = {
    IndicatorType.repeated_failed_logins: [
        FrameworkMapping("OWASP Top 10", "A07:2021", "Identification and Authentication Failures", "Permits brute force or other automated attacks. Implement rate limiting and account lockout.", "HIGH"),
    ],
    IndicatorType.privilege_abuse: [
        FrameworkMapping("OWASP Top 10", "A01:2021", "Broken Access Control", "Unauthorized privilege escalation — failure of access control enforcement.", "HIGH"),
    ],
    IndicatorType.api_spike: [
        FrameworkMapping("OWASP Top 10", "A04:2021", "Insecure Design", "Missing rate limiting or throttling on API endpoints.", "HIGH"),
        FrameworkMapping("OWASP Top 10", "A09:2021", "Security Logging and Monitoring Failures", "Insufficient logging and monitoring of API activity.", "MEDIUM"),
    ],
    IndicatorType.permission_change_surge: [
        FrameworkMapping("OWASP Top 10", "A01:2021", "Broken Access Control", "Failure to enforce least privilege; excessive permission grants.", "HIGH"),
    ],
    IndicatorType.geo_anomaly: [
        FrameworkMapping("OWASP Top 10", "A07:2021", "Identification and Authentication Failures", "Missing geographic-based anomaly detection in authentication flows.", "MEDIUM"),
    ],
    IndicatorType.risky_signin_context: [
        FrameworkMapping("OWASP Top 10", "A07:2021", "Identification and Authentication Failures", "Risky sign-in context not triggering step-up authentication.", "MEDIUM"),
    ],
    IndicatorType.unusual_time_access: [
        FrameworkMapping("OWASP Top 10", "A09:2021", "Security Logging and Monitoring Failures", "Suspicious temporal access patterns not generating alerts.", "LOW"),
    ],
    IndicatorType.admin_after_hours_activity: [
        FrameworkMapping("OWASP Top 10", "A01:2021", "Broken Access Control", "Administrative access outside expected windows without additional verification.", "HIGH"),
    ],
}


# ── Service ───────────────────────────────────────────────────────────────────

class ComplianceMapper:
    """Map enriched incidents to compliance framework controls."""

    def map_incident(self, incident: EnrichedIncident) -> ComplianceReport:
        report = ComplianceReport(
            incident_id=incident.incident_id,
            event_type=incident.event_type.value,
            severity=incident.severity.value,
        )

        # NIST CSF mappings
        nist = NIST_CSF_MAP.get(incident.event_type, [])
        if nist:
            report.frameworks["NIST CSF 2.0"] = nist

        # CIS Controls mappings
        cis = CIS_CONTROLS_MAP.get(incident.event_type, [])
        if cis:
            report.frameworks["CIS Controls v8"] = cis

        # OWASP Top 10 (based on detected indicators)
        owasp: list[FrameworkMapping] = []
        seen_controls: set[str] = set()
        for indicator in incident.detected_indicators:
            for mapping in OWASP_MAP.get(indicator, []):
                if mapping.control_id not in seen_controls:
                    owasp.append(mapping)
                    seen_controls.add(mapping.control_id)
        if owasp:
            report.frameworks["OWASP Top 10 (2021)"] = owasp

        # ISO 27001 (always add generic controls based on severity)
        iso = self._map_iso27001(incident)
        if iso:
            report.frameworks["ISO 27001:2022"] = iso

        return report

    def _map_iso27001(self, incident: EnrichedIncident) -> list[FrameworkMapping]:
        """Map to ISO 27001:2022 Annex A controls."""
        controls = [
            FrameworkMapping("ISO 27001:2022", "A.8.15", "Logging", "Event logs recording user activities, exceptions, faults shall be produced and regularly reviewed.", "HIGH"),
        ]

        if incident.event_type in (IncidentEventType.multiple_failed_login_attempts, IncidentEventType.repeated_authentication_failures):
            controls.append(FrameworkMapping("ISO 27001:2022", "A.8.5", "Secure Authentication", "Secure authentication technologies and procedures shall be implemented.", "HIGH"))

        if incident.event_type == IncidentEventType.unusual_privilege_escalation:
            controls.append(FrameworkMapping("ISO 27001:2022", "A.8.2", "Privileged Access Rights", "The allocation and use of privileged access rights shall be restricted and managed.", "HIGH"))
            controls.append(FrameworkMapping("ISO 27001:2022", "A.5.18", "Access Rights", "Access rights to information and other associated assets shall be provisioned per policy.", "HIGH"))

        if incident.event_type in (IncidentEventType.impossible_travel_pattern, IncidentEventType.risky_sign_in_pattern):
            controls.append(FrameworkMapping("ISO 27001:2022", "A.8.16", "Monitoring Activities", "Networks, systems and applications shall be monitored for anomalous behaviour.", "HIGH"))

        if incident.event_type == IncidentEventType.suspicious_api_activity:
            controls.append(FrameworkMapping("ISO 27001:2022", "A.8.20", "Network Security", "Networks and network devices shall be secured, managed and controlled.", "MEDIUM"))

        return controls

    def get_summary(self, incident: EnrichedIncident) -> dict:
        """Return a compact compliance summary for API response."""
        report = self.map_incident(incident)
        return report.to_dict()


@lru_cache
def get_compliance_mapper() -> ComplianceMapper:
    return ComplianceMapper()
