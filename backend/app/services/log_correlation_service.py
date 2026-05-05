# Bu dosya normalize edilmiş log event'lerden incident adayları üretir.

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from statistics import median

from app.models.domain import (
    CorrelatedIncidentRecord,
    IncidentEventType,
    LoginTimeBucket,
    NormalizedEventKind,
    NormalizedLogEvent,
    RawIncidentRecord,
)


COUNTRY_COORDINATES = {
    "US": (39.8283, -98.5795),
    "DE": (51.1657, 10.4515),
    "GB": (55.3781, -3.4360),
    "TR": (38.9637, 35.2433),
    "NL": (52.1326, 5.2913),
    "CA": (56.1304, -106.3468),
    "SG": (1.3521, 103.8198),
    "JP": (36.2048, 138.2529),
    "FR": (46.2276, 2.2137),
    "AU": (-25.2744, 133.7751),
}


class LogCorrelationService:
    def correlate(
        self,
        upload_id: str,
        events: list[NormalizedLogEvent],
    ) -> list[CorrelatedIncidentRecord]:
        grouped_events: dict[str, list[NormalizedLogEvent]] = defaultdict(list)
        for event in sorted(events, key=lambda item: item.timestamp):
            grouped_events[event.actor_user].append(event)

        api_counts = [
            sum(1 for event in actor_events if self._is_api_event(event))
            for actor_events in grouped_events.values()
        ]
        api_baseline = median(api_counts) if api_counts else 0

        incident_counter = 1
        correlated: list[CorrelatedIncidentRecord] = []

        for actor_user, actor_events in grouped_events.items():
            detectors = [
                self._detect_auth_clusters(actor_events),
                self._detect_geo_anomalies(actor_events),
                self._detect_privilege_windows(actor_events),
                self._detect_after_hours_admin(actor_events),
                self._detect_api_spikes(actor_events, api_baseline),
            ]

            for detector_output in detectors:
                for incident in detector_output:
                    incident.incident.incident_id = self._build_incident_id(
                        upload_id,
                        incident_counter,
                    )
                    incident_counter += 1
                    correlated.append(incident)

        correlated.sort(key=lambda item: item.incident.timestamp, reverse=True)
        return correlated

    def _detect_auth_clusters(
        self,
        actor_events: list[NormalizedLogEvent],
    ) -> list[CorrelatedIncidentRecord]:
        failures = [event for event in actor_events if self._is_auth_failure(event)]
        correlated: list[CorrelatedIncidentRecord] = []

        for cluster in self._cluster_events(failures, max_gap=timedelta(minutes=30)):
            if len(cluster) < 5:
                continue

            event_type = (
                IncidentEventType.multiple_failed_login_attempts
                if len(cluster) >= 8
                else IncidentEventType.repeated_authentication_failures
            )
            primary = cluster[-1]
            correlated.append(
                CorrelatedIncidentRecord(
                    incident=RawIncidentRecord(
                        incident_id="TEMP",
                        timestamp=primary.timestamp,
                        source_system=self._most_common_source(cluster),
                        affected_entity=self._most_common_entity(cluster),
                        actor_user=primary.actor_user,
                        actor_ip=primary.source_ip or "0.0.0.0",
                        actor_country=primary.source_country or "NA",
                        target_country=None,
                        event_type=event_type,
                        failed_login_count=len(cluster),
                        privilege_change_count=0,
                        api_request_count=0,
                        login_time_bucket=self._time_bucket(primary.timestamp),
                        is_admin_action=any(item.is_admin_action for item in cluster),
                        geo_distance_km=0,
                        impossible_travel_flag=False,
                        after_hours_flag=self._is_after_hours(primary.timestamp),
                        notes=(
                            f"{len(cluster)} authentication failures were correlated for "
                            f"{primary.actor_user} in a 30 minute window."
                        ),
                    ),
                    source_event_count=len(cluster),
                    source_event_samples=self._build_event_samples(cluster),
                )
            )

        return correlated

    def _detect_geo_anomalies(
        self,
        actor_events: list[NormalizedLogEvent],
    ) -> list[CorrelatedIncidentRecord]:
        successful_logins = [
            event
            for event in actor_events
            if self._is_auth_success(event) and event.source_country
        ]
        correlated: list[CorrelatedIncidentRecord] = []

        for previous, current in zip(successful_logins, successful_logins[1:]):
            if previous.source_country == current.source_country:
                continue

            distance = self._country_distance(
                previous.source_country,
                current.source_country,
            )
            if distance < 1000:
                continue

            hours_apart = abs((current.timestamp - previous.timestamp).total_seconds()) / 3600
            event_type = (
                IncidentEventType.impossible_travel_pattern
                if distance >= 5000 and hours_apart <= 4
                else IncidentEventType.risky_sign_in_pattern
            )

            related_events = [previous, current]
            correlated.append(
                CorrelatedIncidentRecord(
                    incident=RawIncidentRecord(
                        incident_id="TEMP",
                        timestamp=current.timestamp,
                        source_system=current.source_system,
                        affected_entity=current.affected_entity,
                        actor_user=current.actor_user,
                        actor_ip=current.source_ip or "0.0.0.0",
                        actor_country=previous.source_country or "NA",
                        target_country=current.source_country,
                        event_type=event_type,
                        failed_login_count=0,
                        privilege_change_count=0,
                        api_request_count=0,
                        login_time_bucket=self._time_bucket(current.timestamp),
                        is_admin_action=current.is_admin_action,
                        geo_distance_km=distance,
                        impossible_travel_flag=event_type == IncidentEventType.impossible_travel_pattern,
                        after_hours_flag=self._is_after_hours(current.timestamp),
                        notes=(
                            f"Successful authentication events for {current.actor_user} "
                            f"moved from {previous.source_country} to {current.source_country} "
                            f"in approximately {hours_apart:.1f} hours."
                        ),
                    ),
                    source_event_count=len(related_events),
                    source_event_samples=self._build_event_samples(related_events),
                )
            )

        return correlated

    def _detect_privilege_windows(
        self,
        actor_events: list[NormalizedLogEvent],
    ) -> list[CorrelatedIncidentRecord]:
        privilege_events = [
            event
            for event in actor_events
            if event.is_privilege_change or event.event_kind == NormalizedEventKind.privilege_change
        ]
        correlated: list[CorrelatedIncidentRecord] = []

        for cluster in self._cluster_events(privilege_events, max_gap=timedelta(hours=2)):
            if not cluster:
                continue

            primary = cluster[-1]
            correlated.append(
                CorrelatedIncidentRecord(
                    incident=RawIncidentRecord(
                        incident_id="TEMP",
                        timestamp=primary.timestamp,
                        source_system=self._most_common_source(cluster),
                        affected_entity=self._most_common_entity(cluster),
                        actor_user=primary.actor_user,
                        actor_ip=primary.source_ip or "0.0.0.0",
                        actor_country=primary.source_country or "NA",
                        target_country=None,
                        event_type=IncidentEventType.unusual_privilege_escalation,
                        failed_login_count=0,
                        privilege_change_count=len(cluster),
                        api_request_count=0,
                        login_time_bucket=self._time_bucket(primary.timestamp),
                        is_admin_action=True,
                        geo_distance_km=0,
                        impossible_travel_flag=False,
                        after_hours_flag=self._is_after_hours(primary.timestamp),
                        notes=(
                            f"{len(cluster)} privilege-related actions were correlated for "
                            f"{primary.actor_user} in a short time window."
                        ),
                    ),
                    source_event_count=len(cluster),
                    source_event_samples=self._build_event_samples(cluster),
                )
            )

        return correlated

    def _detect_after_hours_admin(
        self,
        actor_events: list[NormalizedLogEvent],
    ) -> list[CorrelatedIncidentRecord]:
        admin_events = [
            event
            for event in actor_events
            if event.is_admin_action and self._is_after_hours(event.timestamp)
        ]
        correlated: list[CorrelatedIncidentRecord] = []

        for cluster in self._cluster_events(admin_events, max_gap=timedelta(hours=1)):
            if not cluster:
                continue

            primary = cluster[-1]
            correlated.append(
                CorrelatedIncidentRecord(
                    incident=RawIncidentRecord(
                        incident_id="TEMP",
                        timestamp=primary.timestamp,
                        source_system=self._most_common_source(cluster),
                        affected_entity=self._most_common_entity(cluster),
                        actor_user=primary.actor_user,
                        actor_ip=primary.source_ip or "0.0.0.0",
                        actor_country=primary.source_country or "NA",
                        target_country=None,
                        event_type=IncidentEventType.abnormal_access_outside_hours,
                        failed_login_count=0,
                        privilege_change_count=0,
                        api_request_count=0,
                        login_time_bucket=self._time_bucket(primary.timestamp),
                        is_admin_action=True,
                        geo_distance_km=0,
                        impossible_travel_flag=False,
                        after_hours_flag=True,
                        notes=(
                            f"Administrative activity for {primary.actor_user} was observed "
                            f"outside normal operating hours."
                        ),
                    ),
                    source_event_count=len(cluster),
                    source_event_samples=self._build_event_samples(cluster),
                )
            )

        return correlated

    def _detect_api_spikes(
        self,
        actor_events: list[NormalizedLogEvent],
        api_baseline: float,
    ) -> list[CorrelatedIncidentRecord]:
        api_events = [event for event in actor_events if self._is_api_event(event)]
        if not api_events:
            return []

        api_count = len(api_events)
        threshold = max(15, int(api_baseline * 3) if api_baseline else 15)
        if api_count < threshold:
            return []

        primary = api_events[-1]
        return [
            CorrelatedIncidentRecord(
                incident=RawIncidentRecord(
                    incident_id="TEMP",
                    timestamp=primary.timestamp,
                    source_system=self._most_common_source(api_events),
                    affected_entity=self._most_common_entity(api_events),
                    actor_user=primary.actor_user,
                    actor_ip=primary.source_ip or "0.0.0.0",
                    actor_country=primary.source_country or "NA",
                    target_country=None,
                    event_type=IncidentEventType.suspicious_api_activity,
                    failed_login_count=0,
                    privilege_change_count=0,
                    api_request_count=api_count * 150,
                    login_time_bucket=self._time_bucket(primary.timestamp),
                    is_admin_action=any(item.is_admin_action for item in api_events),
                    geo_distance_km=0,
                    impossible_travel_flag=False,
                    after_hours_flag=self._is_after_hours(primary.timestamp),
                    notes=(
                        f"API activity volume for {primary.actor_user} exceeded the "
                        f"upload baseline with {api_count} correlated requests."
                    ),
                ),
                source_event_count=api_count,
                source_event_samples=self._build_event_samples(api_events),
            )
        ]

    def _cluster_events(
        self,
        events: list[NormalizedLogEvent],
        *,
        max_gap: timedelta,
    ) -> list[list[NormalizedLogEvent]]:
        if not events:
            return []

        clusters: list[list[NormalizedLogEvent]] = []
        current_cluster = [events[0]]

        for event in events[1:]:
            if event.timestamp - current_cluster[-1].timestamp <= max_gap:
                current_cluster.append(event)
            else:
                clusters.append(current_cluster)
                current_cluster = [event]

        clusters.append(current_cluster)
        return clusters

    def _is_auth_failure(self, event: NormalizedLogEvent) -> bool:
        combined = f"{event.action} {event.status} {event.message}".lower()
        return (
            event.event_kind == NormalizedEventKind.authentication
            and any(keyword in combined for keyword in ("fail", "denied", "invalid", "error"))
        )

    def _is_auth_success(self, event: NormalizedLogEvent) -> bool:
        combined = f"{event.action} {event.status} {event.message}".lower()
        return (
            event.event_kind == NormalizedEventKind.authentication
            and any(keyword in combined for keyword in ("success", "ok", "allow", "accepted"))
        )

    def _is_api_event(self, event: NormalizedLogEvent) -> bool:
        return event.is_api_activity or event.event_kind == NormalizedEventKind.api_activity

    def _build_event_samples(self, events: list[NormalizedLogEvent]) -> list[str]:
        samples: list[str] = []
        for event in events[:3]:
            sample = (
                f"{event.timestamp.isoformat()} | {event.source_system} | "
                f"{event.action} | {event.status} | {event.message[:180]}"
            )
            samples.append(sample)
        return samples

    def _most_common_entity(self, events: list[NormalizedLogEvent]) -> str:
        return Counter(event.affected_entity for event in events).most_common(1)[0][0]

    def _most_common_source(self, events: list[NormalizedLogEvent]) -> str:
        return Counter(event.source_system for event in events).most_common(1)[0][0]

    def _time_bucket(self, timestamp: datetime) -> LoginTimeBucket:
        hour = timestamp.astimezone(UTC).hour
        if 8 <= hour < 18:
            return LoginTimeBucket.business_hours
        if 18 <= hour < 23:
            return LoginTimeBucket.after_hours
        return LoginTimeBucket.overnight

    def _is_after_hours(self, timestamp: datetime) -> bool:
        return self._time_bucket(timestamp) != LoginTimeBucket.business_hours

    def _build_incident_id(self, upload_id: str, index: int) -> str:
        normalized_upload_id = upload_id.replace("-", "").upper()[:6]
        return f"UPL-{normalized_upload_id}-{index:03d}"

    def _country_distance(self, left_country: str | None, right_country: str | None) -> int:
        if not left_country or not right_country:
            return 0

        left = COUNTRY_COORDINATES.get(left_country.upper())
        right = COUNTRY_COORDINATES.get(right_country.upper())
        if left is None or right is None:
            return 0

        return int(self._haversine_km(left[0], left[1], right[0], right[1]))

    def _haversine_km(
        self,
        left_lat: float,
        left_lng: float,
        right_lat: float,
        right_lng: float,
    ) -> float:
        radius_km = 6371
        d_lat = radians(right_lat - left_lat)
        d_lng = radians(right_lng - left_lng)
        a = (
            sin(d_lat / 2) ** 2
            + cos(radians(left_lat)) * cos(radians(right_lat)) * sin(d_lng / 2) ** 2
        )
        c = 2 * asin(sqrt(a))
        return radius_km * c


@lru_cache
def get_log_correlation_service() -> LogCorrelationService:
    return LogCorrelationService()
