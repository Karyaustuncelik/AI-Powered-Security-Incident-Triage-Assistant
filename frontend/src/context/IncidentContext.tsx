/**
 * Cross-page incident context — allows any module to read the currently
 * selected incident from the dashboard without prop drilling.
 *
 * The context is populated by App.tsx when an incident is selected in the
 * dashboard, and consumed by AgentWorkspace, PentestWorkspace, and
 * NebulaCopilot to pre-fill inputs when navigating via "Solve Incident" actions.
 */

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import type { IncidentDetail, ScoreContribution } from '../types/incident'

export type IncidentContextPayload = {
  incidentId: string
  summary: string
  severity: string
  priority: string
  eventType: string
  category: string
  affectedEntity: string
  actorUser: string
  sourceSystem: string
  detectedIndicators: string[]
  score: number
  scoreBreakdown: ScoreContribution[]
  suggestedAction: string
  sourceEventSamples: string[]
  sourceEventCount: number
  timestamp: string
}

type IncidentContextValue = {
  activeIncident: IncidentContextPayload | null
  setActiveIncident: (payload: IncidentContextPayload | null) => void
  clearIncident: () => void
  /** Set from an IncidentDetail object directly */
  setFromDetail: (detail: IncidentDetail) => void
}

const IncidentContext = createContext<IncidentContextValue | null>(null)

export function IncidentContextProvider({ children }: { children: ReactNode }) {
  const [activeIncident, setActiveIncident] = useState<IncidentContextPayload | null>(() => {
    try {
      const stored = sessionStorage.getItem('sirius_active_incident')
      return stored ? (JSON.parse(stored) as IncidentContextPayload) : null
    } catch {
      return null
    }
  })

  // Persist to sessionStorage so context survives within-session navigations
  useEffect(() => {
    if (activeIncident) {
      sessionStorage.setItem('sirius_active_incident', JSON.stringify(activeIncident))
    } else {
      sessionStorage.removeItem('sirius_active_incident')
    }
  }, [activeIncident])

  const clearIncident = useCallback(() => setActiveIncident(null), [])

  const setFromDetail = useCallback((detail: IncidentDetail) => {
    setActiveIncident({
      incidentId: detail.incident_id,
      summary: detail.summary,
      severity: detail.severity,
      priority: detail.priority,
      eventType: detail.event_type,
      category: detail.category,
      affectedEntity: detail.affected_entity,
      actorUser: detail.actor_user,
      sourceSystem: detail.source_system,
      detectedIndicators: detail.detected_indicators,
      score: detail.score,
      scoreBreakdown: detail.score_breakdown,
      suggestedAction: detail.suggested_action,
      sourceEventSamples: detail.source_event_samples,
      sourceEventCount: detail.source_event_count,
      timestamp: detail.timestamp,
    })
  }, [])

  return (
    <IncidentContext.Provider value={{ activeIncident, setActiveIncident, clearIncident, setFromDetail }}>
      {children}
    </IncidentContext.Provider>
  )
}

export function useIncidentContext(): IncidentContextValue {
  const ctx = useContext(IncidentContext)
  if (!ctx) throw new Error('useIncidentContext must be used within IncidentContextProvider')
  return ctx
}
