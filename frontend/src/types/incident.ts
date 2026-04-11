// Bu dosya frontend'in backend'den beklediği veri şekillerini tanımlar.

// Liste ekranındaki tek incident satırı.
export type IncidentListItem = {
  incident_id: string
  timestamp: string
  event_type: string
  affected_entity: string
  severity: string
  priority: string
  review_status: string
  assigned_analyst: string | null
}

// Teknik gerçek kartları için küçük etiket-değer yapısı.
export type TechnicalFact = {
  label: string
  value: string
}

// Score breakdown içindeki tek bir katkı kaydı.
export type ScoreContribution = {
  indicator: string
  weight: number
  reason: string
}

// LLM veya fallback açıklaması.
export type IncidentExplanation = {
  short_explanation: string
  why_risky: string
  recommended_action: string
  source: string
}

export type IncidentReview = {
  incident_id: string
  review_status: string
  assigned_analyst: string | null
  review_notes: string | null
  reviewed_at: string | null
}

// Sağ panelde göstereceğimiz tam incident detayı.
export type IncidentDetail = {
  incident_id: string
  timestamp: string
  event_type: string
  category: string
  affected_entity: string
  actor_user: string
  source_system: string
  summary: string
  technical_facts: TechnicalFact[]
  detected_indicators: string[]
  score_breakdown: ScoreContribution[]
  score: number
  severity: string
  priority: string
  suggested_action: string
  review: IncidentReview | null
  llm_explanation: IncidentExplanation | null
}

// Grafik ve dağılım göstermek için label-count çifti.
export type DistributionBucket = {
  label: string
  count: number
}

// Dashboard özet cevabı.
export type StatsResponse = {
  total_incidents: number
  high_or_critical_count: number
  category_distribution: DistributionBucket[]
  priority_distribution: DistributionBucket[]
  review_status_distribution: DistributionBucket[]
  recent_incidents: IncidentListItem[]
}

// Filtre dropdown'larında kullanılacak backend seçenekleri.
export type FilterOptionsResponse = {
  severity_options: string[]
  priority_options: string[]
  review_status_options: string[]
  event_type_options: string[]
  category_options: string[]
  actor_options: string[]
  entity_options: string[]
}

// Frontend tarafında tuttuğumuz filtre state'i.
export type IncidentFilters = {
  severity: string
  priority: string
  review_status: string
  event_type: string
  actor_user: string
  affected_entity: string
  search: string
  start_time: string
  end_time: string
}

export type IncidentReviewUpdatePayload = {
  review_status: string
  assigned_analyst: string
  review_notes: string
}
