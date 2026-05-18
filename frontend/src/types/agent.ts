/** Type definitions for the AI Security Agent */

export interface AgentTool {
  name: string
  description: string
  parameters: Record<string, unknown>
}

export interface SecurityFinding {
  title: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'
  category: string
  description: string
  recommendation: string
  evidence: string
}

export interface AgentSSEEvent {
  type: 'thought' | 'tool_call' | 'tool_result' | 'finding' | 'summary' | 'progress' | 'error' | 'done'
  content?: string
  tool?: string
  params?: Record<string, unknown>
  description?: string
  result?: Record<string, unknown>
  title?: string
  severity?: string
  category?: string
  recommendation?: string
  evidence?: string
  risk_level?: string
  finding_counts?: { critical: number; high: number; medium: number; low: number }
  duration?: number
  step?: number
  total?: number
}

export interface AgentStep {
  type: 'thought' | 'tool_call' | 'tool_result' | 'finding' | 'summary' | 'error'
  content: string
  timestamp: number
  tool?: string
  params?: Record<string, unknown>
  result?: Record<string, unknown>
  finding?: SecurityFinding
  summary?: {
    risk_level: string
    finding_counts: { critical: number; high: number; medium: number; low: number }
    duration: number
  }
}

// SIGMA / Detection Engineering types
export interface SigmaResponse {
  incident_id: string
  sigma_rule: string
  splunk_spl: string
  kql: string
}

export interface ComplianceMapping {
  control_id: string
  control_name: string
  description: string
  relevance: string
}

export interface ComplianceResponse {
  incident_id: string
  event_type: string
  severity: string
  frameworks: Record<string, ComplianceMapping[]>
}

export interface AnomalyScore {
  anomaly_type: string
  z_score: number
  observed_value: number
  baseline_mean: number
  baseline_std: number
  is_anomalous: boolean
  is_strong_anomaly: boolean
  description: string
}

export interface AnomalyResponse {
  incident_id: string
  user_id: string
  anomaly_scores: AnomalyScore[]
  composite_z_score: number
  risk_multiplier: number
  is_anomalous: boolean
  explanation: string
}
