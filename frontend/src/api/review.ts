import { apiPut } from './client'
import type { IncidentReview, IncidentReviewUpdatePayload } from '../types/incident'

type ReviewResponse = {
  incident_id: string
  review: IncidentReview
}

export async function saveIncidentReview(
  incidentId: string,
  payload: IncidentReviewUpdatePayload,
): Promise<IncidentReview> {
  const response = await apiPut<ReviewResponse, IncidentReviewUpdatePayload>(
    `/incidents/${incidentId}/review`,
    payload,
  )
  return response.review
}
