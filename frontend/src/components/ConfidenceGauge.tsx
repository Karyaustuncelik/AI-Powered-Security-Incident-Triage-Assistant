// SVG semicircle gauge that visualises a risk / detection-confidence score
// from 0–100, colored by incident severity.

type Props = {
  score: number; // 0–100
  severity: string; // 'critical' | 'high' | 'medium' | 'low'
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#f85149",
  high: "#f0883e",
  medium: "#d29922",
  low: "#3fb950",
};

export function ConfidenceGauge({ score, severity }: Props) {
  const clampedScore = Math.max(0, Math.min(100, score));
  const color = SEVERITY_COLORS[severity.toLowerCase()] ?? "#8b949e";

  // Arc geometry — semicircle from left (10,60) to right (110,60),
  // center at (60,60), radius 50.
  const angle = (clampedScore / 100) * 180;
  const radians = (angle * Math.PI) / 180;
  const x = 60 + 50 * Math.cos(Math.PI - radians);
  const y = 60 - 50 * Math.sin(Math.PI - radians);
  const largeArc = angle > 90 ? 1 : 0;

  // Full background arc (180°).
  const bgPath = "M 10 60 A 50 50 0 1 1 110 60";

  // Filled arc proportional to score.  For score === 0 we skip the path.
  const fgPath =
    clampedScore > 0
      ? `M 10 60 A 50 50 0 ${largeArc} 1 ${x.toFixed(2)} ${y.toFixed(2)}`
      : "";

  return (
    <div className="confidence-gauge">
      <svg viewBox="0 0 120 70" width="100%" aria-label={`Risk score: ${clampedScore}`}>
        {/* Background arc */}
        <path
          d={bgPath}
          fill="none"
          stroke="#30363d"
          strokeWidth="8"
          strokeLinecap="round"
        />

        {/* Foreground arc */}
        {fgPath && (
          <path
            d={fgPath}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
          />
        )}

        {/* Score number */}
        <text
          x="60"
          y="58"
          textAnchor="middle"
          dominantBaseline="middle"
          fill={color}
          fontSize="18"
          fontWeight="700"
          fontFamily="inherit"
        >
          {clampedScore}
        </text>

        {/* Label */}
        <text
          x="60"
          y="68"
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#8b949e"
          fontSize="5"
          fontFamily="inherit"
        >
          Risk Score
        </text>
      </svg>
    </div>
  );
}
