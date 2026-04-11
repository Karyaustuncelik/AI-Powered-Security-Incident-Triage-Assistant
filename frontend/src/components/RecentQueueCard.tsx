import type { IncidentListItem } from '../types/incident'
import { formatLabel, formatTimestamp } from '../utils/format'

type RecentQueueCardProps = {
  incidents: IncidentListItem[]
  onSelect: (incidentId: string) => void
}

export function RecentQueueCard({
  incidents,
  onSelect,
}: RecentQueueCardProps) {
  return (
    <article className="panel">
      <div className="panel-header">
        <h2>Recent Analyst Queue</h2>
      </div>

      {incidents.length === 0 ? (
        <div className="empty-state">No recent incidents match the current filters.</div>
      ) : (
        <div className="recent-list">
          {incidents.map((incident) => (
            <button
              key={incident.incident_id}
              className="recent-item"
              onClick={() => onSelect(incident.incident_id)}
              type="button"
            >
              <div className="recent-copy">
                <span>{incident.incident_id}</span>
                <strong>{formatLabel(incident.event_type)}</strong>
                <small>{formatTimestamp(incident.timestamp)}</small>
              </div>
              <span className={`priority ${incident.priority}`}>
                {formatLabel(incident.priority)}
              </span>
            </button>
          ))}
        </div>
      )}
    </article>
  )
}
