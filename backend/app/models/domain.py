# `datetime` tarih-saat tutmak için kullanılır.
from datetime import datetime
# `Enum` sabit seçenek listeleri oluşturmak için kullanılır.
from enum import Enum

# `BaseModel` veri modelleri tanımlamak içindir.
# `Field` ise alanlara kural vermemizi sağlar.
from pydantic import BaseModel, Field


# Incident'ın genel kategorisini tutar.
class IncidentCategory(str, Enum):
    # Kimlik/doğrulama odaklı olaylar.
    identity = "identity"
    # Erişim davranışıyla ilgili olaylar.
    access = "access"
    # API kullanım anormallikleri.
    api_abuse = "api_abuse"
    # Yetki yükseltme ve izin değişikliği olayları.
    privilege = "privilege"


# Desteklediğimiz olay tipleri.
class IncidentEventType(str, Enum):
    multiple_failed_login_attempts = "multiple_failed_login_attempts"
    repeated_authentication_failures = "repeated_authentication_failures"
    risky_sign_in_pattern = "risky_sign_in_pattern"
    abnormal_access_outside_hours = "abnormal_access_outside_hours"
    impossible_travel_pattern = "impossible_travel_pattern"
    unusual_privilege_escalation = "unusual_privilege_escalation"
    suspicious_api_activity = "suspicious_api_activity"


# Risk şiddeti seviyeleri.
class SeverityLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


# Analistin ne kadar hızlı bakması gerektiğini anlatan öncelik seviyeleri.
class PriorityLevel(str, Enum):
    investigate_later = "investigate_later"
    investigate_soon = "investigate_soon"
    immediate_attention = "immediate_attention"


# Tespit edilen şüpheli sinyal türleri.
class IndicatorType(str, Enum):
    repeated_failed_logins = "repeated_failed_logins"
    geo_anomaly = "geo_anomaly"
    privilege_abuse = "privilege_abuse"
    unusual_time_access = "unusual_time_access"
    api_spike = "api_spike"
    admin_after_hours_activity = "admin_after_hours_activity"
    permission_change_surge = "permission_change_surge"
    risky_signin_context = "risky_signin_context"


# Olayın günün hangi zamanında gerçekleştiğini kabaca anlatır.
class LoginTimeBucket(str, Enum):
    business_hours = "business_hours"
    after_hours = "after_hours"
    overnight = "overnight"


# Açıklamanın nereden geldiğini tutar.
class ExplanationSource(str, Enum):
    llm = "llm"
    fallback = "fallback"


# Analistin incident üzerinde hangi aşamada olduğunu tutar.
class ReviewStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    escalated = "escalated"
    resolved = "resolved"
    dismissed = "dismissed"


# Ham log satırı normalize edilince hangi güvenlik ailesine girdiğini tutar.
class NormalizedEventKind(str, Enum):
    authentication = "authentication"
    privilege_change = "privilege_change"
    api_activity = "api_activity"
    admin_activity = "admin_activity"
    generic_security = "generic_security"


# Score'a etki eden tek bir katkıyı temsil eder.
class ScoreContribution(BaseModel):
    # Hangi indicator bu puanı etkiledi?
    indicator: IndicatorType
    # `Field(..., ge=0)`:
    # `...` bu alan zorunlu demek.
    # `ge=0` ise 0'dan küçük olamaz demek.
    weight: int = Field(..., ge=0, description="How much this signal contributes to risk.")
    # İnsan okuyacağı açıklama cümlesi.
    reason: str = Field(..., min_length=5, description="Human-readable reason for the score.")


# UI'da göstereceğimiz teknik gerçeklerin kısa hali.
class TechnicalFact(BaseModel):
    # Etiket, örneğin "Failed logins"
    label: str = Field(..., min_length=2, description="Short name shown in the UI.")
    # Değer, örneğin "16 in 10 minutes"
    value: str = Field(..., min_length=1, description="Readable fact value for analysts.")


# LLM veya fallback tarafından oluşturulan açıklama.
class IncidentExplanation(BaseModel):
    short_explanation: str = Field(..., min_length=10)
    why_risky: str = Field(..., min_length=10)
    recommended_action: str = Field(..., min_length=10)
    source: ExplanationSource


# Analist tarafından girilen kalıcı review bilgisi.
class IncidentReview(BaseModel):
    incident_id: str = Field(..., min_length=4)
    review_status: ReviewStatus = ReviewStatus.open
    assigned_analyst: str | None = None
    review_notes: str | None = None
    reviewed_at: datetime | None = None


# Farkli log kaynaklarından gelen satırları ortak bir şekle çeviriyoruz.
class NormalizedLogEvent(BaseModel):
    event_id: str = Field(..., min_length=4)
    timestamp: datetime
    source_system: str = Field(..., min_length=2)
    actor_user: str = Field(..., min_length=1)
    affected_entity: str = Field(..., min_length=1)
    source_ip: str | None = None
    source_country: str | None = None
    target_country: str | None = None
    action: str = Field(..., min_length=1)
    status: str = Field(default="unknown", min_length=1)
    message: str = ""
    event_kind: NormalizedEventKind = NormalizedEventKind.generic_security
    is_admin_action: bool = False
    is_privilege_change: bool = False
    is_api_activity: bool = False
    raw_data: dict[str, str] = Field(default_factory=dict)


# Correlation aşaması tek bir incident üretirken onu destekleyen log örneklerini de taşır.
class CorrelatedIncidentRecord(BaseModel):
    incident: "RawIncidentRecord"
    source_event_count: int = Field(default=0, ge=0)
    source_event_samples: list[str] = Field(default_factory=list)


# Kullanıcının yüklediği log dosyasına ait session özeti.
class UploadSession(BaseModel):
    upload_id: str = Field(..., min_length=4)
    filename: str = Field(..., min_length=1)
    parser_format: str = Field(..., min_length=1)
    created_at: datetime
    raw_event_count: int = Field(default=0, ge=0)
    normalized_event_count: int = Field(default=0, ge=0)
    correlated_incidents: list[CorrelatedIncidentRecord] = Field(default_factory=list)


# Ham sayılara daha yakın olay kaydı.
class RawIncidentRecord(BaseModel):
    incident_id: str = Field(..., min_length=4)
    timestamp: datetime
    source_system: str = Field(..., min_length=2)
    affected_entity: str = Field(..., min_length=2)
    actor_user: str = Field(..., min_length=2)
    actor_ip: str = Field(..., min_length=7)
    actor_country: str = Field(..., min_length=2)
    target_country: str | None = None
    event_type: IncidentEventType
    failed_login_count: int = Field(default=0, ge=0)
    privilege_change_count: int = Field(default=0, ge=0)
    api_request_count: int = Field(default=0, ge=0)
    login_time_bucket: LoginTimeBucket = LoginTimeBucket.business_hours
    is_admin_action: bool = False
    geo_distance_km: int = Field(default=0, ge=0)
    impossible_travel_flag: bool = False
    after_hours_flag: bool = False
    notes: str | None = None


# İşlenmiş ve zenginleştirilmiş olay kaydı.
class EnrichedIncident(BaseModel):
    incident_id: str
    timestamp: datetime
    event_type: IncidentEventType
    category: IncidentCategory
    affected_entity: str
    actor_user: str
    source_system: str
    summary: str
    technical_facts: list[TechnicalFact] = Field(default_factory=list)
    detected_indicators: list[IndicatorType] = Field(default_factory=list)
    score_breakdown: list[ScoreContribution] = Field(default_factory=list)
    score: int = Field(..., ge=0, le=100)
    severity: SeverityLevel
    priority: PriorityLevel
    suggested_action: str
    source_event_count: int = Field(default=0, ge=0)
    source_event_samples: list[str] = Field(default_factory=list)
    review: IncidentReview | None = None
    llm_explanation: IncidentExplanation | None = None


class PentestStepStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class CVEFinding(BaseModel):
    cve_id: str
    description: str
    cvss_score: float | None = None
    severity: str | None = None
    published: str | None = None


class TopologyNodeType(str, Enum):
    attacker = "attacker"
    host = "host"
    service = "service"
    vulnerability = "vulnerability"
    data = "data"


class TopologyNodeStatus(str, Enum):
    normal = "normal"
    vulnerable = "vulnerable"
    compromised = "compromised"


class TopologyNode(BaseModel):
    id: str
    label: str
    node_type: TopologyNodeType
    status: TopologyNodeStatus = TopologyNodeStatus.normal
    detail: str | None = None


class TopologyEdge(BaseModel):
    source: str
    target: str
    label: str = ""
    edge_type: str = "normal"


class AttackGraph(BaseModel):
    nodes: list[TopologyNode] = Field(default_factory=list)
    edges: list[TopologyEdge] = Field(default_factory=list)


class PentestStep(BaseModel):
    index: int
    title: str
    description: str
    commands: list[str] = Field(default_factory=list)
    expected_outcome: str
    status: PentestStepStatus = PentestStepStatus.pending
    user_output: str | None = None
    llm_analysis: str | None = None
    cve_findings: list[CVEFinding] = Field(default_factory=list)


class PentestSession(BaseModel):
    session_id: str
    target: str
    description: str
    suspected_vuln: str | None = None
    goal: str | None = None
    steps: list[PentestStep] = Field(default_factory=list)
    current_step_index: int = 0
    status: str = "planning"
    created_at: datetime
    latex_report: str | None = None
    report_content: str | None = None
    report_format: str | None = None
    report_draft: str | None = None
    attack_graph: AttackGraph = Field(default_factory=AttackGraph)
