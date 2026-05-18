// Incident response action toolbar — provides quick-access buttons for
// AI-assisted investigation, pentest workspace, copilot chat, response
// plan generation, and IR escalation.

import type { IncidentDetail, ResponsePlan } from "../types/incident";
import type { Route } from "./nebula/NavBar";

// ---------- Component props ----------

type Props = {
  incident: IncidentDetail;
  onNavigate: (route: Route) => void;
  onSetIncidentContext: (detail: IncidentDetail) => void;
  onEscalate: () => void;
  isGeneratingPlan: boolean;
  onGeneratePlan: () => void;
  responsePlan: ResponsePlan | null;
};

// ---------- Helpers ----------

const PRIORITY_COLORS: Record<string, string> = {
  critical: "#f85149",
  high: "#f0883e",
  medium: "#d29922",
  low: "#3fb950",
};

function PriorityBadge({ priority }: { priority: string }) {
  const color = PRIORITY_COLORS[priority.toLowerCase()] ?? "#8b949e";
  return (
    <span
      className="priority-badge"
      style={{
        background: `${color}22`,
        color,
        border: `1px solid ${color}55`,
        borderRadius: 6,
        padding: "2px 8px",
        fontSize: "0.75rem",
        fontWeight: 600,
        textTransform: "uppercase",
      }}
    >
      {priority}
    </span>
  );
}

// ---------- Main component ----------

export function SolveIncidentActions({
  incident,
  onNavigate,
  onSetIncidentContext,
  onEscalate,
  isGeneratingPlan,
  onGeneratePlan,
  responsePlan,
}: Props) {
  const navigateWithContext = (route: Route) => {
    onSetIncidentContext(incident);
    onNavigate(route);
  };

  return (
    <div className="solve-incident-actions">
      {/* Section title */}
      <div className="solve-actions-header">
        <h3 className="solve-actions-title">Incident Response Actions</h3>
        <span className="solve-actions-label">
          Quick actions for incident #{incident.incident_id}
        </span>
      </div>

      {/* Action grid — 2 columns, 5 buttons */}
      <div className="solve-actions-grid">
        <button
          className="solve-action-btn"
          data-variant="agent"
          onClick={() => navigateWithContext("/agent")}
        >
          <span className="solve-action-icon">🤖</span>
          <span className="solve-action-text">Investigate with AI Agent</span>
        </button>

        <button
          className="solve-action-btn"
          data-variant="pentest"
          onClick={() => navigateWithContext("/pentest")}
        >
          <span className="solve-action-icon">🔬</span>
          <span className="solve-action-text">Open in Pentest Workspace</span>
        </button>

        <button
          className="solve-action-btn"
          data-variant="copilot"
          onClick={() => navigateWithContext("/sirius")}
        >
          <span className="solve-action-icon">💬</span>
          <span className="solve-action-text">Open in SIRIUS Copilot</span>
        </button>

        <button
          className="solve-action-btn"
          data-variant="plan"
          onClick={onGeneratePlan}
          disabled={isGeneratingPlan}
        >
          <span className="solve-action-icon">📋</span>
          <span className="solve-action-text">
            {isGeneratingPlan
              ? "Generating Plan…"
              : "Auto-Generate Response Plan"}
          </span>
        </button>

        <button
          className="solve-action-btn"
          data-variant="escalate"
          onClick={onEscalate}
        >
          <span className="solve-action-icon">🚨</span>
          <span className="solve-action-text">Escalate to IR Workflow</span>
        </button>
      </div>

      {/* Response plan (shown only when generated) */}
      {responsePlan && (
        <div className="response-plan">
          <div className="response-plan-header">
            <h4>Response Plan</h4>
            <span className="response-plan-meta">
              Generated {responsePlan.generated_at} &middot;{" "}
              {responsePlan.severity.toUpperCase()} severity &middot;{" "}
              {responsePlan.event_type}
            </span>
          </div>

          <div className="response-plan-phases">
            {responsePlan.phases.map((step, idx) => (
              <div className="plan-phase-item" key={idx}>
                <div className="plan-phase-left">
                  <span className="plan-phase-number">{step.phase}</span>
                </div>
                <div className="plan-phase-body">
                  <div className="plan-phase-title-row">
                    <strong className="plan-phase-title">{step.title}</strong>
                    <PriorityBadge priority={step.priority} />
                  </div>
                  <p className="plan-phase-description">{step.description}</p>
                  <span className="plan-phase-time">
                    ⏱ {step.estimated_time}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
