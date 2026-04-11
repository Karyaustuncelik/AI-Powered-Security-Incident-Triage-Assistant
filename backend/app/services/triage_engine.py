# Bu dosya ham incident kaydını işleyip zenginleştirilmiş incident üretir.

# `lru_cache` aynı engine nesnesini tekrar kullanmak için.
from functools import lru_cache

# Domain katmanındaki veri tiplerini alıyoruz.
from app.models.domain import (
    EnrichedIncident,
    IncidentCategory,
    IncidentEventType,
    IndicatorType,
    RawIncidentRecord,
    ScoreContribution,
    TechnicalFact,
)
# Score'u severity ve priority'ye çevirecek yardımcı fonksiyonlar.
from app.utils.severity import score_to_severity, severity_to_priority


# Hangi event type hangi kategoriye daha yakın, onu burada tanımlıyoruz.
EVENT_CATEGORY_MAP = {
    IncidentEventType.multiple_failed_login_attempts: IncidentCategory.identity,
    IncidentEventType.repeated_authentication_failures: IncidentCategory.identity,
    IncidentEventType.risky_sign_in_pattern: IncidentCategory.identity,
    IncidentEventType.abnormal_access_outside_hours: IncidentCategory.access,
    IncidentEventType.impossible_travel_pattern: IncidentCategory.identity,
    IncidentEventType.unusual_privilege_escalation: IncidentCategory.privilege,
    IncidentEventType.suspicious_api_activity: IncidentCategory.api_abuse,
}


# Bazı olay tipleri doğası gereği daha yüksek başlangıç riski taşır.
EVENT_BASE_SCORE_MAP = {
    IncidentEventType.multiple_failed_login_attempts: 8,
    IncidentEventType.repeated_authentication_failures: 6,
    IncidentEventType.risky_sign_in_pattern: 10,
    IncidentEventType.abnormal_access_outside_hours: 12,
    IncidentEventType.impossible_travel_pattern: 24,
    IncidentEventType.unusual_privilege_escalation: 26,
    IncidentEventType.suspicious_api_activity: 18,
}


# Indicator eklerken tekrar eden kodu azaltmak için küçük yardımcı fonksiyon.
def add_indicator(
    contributions: list[ScoreContribution],
    indicators: list[IndicatorType],
    indicator: IndicatorType,
    weight: int,
    reason: str,
) -> None:
    # Aynı indicator iki kez eklenmesin.
    if indicator not in indicators:
        indicators.append(indicator)
    # Score breakdown listesine de neden eklendiğini yaz.
    contributions.append(
        ScoreContribution(
            indicator=indicator,
            weight=weight,
            reason=reason,
        )
    )


# Ham incident'ten teknik gerçekler listesi oluştur.
def build_technical_facts(record: RawIncidentRecord) -> list[TechnicalFact]:
    facts: list[TechnicalFact] = [
        TechnicalFact(label="Source system", value=record.source_system),
        TechnicalFact(label="Actor user", value=record.actor_user),
        TechnicalFact(label="Source IP", value=record.actor_ip),
    ]

    # Alan anlamlıysa facts listesine ekliyoruz.
    if record.failed_login_count:
        facts.append(
            TechnicalFact(label="Failed logins", value=str(record.failed_login_count))
        )
    if record.privilege_change_count:
        facts.append(
            TechnicalFact(
                label="Privilege changes",
                value=str(record.privilege_change_count),
            )
        )
    if record.api_request_count:
        facts.append(
            TechnicalFact(label="API requests", value=str(record.api_request_count))
        )
    if record.geo_distance_km:
        facts.append(
            TechnicalFact(label="Geo distance km", value=str(record.geo_distance_km))
        )

    facts.append(
        TechnicalFact(label="Time bucket", value=record.login_time_bucket.value)
    )
    facts.append(
        TechnicalFact(
            label="Admin action",
            value="yes" if record.is_admin_action else "no",
        )
    )
    return facts


# Tek cümlelik event summary üret.
def build_summary(record: RawIncidentRecord) -> str:
    event_labels = {
        IncidentEventType.multiple_failed_login_attempts: "Multiple failed login attempts detected",
        IncidentEventType.repeated_authentication_failures: "Repeated authentication failures detected",
        IncidentEventType.risky_sign_in_pattern: "Risky sign-in behavior detected",
        IncidentEventType.abnormal_access_outside_hours: "Access outside normal hours detected",
        IncidentEventType.impossible_travel_pattern: "Impossible travel pattern detected",
        IncidentEventType.unusual_privilege_escalation: "Unusual privilege escalation detected",
        IncidentEventType.suspicious_api_activity: "Suspicious API activity detected",
    }
    return f"{event_labels[record.event_type]} for {record.affected_entity}."


# Önerilen ilk aksiyonu event type'a göre seç.
def build_suggested_action(record: RawIncidentRecord) -> str:
    action_map = {
        IncidentEventType.multiple_failed_login_attempts: "Review sign-in logs, validate the source IP, and consider forcing a password reset.",
        IncidentEventType.repeated_authentication_failures: "Check whether the account is under attack or misconfigured, then confirm user activity.",
        IncidentEventType.risky_sign_in_pattern: "Validate session legitimacy and challenge the session with additional authentication.",
        IncidentEventType.abnormal_access_outside_hours: "Confirm whether the access was expected and review the affected user's recent activity.",
        IncidentEventType.impossible_travel_pattern: "Invalidate risky sessions and verify whether account credentials may be compromised.",
        IncidentEventType.unusual_privilege_escalation: "Review recent permission changes immediately and confirm change approval records.",
        IncidentEventType.suspicious_api_activity: "Inspect API logs, rotate keys if needed, and compare traffic against the normal baseline.",
    }
    return action_map[record.event_type]


# Asıl triage motoru.
class TriageEngine:
    # Tek bir ham incident'i alıp zenginleştirilmiş incident döndür.
    def enrich_incident(self, record: RawIncidentRecord) -> EnrichedIncident:
        indicators: list[IndicatorType] = []
        contributions: list[ScoreContribution] = []
        # Olay tipine göre başlangıç riski belirliyoruz.
        base_score = EVENT_BASE_SCORE_MAP[record.event_type]

        # Failed login'ler arttıkça risk artar.
        if record.failed_login_count >= 10:
            add_indicator(
                contributions,
                indicators,
                IndicatorType.repeated_failed_logins,
                30,
                "Failed login count is well above the normal threshold.",
            )
        elif record.failed_login_count >= 5:
            add_indicator(
                contributions,
                indicators,
                IndicatorType.repeated_failed_logins,
                18,
                "Repeated authentication failures were observed.",
            )

        # Coğrafi anormallik varsa yüksek risk katkısı.
        if record.impossible_travel_flag or record.geo_distance_km >= 6000:
            add_indicator(
                contributions,
                indicators,
                IndicatorType.geo_anomaly,
                34,
                "The location shift is too large for the observed time window.",
            )
        elif record.geo_distance_km >= 1000:
            add_indicator(
                contributions,
                indicators,
                IndicatorType.risky_signin_context,
                14,
                "The sign-in originated from an unusual geographic context.",
            )

        # Yetki değişiklikleri ciddi ağırlık taşır.
        if record.privilege_change_count >= 5:
            add_indicator(
                contributions,
                indicators,
                IndicatorType.privilege_abuse,
                40,
                "Privilege changes exceed the expected baseline for this entity.",
            )
        elif record.privilege_change_count >= 2:
            add_indicator(
                contributions,
                indicators,
                IndicatorType.permission_change_surge,
                24,
                "Permission changes are elevated compared with normal activity.",
            )

        # API isteği çok artmışsa şüpheli davranış.
        if record.api_request_count >= 2500:
            add_indicator(
                contributions,
                indicators,
                IndicatorType.api_spike,
                28,
                "API request volume deviates strongly from a normal baseline.",
            )
        elif record.api_request_count >= 1000:
            add_indicator(
                contributions,
                indicators,
                IndicatorType.api_spike,
                18,
                "API request volume is noticeably elevated.",
            )

        # Mesai dışı erişim de sinyal üretir.
        if record.after_hours_flag:
            add_indicator(
                contributions,
                indicators,
                IndicatorType.unusual_time_access,
                12,
                "Activity occurred outside normal operating hours.",
            )

        # Admin aksiyonu mesai dışındaysa ekstra risk.
        if record.after_hours_flag and record.is_admin_action:
            add_indicator(
                contributions,
                indicators,
                IndicatorType.admin_after_hours_activity,
                16,
                "Administrative activity outside normal hours requires urgent validation.",
            )

        # Toplam score: base score + bütün indicator ağırlıkları.
        score = min(100, base_score + sum(item.weight for item in contributions))
        severity = score_to_severity(score)
        priority = severity_to_priority(severity, indicators)

        return EnrichedIncident(
            incident_id=record.incident_id,
            timestamp=record.timestamp,
            event_type=record.event_type,
            category=EVENT_CATEGORY_MAP[record.event_type],
            affected_entity=record.affected_entity,
            actor_user=record.actor_user,
            source_system=record.source_system,
            summary=build_summary(record),
            technical_facts=build_technical_facts(record),
            detected_indicators=indicators,
            score_breakdown=contributions,
            score=score,
            severity=severity,
            priority=priority,
            suggested_action=build_suggested_action(record),
            llm_explanation=None,
        )

    # Liste halindeki kayıtları topluca zenginleştir.
    def enrich_many(self, records: list[RawIncidentRecord]) -> list[EnrichedIncident]:
        return [self.enrich_incident(record) for record in records]


# Engine'i tek noktadan alabilmek için helper.
@lru_cache
def get_triage_engine() -> TriageEngine:
    return TriageEngine()
