// Filtre seçeneklerini backend'den almak için helper fonksiyon.

import { apiGet } from './client'
import type { FilterOptionsResponse } from '../types/incident'

// Dropdown seçeneklerini getir.
export function fetchFilterOptions(): Promise<FilterOptionsResponse> {
  return apiGet<FilterOptionsResponse>('/filters/options')
}
