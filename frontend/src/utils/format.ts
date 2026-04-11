import type {
  DistributionBucket,
  IncidentFilters,
} from '../types/incident'

// `multiple_failed_login_attempts` gibi backend değerlerini okunur etikete çevir.
export function formatLabel(value: string): string {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

// ISO zaman damgasını kullanıcı için daha okunur hale getir.
export function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

// Dağılım listesindeki en yüksek sayılı öğeyi bul.
export function getTopBucket(
  buckets: DistributionBucket[],
): DistributionBucket | null {
  if (buckets.length === 0) {
    return null
  }

  return [...buckets].sort((left, right) => right.count - left.count)[0]
}

// Aktif filtreleri küçük etiketler halinde gösterebilmek için yardımcı yapı üret.
export function getActiveFilterEntries(filters: IncidentFilters): Array<{
  key: keyof IncidentFilters
  label: string
  value: string
}> {
  const labels: Record<keyof IncidentFilters, string> = {
    severity: 'Severity',
    priority: 'Priority',
    review_status: 'Review',
    event_type: 'Event Type',
    actor_user: 'Actor',
    affected_entity: 'Entity',
    search: 'Search',
    start_time: 'Start',
    end_time: 'End',
  }

  return Object.entries(filters)
    .filter(([, value]) => value)
    .map(([key, value]) => {
      const typedKey = key as keyof IncidentFilters
      const isDateFilter = typedKey === 'start_time' || typedKey === 'end_time'
      const isEnumLike =
        typedKey === 'severity' ||
        typedKey === 'priority' ||
        typedKey === 'review_status' ||
        typedKey === 'event_type'

      return {
        key: typedKey,
        label: labels[typedKey],
        value: isDateFilter
          ? formatTimestamp(value)
          : isEnumLike
            ? formatLabel(value)
            : value,
      }
    })
}
