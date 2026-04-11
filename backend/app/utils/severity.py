# Bu dosya sayısal score'u insanın okuyacağı severity ve priority değerlerine çevirir.

# Domain katmanındaki enum'ları kullanıyoruz.
from app.models.domain import IndicatorType, PriorityLevel, SeverityLevel


# Sayısal score'dan severity üret.
def score_to_severity(score: int) -> SeverityLevel:
    # 75 ve üstü en yüksek risk seviyesi.
    if score >= 75:
        return SeverityLevel.critical
    # 55 ve üstü yüksek risk.
    if score >= 55:
        return SeverityLevel.high
    # 30 ve üstü orta risk.
    if score >= 30:
        return SeverityLevel.medium
    # Geri kalan durumlar düşük risk.
    return SeverityLevel.low


# Severity ve indicator'lara bakarak analist önceliğini belirle.
def severity_to_priority(
    severity: SeverityLevel,
    indicators: list[IndicatorType],
) -> PriorityLevel:
    # Eğer risk kritikse doğrudan acil dikkat gerekir.
    if severity == SeverityLevel.critical:
        return PriorityLevel.immediate_attention

    # Privilege abuse veya admin-after-hours gibi indicator'lar varsa önceliği yükselt.
    escalation_indicators = {
        IndicatorType.privilege_abuse,
        IndicatorType.admin_after_hours_activity,
    }
    if any(indicator in escalation_indicators for indicator in indicators):
        return PriorityLevel.immediate_attention

    # High severity ise yakında incelenmeli.
    if severity == SeverityLevel.high:
        return PriorityLevel.investigate_soon

    # Medium severity olaylar daha sonra ama bekletmeden incelenebilir.
    if severity == SeverityLevel.medium:
        return PriorityLevel.investigate_later

    # Low severity için en düşük öncelik.
    return PriorityLevel.investigate_later

