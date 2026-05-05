import { useEffect, useState } from 'react'
import type { UploadSession } from '../types/incident'
import { formatLabel, formatTimestamp } from '../utils/format'

type UploadPanelProps = {
  activeSession: UploadSession | null
  isUploading: boolean
  onResetToDemo: () => void
  onUpload: (file: File) => void | Promise<void>
}

export function UploadPanel({
  activeSession,
  isUploading,
  onResetToDemo,
  onUpload,
}: UploadPanelProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  useEffect(() => {
    if (!isUploading) {
      setSelectedFile(null)
    }
  }, [activeSession?.upload_id, isUploading])

  return (
    <section className="panel upload-panel">
      <div className="panel-header">
        <div>
          <h2>Log Upload Workspace</h2>
          <p className="panel-copy">
            Upload a CSV, JSON, JSONL, plain-text log, or gzip-compressed log file to build a
            fresh incident session from raw events.
          </p>
        </div>
        <span className={`status-pill ${activeSession ? '' : 'subtle'}`}>
          {activeSession ? 'Upload Session Active' : 'Demo Dataset Active'}
        </span>
      </div>

      <div className="upload-layout">
        <div className="upload-controls">
          <label className="filter-field">
            <span className="filter-label">Evidence File</span>
            <input
              accept=".csv,.json,.jsonl,.log,.txt,.gz"
              className="filter-input"
              key={activeSession?.upload_id ?? 'demo-dataset'}
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              type="file"
            />
          </label>

          <div className="upload-actions">
            <button
              className="generate-button"
              disabled={!selectedFile || isUploading}
              onClick={() => selectedFile && onUpload(selectedFile)}
              type="button"
            >
              {isUploading ? 'Analyzing...' : 'Upload and Correlate'}
            </button>

            <button
              className="reset-button"
              disabled={isUploading || !activeSession}
              onClick={onResetToDemo}
              type="button"
            >
              Return to Demo Dataset
            </button>
          </div>

          <div className="upload-hints">
            <span className="detail-label">Why this matters</span>
            <p>
              The app does not ask the LLM to guess the incident from scratch. It first parses
              raw logs, correlates suspicious patterns, and then lets the copilot explain the
              result in analyst language.
            </p>
          </div>
        </div>

        <div className="upload-summary">
          <span className="detail-label">Current Source</span>
          {activeSession ? (
            <div className="session-card">
              <div className="session-row">
                <strong>{activeSession.filename}</strong>
                <span className="status-pill subtle">{formatLabel(activeSession.parser_format)}</span>
              </div>
              <div className="session-grid">
                <div className="fact-card">
                  <span className="detail-label">Uploaded At</span>
                  <p>{formatTimestamp(activeSession.created_at)}</p>
                </div>
                <div className="fact-card">
                  <span className="detail-label">Raw Events</span>
                  <p>{activeSession.raw_event_count}</p>
                </div>
                <div className="fact-card">
                  <span className="detail-label">Normalized Events</span>
                  <p>{activeSession.normalized_event_count}</p>
                </div>
                <div className="fact-card">
                  <span className="detail-label">Correlated Incidents</span>
                  <p>{activeSession.incident_count}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              No uploaded log session yet. The dashboard is currently showing the curated demo
              dataset.
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
