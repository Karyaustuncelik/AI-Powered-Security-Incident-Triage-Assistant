import type { IncidentFilters } from '../types/incident'
import { getActiveFilterEntries } from '../utils/format'

type ActiveFilterChipsProps = {
  filters: IncidentFilters
  onRemoveFilter?: (name: keyof IncidentFilters) => void
}

export function ActiveFilterChips({ filters, onRemoveFilter }: ActiveFilterChipsProps) {
  const activeFilters = getActiveFilterEntries(filters)

  return (
    <section className="panel active-filters">
      <div className="panel-header compact">
        <h2>Active Filters</h2>
        <span className="status-pill subtle">
          {activeFilters.length === 0 ? 'No filters applied' : `${activeFilters.length} active`}
        </span>
      </div>

      {activeFilters.length === 0 ? (
        <div className="empty-state">The queue is currently showing the full incident dataset.</div>
      ) : (
        <div className="chip-list">
          {activeFilters.map((entry) => (
            <span key={entry.key} className="filter-chip">
              <strong>{entry.label}:</strong> {entry.value}
              {onRemoveFilter && (
                <button
                  className="chip-remove-btn"
                  onClick={() => onRemoveFilter(entry.key)}
                  type="button"
                  aria-label={`Remove ${entry.label} filter`}
                >
                  &times;
                </button>
              )}
            </span>
          ))}
        </div>
      )}
    </section>
  )
}
