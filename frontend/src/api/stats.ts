// Dashboard istatistiklerini almak için helper fonksiyon.

import { apiGet } from './client'
import type { IncidentFilters, StatsResponse } from '../types/incident'

// Filtre nesnesini stats endpoint'i için query string'e çevir.
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

// Dashboard özet verisini getir.
export function fetchStats(filters?: Partial<IncidentFilters>): Promise<StatsResponse> {
  return apiGet<StatsResponse>(`/stats${buildQueryString(filters)}`)
}
