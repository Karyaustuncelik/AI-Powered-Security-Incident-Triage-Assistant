import { apiGet, apiPostJson } from './client'
import type {
  FilterOptionsResponse,
  IncidentCopilotRequest,
  IncidentCopilotResponse,
  IncidentDetail,
  IncidentFilters,
  IncidentListItem,
  StatsResponse,
  UploadedLogPayload,
  UploadSession,
} from '../types/incident'

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

export function uploadLogs(payload: UploadedLogPayload): Promise<UploadSession> {
  return apiPostJson<UploadSession, UploadedLogPayload>('/uploads/logs', payload)
}

export function fetchUploadedIncidents(
  uploadId: string,
  filters?: Partial<IncidentFilters>,
): Promise<IncidentListItem[]> {
  return apiGet<IncidentListItem[]>(
    `/uploads/${uploadId}/incidents${buildQueryString(filters)}`,
  )
}

export function fetchUploadedIncidentDetail(
  uploadId: string,
  incidentId: string,
): Promise<IncidentDetail> {
  return apiGet<IncidentDetail>(`/uploads/${uploadId}/incidents/${incidentId}`)
}

export function fetchUploadedStats(
  uploadId: string,
  filters?: Partial<IncidentFilters>,
): Promise<StatsResponse> {
  return apiGet<StatsResponse>(`/uploads/${uploadId}/stats${buildQueryString(filters)}`)
}

export function fetchUploadedFilterOptions(
  uploadId: string,
): Promise<FilterOptionsResponse> {
  return apiGet<FilterOptionsResponse>(`/uploads/${uploadId}/filters/options`)
}

export function chatAboutUploadedIncident(
  uploadId: string,
  incidentId: string,
  payload: IncidentCopilotRequest,
): Promise<IncidentCopilotResponse> {
  return apiPostJson<IncidentCopilotResponse, IncidentCopilotRequest>(
    `/uploads/${uploadId}/incidents/${incidentId}/chat`,
    payload,
  )
}
