import type { IncidentListItem } from '../types/incident'
import { formatLabel, formatTimestamp } from '../utils/format'

type IncidentQueueTableProps = {
  incidents: IncidentListItem[]
  isLoading: boolean
  selectedIncidentId: string | null
  onSelect: (incidentId: string) => void
}

export function IncidentQueueTable({
  incidents,
  isLoading,
  selectedIncidentId,
  onSelect,
}: IncidentQueueTableProps) {
  return (
    <div className="panel panel-wide">
      <div className="panel-header">
        <h2>Incident Queue</h2>
        <span className="status-pill">
          {isLoading ? 'Loading...' : `${incidents.length} incidents`}
        </span>
      </div>

      <div className="placeholder-table">
        <div className="table-row header">
          <span>Incident ID</span>
          <span>Entity</span>
          <span>Event Type</span>
          <span>Observed At</span>
          <span>Severity</span>
          <span>Priority</span>
          <span>Review</span>
        </div>

        {isLoading ? (
          <div className="empty-state">Incident list is loading from the backend.</div>
        ) : null}

        {!isLoading && incidents.length === 0 ? (
          <div className="empty-state">No incidents were returned by the backend.</div>
        ) : null}

        {incidents.map((incident) => (
          <button
            key={incident.incident_id}
            className={`table-row clickable ${
              incident.incident_id === selectedIncidentId ? 'active' : ''
            }`}
            onClick={() => onSelect(incident.incident_id)}
            type="button"
          >
            <span>{incident.incident_id}</span>
            <span>{incident.affected_entity}</span>
            <span>{formatLabel(incident.event_type)}</span>
            <span>{formatTimestamp(incident.timestamp)}</span>
            <span className={`severity ${incident.severity}`}>
              {formatLabel(incident.severity)}
            </span>
            <span className={`priority ${incident.priority}`}>
              {formatLabel(incident.priority)}
            </span>
            <span className={`review-status ${incident.review_status}`}>
              {formatLabel(incident.review_status)}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
