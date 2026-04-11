// Explanation endpoint'i için yardımcı fonksiyonlar.

import { apiPost } from './client'
import type { IncidentExplanation } from '../types/incident'

// Backend'den dönen explanation response şekli.
type ExplanationResponse = {
  incident_id: string
  explanation: IncidentExplanation
}

// Seçilen incident için explanation üret.
export async function generateExplanation(
  incidentId: string,
): Promise<IncidentExplanation> {
  const payload = await apiPost<ExplanationResponse>(`/explain/${incidentId}`)
  return payload.explanation
}
