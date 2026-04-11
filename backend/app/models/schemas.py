# Tarih-saat alanı için import.
from datetime import datetime

# API'ye giden ve API'den dönen veri şekillerini tanımlamak için kullanıyoruz.
from pydantic import BaseModel, Field

# Domain katmanındaki tipleri yeniden kullanıyoruz.
from app.models.domain import (
    IncidentCategory,
    IncidentEventType,
    IncidentExplanation,
    IncidentReview,
    IndicatorType,
    PriorityLevel,
    ReviewStatus,
    ScoreContribution,
    SeverityLevel,
    TechnicalFact,
)


# Incident liste ekranında gereken kısa alanlar.
class IncidentListItem(BaseModel):
    incident_id: str
    timestamp: datetime
    event_type: IncidentEventType
    affected_entity: str
    severity: SeverityLevel
    priority: PriorityLevel
    review_status: ReviewStatus = ReviewStatus.open
    assigned_analyst: str | None = None


# Sağ panel detay görünümünde gereken tam veri.
class IncidentDetailResponse(BaseModel):
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
    review: IncidentReview | None = None
    llm_explanation: IncidentExplanation | None = None


# Grafiklerde kullanacağımız label-count çifti.
class DistributionBucket(BaseModel):
    label: str
    count: int = Field(..., ge=0)


# Dashboard istatistik cevabı.
class StatsResponse(BaseModel):
    total_incidents: int = Field(..., ge=0)
    high_or_critical_count: int = Field(..., ge=0)
    category_distribution: list[DistributionBucket] = Field(default_factory=list)
    priority_distribution: list[DistributionBucket] = Field(default_factory=list)
    review_status_distribution: list[DistributionBucket] = Field(default_factory=list)
    recent_incidents: list[IncidentListItem] = Field(default_factory=list)


# Filtre dropdown'larında göstereceğimiz seçenekler.
class FiltersOptionsResponse(BaseModel):
    severity_options: list[SeverityLevel] = Field(default_factory=list)
    priority_options: list[PriorityLevel] = Field(default_factory=list)
    review_status_options: list[ReviewStatus] = Field(default_factory=list)
    event_type_options: list[IncidentEventType] = Field(default_factory=list)
    category_options: list[IncidentCategory] = Field(default_factory=list)
    actor_options: list[str] = Field(default_factory=list)
    entity_options: list[str] = Field(default_factory=list)


# Açıklama endpoint'inin döneceği yapı.
class ExplanationResponse(BaseModel):
    incident_id: str
    explanation: IncidentExplanation


# Analyst review güncelleme isteği için body modeli.
class IncidentReviewUpdateRequest(BaseModel):
    review_status: ReviewStatus
    assigned_analyst: str | None = None
    review_notes: str | None = None


# Review endpoint'inin response modeli.
class IncidentReviewResponse(BaseModel):
    incident_id: str
    review: IncidentReview
