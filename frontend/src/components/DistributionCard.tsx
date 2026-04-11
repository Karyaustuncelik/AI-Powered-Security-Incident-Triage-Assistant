import type { DistributionBucket } from '../types/incident'
import { formatLabel } from '../utils/format'

type DistributionCardProps = {
  title: string
  buckets: DistributionBucket[]
  isLoading?: boolean
}

export function DistributionCard({
  title,
  buckets,
  isLoading = false,
}: DistributionCardProps) {
  return (
    <article className="panel">
      <div className="panel-header">
        <h2>{title}</h2>
        <span className="status-pill">{isLoading ? 'Loading...' : 'Live'}</span>
      </div>

      {buckets.length === 0 ? (
        <div className="empty-state">No distribution data is available for the current filter set.</div>
      ) : (
        <div className="distribution-list">
          {buckets.map((bucket) => (
            <div key={bucket.label} className="distribution-row">
              <span>{formatLabel(bucket.label)}</span>
              <strong>{bucket.count}</strong>
            </div>
          ))}
        </div>
      )}
    </article>
  )
}
