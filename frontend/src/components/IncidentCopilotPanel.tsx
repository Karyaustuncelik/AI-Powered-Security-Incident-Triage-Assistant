import { useEffect, useState } from 'react'
import type { IncidentCopilotMessage, IncidentDetail } from '../types/incident'

type IncidentCopilotPanelProps = {
  incident: IncidentDetail | null
  isSending: boolean
  messages: IncidentCopilotMessage[]
  modeLabel: string
  onSend: (question: string) => void | Promise<void>
}

export function IncidentCopilotPanel({
  incident,
  isSending,
  messages,
  modeLabel,
  onSend,
}: IncidentCopilotPanelProps) {
  const [draft, setDraft] = useState('')

  useEffect(() => {
    setDraft('')
  }, [incident?.incident_id])

  function handleSubmit() {
    const trimmedDraft = draft.trim()
    if (!trimmedDraft || !incident || isSending) {
      return
    }

    void onSend(trimmedDraft)
    setDraft('')
  }

  return (
    <section className="panel copilot-panel">
      <div className="panel-header">
        <div>
          <h2>Incident Copilot</h2>
          <p className="panel-copy">
            This chat stays grounded in the selected incident, its score breakdown, and the
            correlated evidence that created it.
          </p>
        </div>
        <span className="status-pill">{modeLabel}</span>
      </div>

      {!incident ? (
        <div className="empty-state">
          Select an incident first. Then you can ask why it was flagged, what evidence was used,
          or what next action makes sense.
        </div>
      ) : (
        <div className="copilot-stack">
          <div className="copilot-context">
            <span className="detail-label">Active Incident</span>
            <p>
              {incident.incident_id} for <strong>{incident.affected_entity}</strong>
            </p>
          </div>

          <div className="copilot-messages">
            {messages.length === 0 ? (
              <div className="empty-state">
                Try asking: "Why is this incident high severity?", "Which raw events created this
                case?", or "What should an analyst verify next?"
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}-${message.content.slice(0, 16)}`}
                  className={`chat-message ${message.role === 'user' ? 'user' : 'assistant'}`}
                >
                  <span className="detail-label">
                    {message.role === 'user' ? 'Analyst' : 'Copilot'}
                  </span>
                  <p>{message.content}</p>
                </div>
              ))
            )}
          </div>

          <div className="copilot-composer">
            <label className="filter-field">
              <span className="filter-label">Question</span>
              <textarea
                className="filter-input review-textarea"
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Ask about the incident, indicators, evidence, or recommended action..."
                value={draft}
              />
            </label>

            <button
              className="generate-button"
              disabled={!draft.trim() || isSending}
              onClick={handleSubmit}
              type="button"
            >
              {isSending ? 'Thinking...' : 'Ask Copilot'}
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
