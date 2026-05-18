/**
 * Detection Engineering Panel — SIGMA rules, compliance mapping, and anomaly detection.
 */

import { useState, useCallback, useEffect } from 'react'
import { generateSigmaRule, getComplianceMapping, getAnomalyReport } from '../api/agent'
import type { SigmaResponse, ComplianceResponse, AnomalyResponse } from '../types/agent'

type Tab = 'sigma' | 'compliance' | 'anomaly'

function SigmaTab({ data }: { data: SigmaResponse }) {
  const [view, setView] = useState<'sigma' | 'splunk' | 'kql'>('sigma')
  const [copied, setCopied] = useState(false)
  const content = view === 'sigma' ? data.sigma_rule : view === 'splunk' ? data.splunk_spl : data.kql
  function copy() {
    void navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div className="det-sigma">
      <div className="det-sigma-tabs">
        <button className={`det-sigma-tab ${view === 'sigma' ? 'active' : ''}`} onClick={() => setView('sigma')} type="button">SIGMA (YAML)</button>
        <button className={`det-sigma-tab ${view === 'splunk' ? 'active' : ''}`} onClick={() => setView('splunk')} type="button">Splunk SPL</button>
        <button className={`det-sigma-tab ${view === 'kql' ? 'active' : ''}`} onClick={() => setView('kql')} type="button">KQL (Sentinel)</button>
        <button className="det-copy-btn" onClick={copy} type="button">{copied ? '✓ Copied' : 'Copy'}</button>
      </div>
      <pre className="det-code">{content}</pre>
    </div>
  )
}

function ComplianceTab({ data }: { data: ComplianceResponse }) {
  return (
    <div className="det-compliance">
      {Object.entries(data.frameworks).map(([framework, controls]) => (
        <div key={framework} className="det-fw-group">
          <h4 className="det-fw-name">{framework}</h4>
          <div className="det-controls">
            {controls.map((ctrl, i) => (
              <div key={i} className={`det-control det-rel--${ctrl.relevance.toLowerCase()}`}>
                <div className="det-control-header">
                  <code className="det-ctrl-id">{ctrl.control_id}</code>
                  <span className="det-ctrl-name">{ctrl.control_name}</span>
                  <span className={`det-relevance det-rel-badge--${ctrl.relevance.toLowerCase()}`}>{ctrl.relevance}</span>
                </div>
                <p className="det-ctrl-desc">{ctrl.description}</p>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function AnomalyTab({ data }: { data: AnomalyResponse }) {
  return (
    <div className="det-anomaly">
      <div className={`det-anomaly-summary ${data.is_anomalous ? 'det-anomalous' : 'det-normal'}`}>
        <div className="det-anomaly-header">
          <span className="det-anomaly-badge">
            {data.is_anomalous ? '⚠ ANOMALY DETECTED' : '✓ WITHIN BASELINE'}
          </span>
          <span className="det-z-score">Composite z-score: <strong>{data.composite_z_score.toFixed(2)}</strong></span>
          {data.risk_multiplier > 1.0 && (
            <span className="det-multiplier">Risk ×{data.risk_multiplier.toFixed(2)}</span>
          )}
        </div>
        <p className="det-anomaly-explanation">{data.explanation}</p>
      </div>
      {data.anomaly_scores.length > 0 && (
        <div className="det-scores">
          {data.anomaly_scores.map((score, i) => (
            <div key={i} className={`det-score-card ${score.is_anomalous ? 'det-score-anomalous' : ''}`}>
              <div className="det-score-header">
                <span className="det-score-type">{score.anomaly_type.replace(/_/g, ' ')}</span>
                <span className={`det-score-z ${score.is_strong_anomaly ? 'det-z-strong' : score.is_anomalous ? 'det-z-anomalous' : 'det-z-normal'}`}>
                  z = {score.z_score.toFixed(2)}
                </span>
              </div>
              <div className="det-score-bar">
                <div className="det-score-fill" style={{ width: `${Math.min(100, Math.abs(score.z_score) * 20)}%` }} />
                <div className="det-score-threshold" style={{ left: '40%' }} />
              </div>
              <p className="det-score-desc">{score.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function DetectionPanel({ incidentId }: { incidentId: string | null }) {
  const [tab, setTab] = useState<Tab>('sigma')
  const [sigmaData, setSigmaData] = useState<SigmaResponse | null>(null)
  const [complianceData, setComplianceData] = useState<ComplianceResponse | null>(null)
  const [anomalyData, setAnomalyData] = useState<AnomalyResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loadedId, setLoadedId] = useState<string | null>(null)
  const [loadedTab, setLoadedTab] = useState<Tab | null>(null)

  // Reset when incident changes — safe in useEffect
  useEffect(() => {
    setSigmaData(null)
    setComplianceData(null)
    setAnomalyData(null)
    setLoadedId(null)
    setLoadedTab(null)
    setError(null)
    setTab('sigma')
  }, [incidentId])

  const loadTab = useCallback(async (t: Tab, id: string) => {
    setLoading(true)
    setError(null)
    try {
      if (t === 'sigma') {
        const data = await generateSigmaRule(id)
        setSigmaData(data)
      } else if (t === 'compliance') {
        const data = await getComplianceMapping(id)
        setComplianceData(data)
      } else {
        const data = await getAnomalyReport(id)
        setAnomalyData(data)
      }
      setLoadedId(id)
      setLoadedTab(t)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load.')
    } finally {
      setLoading(false)
    }
  }, [])

  function handleTabSwitch(t: Tab) {
    setTab(t)
    if (incidentId) void loadTab(t, incidentId)
  }

  if (!incidentId) return null

  const isLoaded = loadedId === incidentId && loadedTab === tab

  return (
    <div className="det-panel glass-card">
      <div className="det-tabs">
        <button className={`det-tab ${tab === 'sigma' ? 'active' : ''}`} onClick={() => handleTabSwitch('sigma')} type="button">
          <span className="det-tab-icon">📐</span> SIGMA Rules
        </button>
        <button className={`det-tab ${tab === 'compliance' ? 'active' : ''}`} onClick={() => handleTabSwitch('compliance')} type="button">
          <span className="det-tab-icon">🛡</span> Compliance
        </button>
        <button className={`det-tab ${tab === 'anomaly' ? 'active' : ''}`} onClick={() => handleTabSwitch('anomaly')} type="button">
          <span className="det-tab-icon">📊</span> Anomaly
        </button>
      </div>

      {error && <div className="det-error">{error}</div>}
      {loading && <div className="det-loading"><span className="agent-spinner" /> Loading…</div>}

      {!loading && !isLoaded && (
        <div className="det-empty">
          <button
            className="btn btn-primary"
            onClick={() => { if (incidentId) void loadTab(tab, incidentId) }}
            type="button"
          >
            Load {tab === 'sigma' ? 'Detection Rules' : tab === 'compliance' ? 'Compliance Mapping' : 'Anomaly Analysis'}
          </button>
        </div>
      )}

      {!loading && tab === 'sigma' && sigmaData && isLoaded && <SigmaTab data={sigmaData} />}
      {!loading && tab === 'compliance' && complianceData && isLoaded && <ComplianceTab data={complianceData} />}
      {!loading && tab === 'anomaly' && anomalyData && isLoaded && <AnomalyTab data={anomalyData} />}
    </div>
  )
}
