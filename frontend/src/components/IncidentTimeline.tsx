// Vertical timeline visualisation for an incident — parses source event
// samples and technical facts into chronologically-ordered nodes.

import type { IncidentDetail } from "../types/incident";

type Props = {
  incident: IncidentDetail;
};

// ---------- Helpers ----------

type TimelineNode = {
  timestamp: string | null;
  description: string;
  kind: "event" | "fact";
};

/**
 * Attempt to parse a source_event_sample line.
 * Expected format: "2026-05-13T10:15:00 | user@example.com | Failed login from 203.0.113.42"
 * Returns { timestamp, description } or null if the line is empty.
 */
function parseEventSample(raw: string): TimelineNode | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;

  const parts = trimmed.split("|").map((s) => s.trim());
  if (parts.length >= 2) {
    // First segment might be a timestamp
    const maybeDateStr = parts[0];
    const date = new Date(maybeDateStr);
    const isValidDate = !isNaN(date.getTime());

    return {
      timestamp: isValidDate ? maybeDateStr : null,
      description: isValidDate ? parts.slice(1).join(" — ") : trimmed,
      kind: "event",
    };
  }

  return { timestamp: null, description: trimmed, kind: "event" };
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}

// ---------- Main component ----------

export function IncidentTimeline({ incident }: Props) {
  // Build ordered list of timeline nodes.
  const nodes: TimelineNode[] = [];

  // Incident timestamp as the anchor node.
  nodes.push({
    timestamp: incident.timestamp,
    description: `Incident detected — ${incident.event_type}`,
    kind: "event",
  });

  // Source event samples.
  for (const sample of incident.source_event_samples) {
    const parsed = parseEventSample(sample);
    if (parsed) nodes.push(parsed);
  }

  // Technical facts as supplementary nodes.
  for (const fact of incident.technical_facts) {
    nodes.push({
      timestamp: null,
      description: `${fact.label}: ${fact.value}`,
      kind: "fact",
    });
  }

  return (
    <div className="incident-timeline">
      <h4 className="timeline-heading">Event Timeline</h4>

      <div className="timeline-track">
        {nodes.map((node, idx) => (
          <div className="timeline-node" key={idx} data-kind={node.kind}>
            <div className="timeline-dot" />
            <div className="timeline-content">
              {node.timestamp && (
                <span className="timeline-timestamp">
                  {formatTimestamp(node.timestamp)}
                </span>
              )}
              <span className="timeline-description">{node.description}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Detected indicators as colored tags */}
      {incident.detected_indicators.length > 0 && (
        <div className="timeline-indicators">
          <span className="timeline-indicators-label">
            Detected Indicators
          </span>
          <div className="timeline-indicator-tags">
            {incident.detected_indicators.map((indicator, idx) => (
              <span className="timeline-indicator-tag" key={idx}>
                {indicator}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
