/**
 * Agent Workspace — Interactive UI for the AI Security Agent.
 *
 * Shows:
 * - Target input form
 * - Real-time streaming of agent thoughts, tool calls, and observations
 * - Security findings with severity badges
 * - Final assessment summary with risk level
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import { runAgent } from '../../api/agent'
import type { AgentSSEEvent, AgentStep, SecurityFinding } from '../../types/agent'

// ── Severity badge ──────────────────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: string }) {
  const cls = `agent-sev agent-sev--${severity.toLowerCase()}`
  return <span className={cls}>{severity}</span>
}

// ── Tool call card ──────────────────────────────────────────────────────────

function ToolCallCard({ step }: { step: AgentStep }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="agent-tool-call">
      <button className="agent-tool-header" onClick={() => setExpanded(!expanded)} type="button">
        <span className="agent-tool-icon">⚙</span>
        <span className="agent-tool-name">{step.tool}</span>
        <span className="agent-tool-toggle">{expanded ? '▾' : '▸'}</span>
      </button>
      {step.params && (
        <div className="agent-tool-params">
          {Object.entries(step.params).map(([k, v]) => (
            <span key={k} className="agent-tool-param">
              <span className="agent-tool-param-key">{k}:</span> {String(v)}
            </span>
          ))}
        </div>
      )}
      {expanded && step.result && (
        <pre className="agent-tool-result">{JSON.stringify(step.result, null, 2)}</pre>
      )}
    </div>
  )
}

// ── Finding card ────────────────────────────────────────────────────────────

function FindingCard({ finding }: { finding: SecurityFinding }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={`agent-finding agent-finding--${finding.severity.toLowerCase()}`}>
      <button className="agent-finding-header" onClick={() => setOpen(!open)} type="button">
        <SeverityBadge severity={finding.severity} />
        <span className="agent-finding-title">{finding.title}</span>
        <span className="agent-finding-cat">{finding.category}</span>
      </button>
      {open && (
        <div className="agent-finding-body">
          <p>{finding.description}</p>
          {finding.evidence && <p className="agent-finding-evidence"><strong>Evidence:</strong> {finding.evidence}</p>}
          <p className="agent-finding-rec"><strong>Recommendation:</strong> {finding.recommendation}</p>
        </div>
      )}
    </div>
  )
}

// ── Progress bar ────────────────────────────────────────────────────────────

function AgentProgress({ step, total }: { step: number; total: number }) {
  const pct = Math.round((step / total) * 100)
  return (
    <div className="agent-progress-wrap">
      <div className="agent-progress-bar">
        <div className="agent-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="agent-progress-label">Step {step}/{total} — {pct}%</span>
    </div>
  )
}

// ── Summary card ────────────────────────────────────────────────────────────

function SummaryCard({ summary, findings }: {
  summary: { content: string; risk_level: string; finding_counts: { critical: number; high: number; medium: number; low: number }; duration: number }
  findings: SecurityFinding[]
}) {
  const { risk_level, finding_counts: fc, duration } = summary
  return (
    <div className={`agent-summary agent-summary--${risk_level.toLowerCase()}`}>
      <div className="agent-summary-header">
        <h3>Assessment Complete</h3>
        <span className={`agent-risk-badge agent-risk--${risk_level.toLowerCase()}`}>{risk_level} RISK</span>
      </div>
      <div className="agent-summary-stats">
        <div className="agent-stat">
          <span className="agent-stat-num agent-stat--critical">{fc.critical}</span>
          <span className="agent-stat-label">Critical</span>
        </div>
        <div className="agent-stat">
          <span className="agent-stat-num agent-stat--high">{fc.high}</span>
          <span className="agent-stat-label">High</span>
        </div>
        <div className="agent-stat">
          <span className="agent-stat-num agent-stat--medium">{fc.medium}</span>
          <span className="agent-stat-label">Medium</span>
        </div>
        <div className="agent-stat">
          <span className="agent-stat-num agent-stat--low">{fc.low}</span>
          <span className="agent-stat-label">Low/Info</span>
        </div>
        <div className="agent-stat">
          <span className="agent-stat-num">{duration}s</span>
          <span className="agent-stat-label">Duration</span>
        </div>
      </div>
      {findings.length > 0 && (
        <div className="agent-findings-list">
          <h4>Findings ({findings.length})</h4>
          {findings.map((f, i) => <FindingCard key={i} finding={f} />)}
        </div>
      )}
    </div>
  )
}

// ── Main workspace ──────────────────────────────────────────────────────────

export function AgentWorkspace() {
  const [target, setTarget] = useState('')
  const [goal, setGoal] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [steps, setSteps] = useState<AgentStep[]>([])
  const [findings, setFindings] = useState<SecurityFinding[]>([])
  const [progress, setProgress] = useState<{ step: number; total: number } | null>(null)
  const [summaryData, setSummaryData] = useState<AgentStep['summary'] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const streamRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to latest step
  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight
    }
  }, [steps])

  const handleRun = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!target.trim() || isRunning) return

    setIsRunning(true)
    setSteps([])
    setFindings([])
    setProgress(null)
    setSummaryData(null)
    setError(null)

    try {
      for await (const event of runAgent(target.trim(), goal.trim() || undefined)) {
        const now = Date.now()

        switch (event.type) {
          case 'thought':
            setSteps(prev => [...prev, { type: 'thought', content: event.content ?? '', timestamp: now }])
            break

          case 'tool_call':
            setSteps(prev => [...prev, {
              type: 'tool_call',
              content: `Calling ${event.tool}`,
              timestamp: now,
              tool: event.tool,
              params: event.params,
            }])
            break

          case 'tool_result':
            setSteps(prev => [...prev, {
              type: 'tool_result',
              content: `Result from ${event.tool}`,
              timestamp: now,
              tool: event.tool,
              result: event.result,
            }])
            break

          case 'finding':
            {
              const finding: SecurityFinding = {
                title: event.title ?? '',
                severity: (event.severity ?? 'MEDIUM') as SecurityFinding['severity'],
                category: event.category ?? '',
                description: event.content ?? event.description ?? '',
                recommendation: event.recommendation ?? '',
                evidence: event.evidence ?? '',
              }
              setFindings(prev => [...prev, finding])
              setSteps(prev => [...prev, { type: 'finding', content: finding.title, timestamp: now, finding }])
            }
            break

          case 'summary':
            setSummaryData({
              risk_level: event.risk_level ?? 'UNKNOWN',
              finding_counts: event.finding_counts ?? { critical: 0, high: 0, medium: 0, low: 0 },
              duration: event.duration ?? 0,
            })
            setSteps(prev => [...prev, {
              type: 'summary',
              content: event.content ?? '',
              timestamp: now,
              summary: {
                risk_level: event.risk_level ?? 'UNKNOWN',
                finding_counts: event.finding_counts ?? { critical: 0, high: 0, medium: 0, low: 0 },
                duration: event.duration ?? 0,
              },
            }])
            break

          case 'progress':
            setProgress({ step: event.step ?? 0, total: event.total ?? 7 })
            break

          case 'error':
            setError(event.content ?? 'Unknown error')
            setSteps(prev => [...prev, { type: 'error', content: event.content ?? '', timestamp: now }])
            break

          case 'done':
            break
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Agent execution failed')
    } finally {
      setIsRunning(false)
    }
  }, [target, goal, isRunning])

  const handleReset = () => {
    setSteps([])
    setFindings([])
    setProgress(null)
    setSummaryData(null)
    setError(null)
  }

  // ── Render ──────────────────────────────────────────────────────────────
  return (
    <div className="agent-workspace">
      {/* Input form */}
      <div className="agent-input-card glass-card">
        <form className="agent-form" onSubmit={(e) => void handleRun(e)}>
          <label className="nb-form-field">
            <span className="nb-form-label">Target URL or Domain</span>
            <input
              className="nb-form-input"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="https://example.com"
              required
              disabled={isRunning}
              type="text"
            />
          </label>
          <label className="nb-form-field">
            <span className="nb-form-label">Assessment Goal (optional)</span>
            <input
              className="nb-form-input"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="e.g. Check for OWASP Top 10 vulnerabilities"
              disabled={isRunning}
              type="text"
            />
          </label>
          <div className="agent-form-actions">
            <button
              className="btn btn-primary agent-run-btn"
              disabled={isRunning || !target.trim()}
              type="submit"
            >
              {isRunning ? (
                <><span className="agent-spinner" />Agent Running…</>
              ) : '🤖 Launch Security Agent'}
            </button>
            {steps.length > 0 && !isRunning && (
              <button className="btn agent-reset-btn" onClick={handleReset} type="button">
                New Assessment
              </button>
            )}
          </div>
        </form>
        <div className="agent-tool-count">
          8 security tools available · ReAct reasoning loop · Real-time analysis
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {/* Progress */}
      {isRunning && progress && <AgentProgress step={progress.step} total={progress.total} />}

      {/* Stream feed */}
      {steps.length > 0 && (
        <div className="agent-stream" ref={streamRef}>
          {steps.map((step, i) => (
            <div key={i} className={`agent-event agent-event--${step.type}`}>
              {step.type === 'thought' && (
                <div className="agent-thought">
                  <span className="agent-event-icon">💭</span>
                  <span className="agent-thought-text">{step.content}</span>
                </div>
              )}
              {step.type === 'tool_call' && <ToolCallCard step={step} />}
              {step.type === 'tool_result' && (
                <div className="agent-observation">
                  <span className="agent-event-icon">📋</span>
                  <span className="agent-obs-label">Result from <strong>{step.tool}</strong></span>
                  {step.result && (
                    <details className="agent-obs-details">
                      <summary>View raw data</summary>
                      <pre>{JSON.stringify(step.result, null, 2)}</pre>
                    </details>
                  )}
                </div>
              )}
              {step.type === 'finding' && step.finding && <FindingCard finding={step.finding} />}
              {step.type === 'error' && (
                <div className="agent-error-event">
                  <span className="agent-event-icon">⚠</span>
                  <span>{step.content}</span>
                </div>
              )}
            </div>
          ))}
          {isRunning && (
            <div className="agent-thinking">
              <span className="agent-spinner" />
              <span>Agent is reasoning…</span>
            </div>
          )}
        </div>
      )}

      {/* Summary */}
      {summaryData && !isRunning && (
        <SummaryCard summary={{ ...summaryData, content: '' }} findings={findings} />
      )}
    </div>
  )
}
