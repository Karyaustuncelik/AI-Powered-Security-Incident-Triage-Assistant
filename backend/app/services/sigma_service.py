"""SIGMA Rule Generator — converts incident data into SIGMA detection rules.

SIGMA is a generic and open signature format that allows security professionals
to describe relevant log events in a straightforward manner. The generated rules
can be converted to Splunk SPL, Elasticsearch DSL, or any SIEM query language
using sigmac or pySigma.

This service demonstrates understanding of:
  - SIGMA rule specification v2
  - Detection engineering workflows
  - Log source abstraction
  - MITRE ATT&CK technique mapping
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from functools import lru_cache

from app.models.domain import (
    EnrichedIncident,
    IncidentEventType,
    IndicatorType,
    SeverityLevel,
)


# ── MITRE ATT&CK mapping ─────────────────────────────────────────────────────

EVENT_TO_MITRE: dict[IncidentEventType, list[dict[str, str]]] = {
    IncidentEventType.multiple_failed_login_attempts: [
        {"technique_id": "T1110", "technique_name": "Brute Force", "tactic": "Credential Access"},
        {"technique_id": "T1110.001", "technique_name": "Password Guessing", "tactic": "Credential Access"},
    ],
    IncidentEventType.repeated_authentication_failures: [
        {"technique_id": "T1110", "technique_name": "Brute Force", "tactic": "Credential Access"},
    ],
    IncidentEventType.risky_sign_in_pattern: [
        {"technique_id": "T1078", "technique_name": "Valid Accounts", "tactic": "Defense Evasion"},
        {"technique_id": "T1078.004", "technique_name": "Cloud Accounts", "tactic": "Initial Access"},
    ],
    IncidentEventType.abnormal_access_outside_hours: [
        {"technique_id": "T1078", "technique_name": "Valid Accounts", "tactic": "Persistence"},
    ],
    IncidentEventType.impossible_travel_pattern: [
        {"technique_id": "T1078", "technique_name": "Valid Accounts", "tactic": "Initial Access"},
        {"technique_id": "T1550", "technique_name": "Use Alternate Authentication Material", "tactic": "Lateral Movement"},
    ],
    IncidentEventType.unusual_privilege_escalation: [
        {"technique_id": "T1078.002", "technique_name": "Domain Accounts", "tactic": "Privilege Escalation"},
        {"technique_id": "T1098", "technique_name": "Account Manipulation", "tactic": "Persistence"},
    ],
    IncidentEventType.suspicious_api_activity: [
        {"technique_id": "T1106", "technique_name": "Native API", "tactic": "Execution"},
        {"technique_id": "T1059.009", "technique_name": "Cloud API", "tactic": "Execution"},
    ],
}

INDICATOR_TO_MITRE: dict[IndicatorType, dict[str, str]] = {
    IndicatorType.repeated_failed_logins: {"technique_id": "T1110", "technique_name": "Brute Force"},
    IndicatorType.geo_anomaly: {"technique_id": "T1078", "technique_name": "Valid Accounts"},
    IndicatorType.privilege_abuse: {"technique_id": "T1098", "technique_name": "Account Manipulation"},
    IndicatorType.unusual_time_access: {"technique_id": "T1078", "technique_name": "Valid Accounts"},
    IndicatorType.api_spike: {"technique_id": "T1106", "technique_name": "Native API"},
    IndicatorType.admin_after_hours_activity: {"technique_id": "T1098", "technique_name": "Account Manipulation"},
    IndicatorType.permission_change_surge: {"technique_id": "T1098.001", "technique_name": "Additional Cloud Credentials"},
    IndicatorType.risky_signin_context: {"technique_id": "T1078.004", "technique_name": "Cloud Accounts"},
}


# ── Log source mapping ───────────────────────────────────────────────────────

def _get_logsource(event_type: IncidentEventType) -> dict[str, str]:
    """Map event types to SIGMA log source categories."""
    if event_type in (
        IncidentEventType.multiple_failed_login_attempts,
        IncidentEventType.repeated_authentication_failures,
        IncidentEventType.risky_sign_in_pattern,
        IncidentEventType.impossible_travel_pattern,
    ):
        return {"category": "authentication", "product": "azure_signin", "service": "azure_ad"}
    if event_type == IncidentEventType.abnormal_access_outside_hours:
        return {"category": "authentication", "product": "okta", "service": "okta_system_log"}
    if event_type == IncidentEventType.unusual_privilege_escalation:
        return {"category": "iam", "product": "azure_ad", "service": "audit_log"}
    if event_type == IncidentEventType.suspicious_api_activity:
        return {"category": "proxy", "product": "cloud_api", "service": "api_gateway"}
    return {"category": "generic", "product": "security_event"}


# ── SIGMA rule generation ─────────────────────────────────────────────────────

def _severity_to_sigma_level(severity: SeverityLevel) -> str:
    return {
        SeverityLevel.critical: "critical",
        SeverityLevel.high: "high",
        SeverityLevel.medium: "medium",
        SeverityLevel.low: "low",
    }[severity]


def _build_detection_block(incident: EnrichedIncident) -> dict:
    """Build the SIGMA detection logic block."""
    event_type = incident.event_type
    selection: dict[str, object] = {}

    if event_type in (
        IncidentEventType.multiple_failed_login_attempts,
        IncidentEventType.repeated_authentication_failures,
    ):
        selection = {
            "selection_user": {"TargetUserName": incident.actor_user},
            "selection_status": {"Status": "Failure"},
            "condition": "selection_user and selection_status | count(TargetUserName) > 5",
            "timeframe": "10m",
        }
    elif event_type == IncidentEventType.risky_sign_in_pattern:
        selection = {
            "selection_user": {"TargetUserName": incident.actor_user},
            "selection_risk": {"RiskLevel|contains": ["high", "medium"]},
            "condition": "selection_user and selection_risk",
        }
    elif event_type == IncidentEventType.impossible_travel_pattern:
        selection = {
            "selection_user": {"TargetUserName": incident.actor_user},
            "filter_success": {"Status": "Success"},
            "condition": "selection_user and filter_success | near(TargetUserName, SourceGeoLocation) timespan=2h",
        }
    elif event_type == IncidentEventType.abnormal_access_outside_hours:
        selection = {
            "selection_user": {"TargetUserName": incident.actor_user},
            "selection_time": {"EventTime|time": "00:00..05:59,22:00..23:59"},
            "condition": "selection_user and selection_time",
        }
    elif event_type == IncidentEventType.unusual_privilege_escalation:
        selection = {
            "selection_action": {"Action|contains": ["Add member to role", "Set-MsolUserRole", "roleAssignments"]},
            "selection_target": {"TargetUserName": incident.affected_entity},
            "condition": "selection_action and selection_target",
        }
    elif event_type == IncidentEventType.suspicious_api_activity:
        selection = {
            "selection_user": {"SourceUserName": incident.actor_user},
            "condition": "selection_user | count(SourceUserName) > 1000",
            "timeframe": "1h",
        }
    else:
        selection = {
            "selection": {"TargetUserName": incident.actor_user},
            "condition": "selection",
        }

    return selection


class SigmaRuleGenerator:
    """Generate SIGMA detection rules from enriched incidents."""

    def generate(self, incident: EnrichedIncident) -> str:
        """Generate a complete SIGMA rule in YAML format."""
        rule_id = str(uuid.uuid4())
        today = datetime.now(UTC).strftime("%Y/%m/%d")
        logsource = _get_logsource(incident.event_type)
        detection = _build_detection_block(incident)
        level = _severity_to_sigma_level(incident.severity)
        mitre_techniques = EVENT_TO_MITRE.get(incident.event_type, [])

        # Build MITRE tags
        tags = []
        for tech in mitre_techniques:
            tag = f"attack.{tech['tactic'].lower().replace(' ', '_')}"
            if tag not in tags:
                tags.append(tag)
            tid = tech["technique_id"].lower().replace(".", "_")
            tags.append(f"attack.{tid}")

        # Build the YAML manually for precise formatting
        lines = [
            f"title: {incident.summary[:80]}",
            f"id: {rule_id}",
            f"status: experimental",
            f"description: |",
            f"    Auto-generated SIGMA rule for detecting {incident.event_type.value}.",
            f"    Triggered by triage score {incident.score}/100 ({incident.severity.value} severity).",
            f"    Indicators: {', '.join(i.value for i in incident.detected_indicators)}.",
            f"references:",
            f"    - https://attack.mitre.org/techniques/{mitre_techniques[0]['technique_id']}/" if mitre_techniques else "",
            f"author: SIRIUS AI Security Platform",
            f"date: {today}",
            f"tags:",
        ]
        for tag in tags:
            lines.append(f"    - {tag}")

        lines.append("logsource:")
        for k, v in logsource.items():
            lines.append(f"    {k}: {v}")

        lines.append("detection:")
        for key, value in detection.items():
            if isinstance(value, dict):
                lines.append(f"    {key}:")
                for dk, dv in value.items():
                    if isinstance(dv, list):
                        lines.append(f"        {dk}:")
                        for item in dv:
                            lines.append(f"            - '{item}'")
                    else:
                        lines.append(f"        {dk}: '{dv}'")
            elif key in ("condition", "timeframe"):
                lines.append(f"    {key}: {value}")

        lines.extend([
            f"falsepositives:",
            f"    - Legitimate administrative activity during maintenance windows",
            f"    - Automated service account operations",
            f"level: {level}",
        ])

        # Filter out empty lines from optional references
        return "\n".join(line for line in lines if line)

    def generate_splunk_spl(self, incident: EnrichedIncident) -> str:
        """Generate a Splunk SPL query equivalent."""
        et = incident.event_type
        user = incident.actor_user
        entity = incident.affected_entity

        if et in (IncidentEventType.multiple_failed_login_attempts, IncidentEventType.repeated_authentication_failures):
            return (
                f'index=auth sourcetype="azure:signin" OR sourcetype="okta:im"\n'
                f'| search user="{user}" status="Failure"\n'
                f'| stats count by user, src_ip, _time span=10m\n'
                f'| where count > 5\n'
                f'| sort -count'
            )
        elif et == IncidentEventType.impossible_travel_pattern:
            return (
                f'index=auth sourcetype="azure:signin"\n'
                f'| search user="{user}" status="Success"\n'
                f'| iplocation src_ip\n'
                f'| sort user, _time\n'
                f'| streamstats current=f last(lat) as prev_lat last(lon) as prev_lon last(_time) as prev_time by user\n'
                f'| eval distance=round(acos(sin(radians(lat))*sin(radians(prev_lat))+cos(radians(lat))*cos(radians(prev_lat))*cos(radians(lon-prev_lon)))*6371,2)\n'
                f'| eval time_diff_hours=round((_time-prev_time)/3600,2)\n'
                f'| eval speed_kmh=if(time_diff_hours>0,round(distance/time_diff_hours,0),0)\n'
                f'| where speed_kmh > 1000'
            )
        elif et == IncidentEventType.unusual_privilege_escalation:
            return (
                f'index=azure sourcetype="azure:audit"\n'
                f'| search Operation="Add member to role" OR Operation="Add eligible member to role"\n'
                f'| search Target.UserPrincipalName="{entity}"\n'
                f'| stats count values(ModifiedProperties.Role.DisplayName) as roles by Target.UserPrincipalName, InitiatedBy.User.UserPrincipalName\n'
                f'| where count >= 2'
            )
        elif et == IncidentEventType.suspicious_api_activity:
            return (
                f'index=proxy OR index=api_logs\n'
                f'| search user="{user}"\n'
                f'| timechart span=1h count by user\n'
                f'| where count > 1000'
            )
        elif et == IncidentEventType.abnormal_access_outside_hours:
            return (
                f'index=auth sourcetype="okta:im"\n'
                f'| search user="{user}"\n'
                f'| eval hour=strftime(_time, "%H")\n'
                f'| where hour >= 22 OR hour <= 5\n'
                f'| stats count by user, src_ip, hour'
            )
        else:
            return (
                f'index=security\n'
                f'| search user="{user}" OR target="{entity}"\n'
                f'| stats count by user, action, src_ip\n'
                f'| sort -count'
            )

    def generate_kql(self, incident: EnrichedIncident) -> str:
        """Generate a KQL (Kusto) query for Microsoft Sentinel."""
        et = incident.event_type
        user = incident.actor_user

        if et in (IncidentEventType.multiple_failed_login_attempts, IncidentEventType.repeated_authentication_failures):
            return (
                f'SigninLogs\n'
                f'| where TimeGenerated > ago(1h)\n'
                f'| where UserPrincipalName == "{user}"\n'
                f'| where ResultType != "0"\n'
                f'| summarize FailedAttempts=count(), DistinctIPs=dcount(IPAddress) by UserPrincipalName, bin(TimeGenerated, 10m)\n'
                f'| where FailedAttempts > 5'
            )
        elif et == IncidentEventType.impossible_travel_pattern:
            return (
                f'SigninLogs\n'
                f'| where UserPrincipalName == "{user}"\n'
                f'| where ResultType == "0"\n'
                f'| project TimeGenerated, UserPrincipalName, IPAddress, Location\n'
                f'| sort by UserPrincipalName, TimeGenerated asc\n'
                f'| extend PrevLocation = prev(Location), PrevTime = prev(TimeGenerated)\n'
                f'| extend TimeDiff = datetime_diff("hour", TimeGenerated, PrevTime)\n'
                f'| where Location != PrevLocation and TimeDiff < 2'
            )
        elif et == IncidentEventType.unusual_privilege_escalation:
            return (
                f'AuditLogs\n'
                f'| where OperationName has "Add member to role"\n'
                f'| extend Target = tostring(TargetResources[0].userPrincipalName)\n'
                f'| extend Role = tostring(TargetResources[0].modifiedProperties[1].newValue)\n'
                f'| where Target == "{user}"\n'
                f'| project TimeGenerated, InitiatedBy, Target, Role'
            )
        else:
            return (
                f'SecurityEvent\n'
                f'| where TimeGenerated > ago(24h)\n'
                f'| where Account has "{user}"\n'
                f'| summarize count() by Account, Activity, Computer\n'
                f'| sort by count_ desc'
            )


@lru_cache
def get_sigma_generator() -> SigmaRuleGenerator:
    return SigmaRuleGenerator()
