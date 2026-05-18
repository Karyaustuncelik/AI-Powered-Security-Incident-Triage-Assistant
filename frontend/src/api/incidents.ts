// Incident endpoint'leri için küçük yardımcı fonksiyonlar.

import { apiGet, apiPostJson } from './client'
import type {
  IncidentCopilotRequest,
  IncidentCopilotResponse,
  IncidentDetail,
  IncidentFilters,
  IncidentListItem,
  ResponsePlan,
} from '../types/incident'

// Filtre nesnesini query string'e çevir.
function buildQueryString(filters?: Partial<IncidentFilters>): string {
  if (!filters) {
    return ''
  }

  const params = new URLSearchParams()

  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value)
    }
  })

  const queryString = params.toString()
  return queryString ? `?${queryString}` : ''
}

// Tüm incident listesini al.
export function fetchIncidents(
  filters?: Partial<IncidentFilters>,
): Promise<IncidentListItem[]> {
  return apiGet<IncidentListItem[]>(`/incidents${buildQueryString(filters)}`)
}

// Tek bir incident detayını al.
export function fetchIncidentDetail(incidentId: string): Promise<IncidentDetail> {
  return apiGet<IncidentDetail>(`/incidents/${incidentId}`)
}

// Benzer incident'ları al (aynı actor veya entity).
export function fetchRelatedIncidents(incidentId: string): Promise<IncidentListItem[]> {
  return apiGet<IncidentListItem[]>(`/incidents/${incidentId}/related`)
}

// Deterministik response plan üret.
export function generateResponsePlan(incidentId: string): Promise<ResponsePlan> {
  return apiGet<ResponsePlan>(`/incidents/${incidentId}/response-plan`)
}

// Curated incident için copilot sohbeti başlat.
export function chatAboutIncident(
  incidentId: string,
  payload: IncidentCopilotRequest,
): Promise<IncidentCopilotResponse> {
  return apiPostJson<IncidentCopilotResponse, IncidentCopilotRequest>(
    `/incidents/${incidentId}/chat`,
    payload,
  )
}
