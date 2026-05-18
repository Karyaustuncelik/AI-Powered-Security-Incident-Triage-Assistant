/** API client for the AI Security Agent and Detection Engineering endpoints */

import { apiGet } from './client'
import type {
  AgentSSEEvent,
  AgentTool,
  AnomalyResponse,
  ComplianceResponse,
  SigmaResponse,
} from '../types/agent'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

// ── Agent ────────────────────────────────────────────────────────────────────

export async function listAgentTools(): Promise<AgentTool[]> {
  return apiGet<AgentTool[]>('/agent/tools')
}

/**
 * Run the AI security agent via SSE streaming.
 * Returns an async generator that yields parsed SSE events.
 */
export async function* runAgent(
  target: string,
  goal?: string,
): AsyncGenerator<AgentSSEEvent> {
  const response = await fetch(`${API_BASE}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target, goal }),
  })

  if (!response.ok) {
    throw new Error(`Agent request failed: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data:')) continue
      const jsonStr = trimmed.slice(5).trim()
      if (!jsonStr) continue
      try {
        yield JSON.parse(jsonStr) as AgentSSEEvent
      } catch {
        // skip malformed SSE frames
      }
    }
  }

  // Process remaining buffer
  if (buffer.trim().startsWith('data:')) {
    const jsonStr = buffer.trim().slice(5).trim()
    if (jsonStr) {
      try {
        yield JSON.parse(jsonStr) as AgentSSEEvent
      } catch {
        // skip
      }
    }
  }
}

// ── Detection Engineering ────────────────────────────────────────────────────

export async function generateSigmaRule(incidentId: string): Promise<SigmaResponse> {
  return apiGet<SigmaResponse>(`/detection/sigma/${incidentId}`)
}

export async function getComplianceMapping(incidentId: string): Promise<ComplianceResponse> {
  return apiGet<ComplianceResponse>(`/detection/compliance/${incidentId}`)
}

export async function getAnomalyReport(incidentId: string): Promise<AnomalyResponse> {
  return apiGet<AnomalyResponse>(`/detection/anomaly/${incidentId}`)
}
