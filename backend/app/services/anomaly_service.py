"""Statistical Anomaly Detection Engine.

Provides behavioral baseline analysis and z-score-based outlier detection
for security events. Works alongside the rule-based triage engine to surface
events that deviate from historical norms.

Mathematical approach:
  z = (x - mu) / sigma

Where:
  x     = observed metric value
  mu    = running mean for that user/entity
  sigma = running standard deviation

A z-score > 2.0 indicates an anomaly (95th percentile).
A z-score > 3.0 indicates a strong anomaly (99.7th percentile).

The engine maintains per-user behavioral baselines for:
  - Login frequency per time window
  - API request volume
  - Privilege change frequency
  - Geographic diversity (unique countries)
  - After-hours activity ratio
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from functools import lru_cache

from app.models.domain import EnrichedIncident, RawIncidentRecord


class AnomalyType(str, Enum):
    login_frequency = "login_frequency"
    api_volume = "api_volume"
    privilege_changes = "privilege_changes"
    geo_diversity = "geo_diversity"
    time_anomaly = "time_anomaly"
    composite = "composite"


@dataclass
class AnomalyScore:
    """A single anomaly detection result."""
    anomaly_type: AnomalyType
    z_score: float
    observed_value: float
    baseline_mean: float
    baseline_std: float
    is_anomalous: bool  # z > 2.0
    is_strong_anomaly: bool  # z > 3.0
    description: str

    def to_dict(self) -> dict:
        return {
            "anomaly_type": self.anomaly_type.value,
            "z_score": round(self.z_score, 2),
            "observed_value": round(self.observed_value, 2),
            "baseline_mean": round(self.baseline_mean, 2),
            "baseline_std": round(self.baseline_std, 2),
            "is_anomalous": self.is_anomalous,
            "is_strong_anomaly": self.is_strong_anomaly,
            "description": self.description,
        }


@dataclass
class UserBaseline:
    """Running statistics for a single user/entity."""
    user_id: str
    login_counts: list[float] = field(default_factory=list)
    api_counts: list[float] = field(default_factory=list)
    priv_counts: list[float] = field(default_factory=list)
    countries: list[set[str]] = field(default_factory=list)
    after_hours_ratios: list[float] = field(default_factory=list)
    last_updated: str = ""


@dataclass
class AnomalyReport:
    """Full anomaly analysis for an incident."""
    incident_id: str
    user_id: str
    anomaly_scores: list[AnomalyScore] = field(default_factory=list)
    composite_z_score: float = 0.0
    risk_multiplier: float = 1.0
    is_anomalous: bool = False
    explanation: str = ""

    def to_dict(self) -> dict:
        return {
            "incident_id": self.incident_id,
            "user_id": self.user_id,
            "anomaly_scores": [s.to_dict() for s in self.anomaly_scores],
            "composite_z_score": round(self.composite_z_score, 2),
            "risk_multiplier": round(self.risk_multiplier, 2),
            "is_anomalous": self.is_anomalous,
            "explanation": self.explanation,
        }


# ── Statistical helpers ───────────────────────────────────────────────────────

def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 1.0  # avoid division by zero; assume unit variance
    mu = _mean(values)
    variance = sum((x - mu) ** 2 for x in values) / (len(values) - 1)
    return max(math.sqrt(variance), 0.01)  # floor at 0.01


def _z_score(observed: float, mean: float, std: float) -> float:
    return (observed - mean) / std


# ── Simulated baseline data ──────────────────────────────────────────────────
# In production, these would come from a time-series database.
# For the portfolio project, we generate realistic baselines on the fly.

def _simulate_baseline(user: str, metric: str) -> tuple[float, float]:
    """Generate a plausible baseline (mean, std) based on user hash and metric.

    Uses deterministic pseudo-random values so the same user always gets the
    same baseline, making the demo reproducible.
    """
    seed = hash(f"{user}:{metric}") % 10000
    # Different metrics have different baseline characteristics
    baselines = {
        "login_frequency": (3.0 + (seed % 7), 1.5 + (seed % 3) * 0.5),
        "api_volume": (200 + (seed % 500), 80 + (seed % 100)),
        "privilege_changes": (0.3 + (seed % 3) * 0.1, 0.2 + (seed % 2) * 0.1),
        "geo_diversity": (1.2 + (seed % 3) * 0.3, 0.5 + (seed % 2) * 0.2),
        "time_anomaly": (0.15 + (seed % 10) * 0.02, 0.08 + (seed % 5) * 0.01),
    }
    return baselines.get(metric, (5.0, 2.0))


# ── Anomaly Detection Engine ─────────────────────────────────────────────────

class AnomalyDetector:
    """Detects statistical anomalies in security events."""

    def analyze(self, record: RawIncidentRecord) -> AnomalyReport:
        """Analyze a raw incident record for behavioral anomalies."""
        scores: list[AnomalyScore] = []
        user = record.actor_user

        # 1. Login frequency anomaly
        if record.failed_login_count > 0:
            mean, std = _simulate_baseline(user, "login_frequency")
            z = _z_score(record.failed_login_count, mean, std)
            scores.append(AnomalyScore(
                anomaly_type=AnomalyType.login_frequency,
                z_score=z,
                observed_value=record.failed_login_count,
                baseline_mean=mean,
                baseline_std=std,
                is_anomalous=z > 2.0,
                is_strong_anomaly=z > 3.0,
                description=(
                    f"User had {record.failed_login_count} failed logins. "
                    f"Baseline: {mean:.1f} ± {std:.1f} (z={z:.2f})"
                ),
            ))

        # 2. API volume anomaly
        if record.api_request_count > 0:
            mean, std = _simulate_baseline(user, "api_volume")
            z = _z_score(record.api_request_count, mean, std)
            scores.append(AnomalyScore(
                anomaly_type=AnomalyType.api_volume,
                z_score=z,
                observed_value=record.api_request_count,
                baseline_mean=mean,
                baseline_std=std,
                is_anomalous=z > 2.0,
                is_strong_anomaly=z > 3.0,
                description=(
                    f"API request count: {record.api_request_count}. "
                    f"Baseline: {mean:.0f} ± {std:.0f} (z={z:.2f})"
                ),
            ))

        # 3. Privilege change anomaly
        if record.privilege_change_count > 0:
            mean, std = _simulate_baseline(user, "privilege_changes")
            z = _z_score(record.privilege_change_count, mean, std)
            scores.append(AnomalyScore(
                anomaly_type=AnomalyType.privilege_changes,
                z_score=z,
                observed_value=record.privilege_change_count,
                baseline_mean=mean,
                baseline_std=std,
                is_anomalous=z > 2.0,
                is_strong_anomaly=z > 3.0,
                description=(
                    f"Privilege changes: {record.privilege_change_count}. "
                    f"Baseline: {mean:.1f} ± {std:.1f} (z={z:.2f})"
                ),
            ))

        # 4. Geographic diversity anomaly
        if record.geo_distance_km > 0:
            # Use geo distance as a proxy for geographic diversity
            mean, std = _simulate_baseline(user, "geo_diversity")
            # Normalize: 1 for same country, 2+ for multi-country
            geo_score = 1.0 + (record.geo_distance_km / 3000.0)
            z = _z_score(geo_score, mean, std)
            scores.append(AnomalyScore(
                anomaly_type=AnomalyType.geo_diversity,
                z_score=z,
                observed_value=geo_score,
                baseline_mean=mean,
                baseline_std=std,
                is_anomalous=z > 2.0,
                is_strong_anomaly=z > 3.0,
                description=(
                    f"Geographic distance: {record.geo_distance_km}km. "
                    f"Diversity index: {geo_score:.1f}. Baseline: {mean:.1f} ± {std:.1f} (z={z:.2f})"
                ),
            ))

        # 5. Time-of-day anomaly
        if record.after_hours_flag:
            mean, std = _simulate_baseline(user, "time_anomaly")
            # After-hours activity = 1.0 (binary)
            z = _z_score(1.0, mean, std)
            scores.append(AnomalyScore(
                anomaly_type=AnomalyType.time_anomaly,
                z_score=z,
                observed_value=1.0,
                baseline_mean=mean,
                baseline_std=std,
                is_anomalous=z > 2.0,
                is_strong_anomaly=z > 3.0,
                description=(
                    f"Activity during {record.login_time_bucket.value}. "
                    f"After-hours baseline ratio: {mean:.2f} ± {std:.2f} (z={z:.2f})"
                ),
            ))

        # Composite z-score (root-mean-square of individual z-scores)
        if scores:
            z_values = [s.z_score for s in scores]
            composite_z = math.sqrt(sum(z * z for z in z_values) / len(z_values))
        else:
            composite_z = 0.0

        # Risk multiplier: boost the triage score for anomalous events
        if composite_z > 3.0:
            risk_mult = 1.5
        elif composite_z > 2.0:
            risk_mult = 1.25
        elif composite_z > 1.5:
            risk_mult = 1.1
        else:
            risk_mult = 1.0

        is_anomalous = composite_z > 2.0
        anomalous_types = [s.anomaly_type.value for s in scores if s.is_anomalous]

        explanation = ""
        if is_anomalous:
            explanation = (
                f"Behavioral anomaly detected for {user}. "
                f"Composite z-score: {composite_z:.2f}. "
                f"Anomalous dimensions: {', '.join(anomalous_types)}. "
                f"This event deviates significantly from the user's historical baseline."
            )
        elif scores:
            explanation = (
                f"No significant anomalies for {user}. "
                f"Composite z-score: {composite_z:.2f} (within normal range)."
            )

        return AnomalyReport(
            incident_id=record.incident_id,
            user_id=user,
            anomaly_scores=scores,
            composite_z_score=composite_z,
            risk_multiplier=risk_mult,
            is_anomalous=is_anomalous,
            explanation=explanation,
        )

    def analyze_enriched(self, incident: EnrichedIncident, record: RawIncidentRecord) -> dict:
        """Return anomaly report as a dict, suitable for API response."""
        report = self.analyze(record)
        return report.to_dict()

    def batch_analyze(self, records: list[RawIncidentRecord]) -> list[AnomalyReport]:
        """Analyze a batch of records."""
        return [self.analyze(r) for r in records]


@lru_cache
def get_anomaly_detector() -> AnomalyDetector:
    return AnomalyDetector()
