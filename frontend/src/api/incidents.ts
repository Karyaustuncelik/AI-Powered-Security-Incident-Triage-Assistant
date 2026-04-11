// Incident endpoint'leri için küçük yardımcı fonksiyonlar.

import { apiGet } from './client'
import type {
  IncidentDetail,
  IncidentFilters,
  IncidentListItem,
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
