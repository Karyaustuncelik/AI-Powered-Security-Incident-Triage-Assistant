# Bu dosya dashboard için gerekli özet istatistikleri üretir.

from collections import Counter

from app.models.domain import EnrichedIncident, SeverityLevel
from app.models.schemas import DistributionBucket, StatsResponse
from app.services.incidents_service import to_list_item


# Dashboard istatistiklerini üreten servis sınıfı.
class StatsService:
    # Incident listesinden özet sayı ve dağılım üret.
    def build_stats(self, incidents: list[EnrichedIncident]) -> StatsResponse:
        category_counts = Counter(incident.category.value for incident in incidents)
        priority_counts = Counter(incident.priority.value for incident in incidents)
        review_status_counts = Counter(
            (incident.review.review_status.value if incident.review else "open")
            for incident in incidents
        )

        category_distribution = [
            DistributionBucket(label=label, count=count)
            for label, count in sorted(category_counts.items())
        ]
        priority_distribution = [
            DistributionBucket(label=label, count=count)
            for label, count in sorted(priority_counts.items())
        ]
        review_status_distribution = [
            DistributionBucket(label=label, count=count)
            for label, count in sorted(review_status_counts.items())
        ]

        recent_incidents = [
            to_list_item(incident)
            for incident in sorted(
                incidents,
                key=lambda incident: incident.timestamp,
                reverse=True,
            )[:5]
        ]

        return StatsResponse(
            total_incidents=len(incidents),
            high_or_critical_count=sum(
                1
                for incident in incidents
                if incident.severity in {SeverityLevel.high, SeverityLevel.critical}
            ),
            category_distribution=category_distribution,
            priority_distribution=priority_distribution,
            review_status_distribution=review_status_distribution,
            recent_incidents=recent_incidents,
        )
