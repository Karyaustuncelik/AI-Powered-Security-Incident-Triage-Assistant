import type { FilterOptionsResponse, IncidentFilters } from '../types/incident'
import { formatLabel } from '../utils/format'

type FilterBarProps = {
  filters: IncidentFilters
  filterOptions: FilterOptionsResponse | null
  onFilterChange: (name: keyof IncidentFilters, value: string) => void
  onReset: () => void
}

export function FilterBar({
  filters,
  filterOptions,
  onFilterChange,
  onReset,
}: FilterBarProps) {
  return (
    <section className="panel filter-panel">
      <div className="panel-header">
        <h2>Filter Bar</h2>
        <button className="reset-button" onClick={onReset} type="button">
          Clear Filters
        </button>
      </div>

      <div className="filter-grid">
        <label className="filter-field">
          <span className="filter-label">Search</span>
          <input
            className="filter-input"
            onChange={(event) => onFilterChange('search', event.target.value)}
            placeholder="incident id, user, summary..."
            type="text"
            value={filters.search}
          />
        </label>

        <label className="filter-field">
          <span className="filter-label">Severity</span>
          <select
            className="filter-input"
            onChange={(event) => onFilterChange('severity', event.target.value)}
            value={filters.severity}
          >
            <option value="">All severities</option>
            {(filterOptions?.severity_options ?? []).map((option) => (
              <option key={option} value={option}>
                {formatLabel(option)}
              </option>
            ))}
          </select>
        </label>

        <label className="filter-field">
          <span className="filter-label">Priority</span>
          <select
            className="filter-input"
            onChange={(event) => onFilterChange('priority', event.target.value)}
            value={filters.priority}
          >
            <option value="">All priorities</option>
            {(filterOptions?.priority_options ?? []).map((option) => (
              <option key={option} value={option}>
                {formatLabel(option)}
              </option>
            ))}
          </select>
        </label>

        <label className="filter-field">
          <span className="filter-label">Review Status</span>
          <select
            className="filter-input"
            onChange={(event) => onFilterChange('review_status', event.target.value)}
            value={filters.review_status}
          >
            <option value="">All review states</option>
            {(filterOptions?.review_status_options ?? []).map((option) => (
              <option key={option} value={option}>
                {formatLabel(option)}
              </option>
            ))}
          </select>
        </label>

        <label className="filter-field">
          <span className="filter-label">Event Type</span>
          <select
            className="filter-input"
            onChange={(event) => onFilterChange('event_type', event.target.value)}
            value={filters.event_type}
          >
            <option value="">All event types</option>
            {(filterOptions?.event_type_options ?? []).map((option) => (
              <option key={option} value={option}>
                {formatLabel(option)}
              </option>
            ))}
          </select>
        </label>

        <label className="filter-field">
          <span className="filter-label">Actor User</span>
          <input
            className="filter-input"
            list="actor-options"
            onChange={(event) => onFilterChange('actor_user', event.target.value)}
            placeholder="m.chen"
            type="text"
            value={filters.actor_user}
          />
          <datalist id="actor-options">
            {(filterOptions?.actor_options ?? []).map((option) => (
              <option key={option} value={option} />
            ))}
          </datalist>
        </label>

        <label className="filter-field">
          <span className="filter-label">Entity</span>
          <input
            className="filter-input"
            list="entity-options"
            onChange={(event) => onFilterChange('affected_entity', event.target.value)}
            placeholder="finance-data-lake"
            type="text"
            value={filters.affected_entity}
          />
          <datalist id="entity-options">
            {(filterOptions?.entity_options ?? []).map((option) => (
              <option key={option} value={option} />
            ))}
          </datalist>
        </label>

        <label className="filter-field">
          <span className="filter-label">Start Time</span>
          <input
            className="filter-input"
            onChange={(event) => onFilterChange('start_time', event.target.value)}
            type="datetime-local"
            value={filters.start_time}
          />
        </label>

        <label className="filter-field">
          <span className="filter-label">End Time</span>
          <input
            className="filter-input"
            onChange={(event) => onFilterChange('end_time', event.target.value)}
            type="datetime-local"
            value={filters.end_time}
          />
        </label>
      </div>
    </section>
  )
}
