import { useEffect, useState } from 'react'
import type { IncidentDetail } from '../types/incident'
import { formatLabel, formatTimestamp } from '../utils/format'

type IncidentDetailPanelProps = {
  incident: IncidentDetail | null
  isLoading: boolean
  showExplanationSection: boolean
  isGeneratingExplanation: boolean
  isSavingReview: boolean
  onGenerateExplanation: () => void
  onSaveReview: (payload: {
    review_status: string
    assigned_analyst: string
    review_notes: string
  }) => void
}

export function IncidentDetailPanel({
  incident,
  isLoading,
  showExplanationSection,
  isGeneratingExplanation,
  isSavingReview,
  onGenerateExplanation,
  onSaveReview,
}: IncidentDetailPanelProps) {
  const [reviewStatus, setReviewStatus] = useState('open')
  const [assignedAnalyst, setAssignedAnalyst] = useState('')
  const [reviewNotes, setReviewNotes] = useState('')

  useEffect(() => {
    setReviewStatus(incident?.review?.review_status ?? 'open')
    setAssignedAnalyst(incident?.review?.assigned_analyst ?? '')
    setReviewNotes(incident?.review?.review_notes ?? '')
  }, [incident])

  return (
    <aside className="panel">
      <div className="panel-header">
        <h2>Incident Detail</h2>
        {incident ? (
          <span className={`priority ${incident.priority}`}>
            {formatLabel(incident.priority)}
          </span>
        ) : null}
      </div>

      {isLoading ? <div className="empty-state">Incident detail is loading.</div> : null}

      {!isLoading && incident ? (
        <div className="detail-stack">
          <div className="detail-header">
            <div>
              <span className="detail-label">Selected Incident</span>
              <h3>{incident.incident_id}</h3>
            </div>
            <div className="meta-badges">
              <span className={`severity ${incident.severity}`}>
                {formatLabel(incident.severity)}
              </span>
              <span className="score-badge">Score {incident.score}</span>
              <span className={`review-status ${incident.review?.review_status ?? 'open'}`}>
                {formatLabel(incident.review?.review_status ?? 'open')}
              </span>
            </div>
          </div>

          <div>
            <span className="detail-label">Summary</span>
            <p>{incident.summary}</p>
          </div>

          <div className="fact-grid">
            <div className="fact-card">
              <span className="detail-label">Event Type</span>
              <p>{formatLabel(incident.event_type)}</p>
            </div>
            <div className="fact-card">
              <span className="detail-label">Entity</span>
              <p>{incident.affected_entity}</p>
            </div>
            <div className="fact-card">
              <span className="detail-label">Actor</span>
              <p>{incident.actor_user}</p>
            </div>
            <div className="fact-card">
              <span className="detail-label">Observed At</span>
              <p>{formatTimestamp(incident.timestamp)}</p>
            </div>
            <div className="fact-card">
              <span className="detail-label">Category</span>
              <p>{formatLabel(incident.category)}</p>
            </div>
            <div className="fact-card">
              <span className="detail-label">Source System</span>
              <p>{formatLabel(incident.source_system)}</p>
            </div>
            <div className="fact-card">
              <span className="detail-label">Source Events</span>
              <p>{incident.source_event_count}</p>
            </div>
          </div>

          <div>
            <span className="detail-label">Detected Indicators</span>
            <div className="indicator-list">
              {incident.detected_indicators.map((indicator) => (
                <span key={indicator} className="indicator-pill">
                  {formatLabel(indicator)}
                </span>
              ))}
            </div>
          </div>

          <div>
            <span className="detail-label">Technical Facts</span>
            <div className="fact-grid">
              {incident.technical_facts.map((fact) => (
                <div key={`${fact.label}-${fact.value}`} className="fact-card">
                  <span className="detail-label">{fact.label}</span>
                  <p>{fact.value}</p>
                </div>
              ))}
            </div>
          </div>

          <div>
            <span className="detail-label">Why Flagged</span>
            <div className="score-list">
              {incident.score_breakdown.map((item) => (
                <div key={`${item.indicator}-${item.reason}`} className="score-item">
                  <strong>
                    +{item.weight} {formatLabel(item.indicator)}
                  </strong>
                  <p>{item.reason}</p>
                </div>
              ))}
            </div>
          </div>

          <div>
            <span className="detail-label">Recommended Action</span>
            <p>{incident.suggested_action}</p>
          </div>

          {incident.source_event_count > 0 ? (
            <div>
              <span className="detail-label">Correlated Source Evidence</span>
              <div className="score-list">
                {incident.source_event_samples.map((sample) => (
                  <div key={sample} className="score-item source-sample">
                    <p>{sample}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <div>
            <div className="inline-header">
              <span className="detail-label">Analyst Review</span>
              {incident.review?.reviewed_at ? (
                <span className="inline-meta">
                  Updated {formatTimestamp(incident.review.reviewed_at)}
                </span>
              ) : null}
            </div>

            <div className="review-form">
              <label className="filter-field">
                <span className="filter-label">Review Status</span>
                <select
                  className="filter-input"
                  onChange={(event) => setReviewStatus(event.target.value)}
                  value={reviewStatus}
                >
                  <option value="open">Open</option>
                  <option value="in_progress">In Progress</option>
                  <option value="escalated">Escalated</option>
                  <option value="resolved">Resolved</option>
                  <option value="dismissed">Dismissed</option>
                </select>
              </label>

              <label className="filter-field">
                <span className="filter-label">Assigned Analyst</span>
                <input
                  className="filter-input"
                  onChange={(event) => setAssignedAnalyst(event.target.value)}
                  placeholder="security.analyst"
                  type="text"
                  value={assignedAnalyst}
                />
              </label>

              <label className="filter-field review-notes">
                <span className="filter-label">Review Notes</span>
                <textarea
                  className="filter-input review-textarea"
                  onChange={(event) => setReviewNotes(event.target.value)}
                  placeholder="Summarize findings, escalation context, or closure rationale."
                  value={reviewNotes}
                />
              </label>

              <button
                className="generate-button"
                disabled={isSavingReview}
                onClick={() =>
                  onSaveReview({
                    review_status: reviewStatus,
                    assigned_analyst: assignedAnalyst,
                    review_notes: reviewNotes,
                  })
                }
                type="button"
              >
                {isSavingReview ? 'Saving...' : 'Save Review'}
              </button>
            </div>
          </div>

          {showExplanationSection ? (
            <div>
              <div className="inline-header">
                <span className="detail-label">Explanation</span>
                <button
                  className="generate-button"
                  disabled={isGeneratingExplanation || isSavingReview}
                  onClick={onGenerateExplanation}
                  type="button"
                >
                  {isGeneratingExplanation ? 'Generating...' : 'Generate Explanation'}
                </button>
              </div>

              {incident.llm_explanation ? (
                <div className="explanation-card">
                  <p className="explanation-title">{incident.llm_explanation.short_explanation}</p>
                  <p>{incident.llm_explanation.why_risky}</p>
                  <p>
                    <strong>Next action:</strong> {incident.llm_explanation.recommended_action}
                  </p>
                  <span className="explanation-source">
                    Source: {formatLabel(incident.llm_explanation.source)}
                  </span>
                </div>
              ) : (
                <div className="empty-state">
                  Generate an explanation to see a human-readable incident summary.
                </div>
              )}
            </div>
          ) : (
            <div className="empty-state">
              Uploaded log sessions use the copilot panel below for follow-up analysis instead of
              the one-click explanation button.
            </div>
          )}
        </div>
      ) : null}

      {!isLoading && !incident ? (
        <div className="empty-state">
          Select an incident from the queue to inspect its triage result.
        </div>
      ) : null}
    </aside>
  )
}
