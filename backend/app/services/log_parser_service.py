# Bu dosya yüklenen CSV/JSON/log dosyalarını normalize edilmiş log event'lere çevirir.

import base64
import csv
import gzip
import io
import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from functools import lru_cache

from app.models.domain import NormalizedEventKind, NormalizedLogEvent


TIMESTAMP_KEYS = [
    "timestamp",
    "_time",
    "time",
    "event_time",
    "occurred_at",
    "datetime",
    "date",
]
USER_KEYS = [
    "user",
    "username",
    "user_name",
    "actor_user",
    "account_name",
    "account",
    "principal",
    "email",
    "userid",
]
ENTITY_KEYS = [
    "affected_entity",
    "entity",
    "host",
    "hostname",
    "computer",
    "computer_name",
    "resource",
    "service",
    "repository",
    "target",
]
IP_KEYS = [
    "src_ip",
    "source_ip",
    "client_ip",
    "ip",
    "ip_address",
    "sourceaddress",
]
COUNTRY_KEYS = [
    "country",
    "src_country",
    "source_country",
    "geo_country",
    "country_code",
]
TARGET_COUNTRY_KEYS = [
    "target_country",
    "dst_country",
    "destination_country",
]
ACTION_KEYS = [
    "action",
    "event_type",
    "event_name",
    "operation",
    "signature",
    "activity",
    "type",
    "category",
]
STATUS_KEYS = [
    "status",
    "result",
    "outcome",
    "auth_result",
    "action_result",
]
MESSAGE_KEYS = [
    "message",
    "description",
    "details",
    "raw_message",
    "summary",
    "cmdline",
]
SOURCE_KEYS = [
    "source_system",
    "source",
    "product",
    "vendor",
    "service_name",
    "log_name",
]


class LogParserService:
    def parse_upload(self, filename: str, content_base64: str) -> tuple[str, bytes, list[NormalizedLogEvent]]:
        raw_bytes = base64.b64decode(content_base64)
        decoded_bytes = self._maybe_decompress(filename, raw_bytes)
        text_content = decoded_bytes.decode("utf-8", errors="replace")
        parser_format = self._detect_format(filename, text_content)

        if parser_format == "csv":
            rows = self._parse_csv(text_content)
        elif parser_format == "json":
            rows = self._parse_json(text_content)
        elif parser_format == "jsonl":
            rows = self._parse_jsonl(text_content)
        else:
            rows = self._parse_plain_lines(text_content)

        normalized_events = [
            self._normalize_row(index=index, row=row, fallback_source=self._infer_source_from_filename(filename))
            for index, row in enumerate(rows, start=1)
        ]
        normalized_events.sort(key=lambda event: event.timestamp)
        return parser_format, decoded_bytes, normalized_events

    def _maybe_decompress(self, filename: str, raw_bytes: bytes) -> bytes:
        if filename.lower().endswith(".gz"):
            try:
                return gzip.decompress(raw_bytes)
            except OSError:
                return raw_bytes
        return raw_bytes

    def _detect_format(self, filename: str, text_content: str) -> str:
        lowered_name = filename.lower()
        stripped = text_content.lstrip()

        if lowered_name.endswith(".json") or stripped.startswith("["):
            return "json"
        if lowered_name.endswith(".jsonl") or lowered_name.endswith(".ndjson"):
            return "jsonl"
        if stripped.startswith("{"):
            first_line = stripped.splitlines()[0]
            if first_line.endswith("}"):
                return "jsonl"
        if lowered_name.endswith(".csv"):
            return "csv"

        first_line = text_content.splitlines()[0] if text_content.splitlines() else ""
        if "," in first_line and len(first_line.split(",")) >= 3:
            return "csv"
        return "plain"

    def _parse_csv(self, text_content: str) -> list[dict[str, str]]:
        reader = csv.DictReader(io.StringIO(text_content))
        return [
            {str(key): "" if value is None else str(value) for key, value in row.items()}
            for row in reader
        ]

    def _parse_json(self, text_content: str) -> list[dict[str, str]]:
        parsed = json.loads(text_content)
        if isinstance(parsed, list):
            return [self._stringify_dict(item) for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            for candidate_key in ("records", "events", "items", "data"):
                candidate = parsed.get(candidate_key)
                if isinstance(candidate, list):
                    return [self._stringify_dict(item) for item in candidate if isinstance(item, dict)]
            return [self._stringify_dict(parsed)]
        return []

    def _parse_jsonl(self, text_content: str) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for line in text_content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                rows.append(self._stringify_dict(parsed))
        return rows

    def _parse_plain_lines(self, text_content: str) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for index, line in enumerate(text_content.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            rows.append(
                {
                    "line_number": str(index),
                    "message": stripped,
                    "timestamp": self._extract_timestamp_from_text(stripped) or datetime.now(UTC).isoformat(),
                }
            )
        return rows

    def _normalize_row(
        self,
        *,
        index: int,
        row: dict[str, str],
        fallback_source: str,
    ) -> NormalizedLogEvent:
        lowered = {key.lower(): value for key, value in row.items() if key is not None}
        timestamp = self._parse_timestamp(self._pick_value(lowered, TIMESTAMP_KEYS))
        actor_user = self._pick_value(lowered, USER_KEYS) or self._extract_user_from_text(lowered)
        affected_entity = self._pick_value(lowered, ENTITY_KEYS) or actor_user or "unknown-entity"
        source_ip = self._pick_value(lowered, IP_KEYS) or self._extract_ip_from_text(lowered)
        source_country = self._pick_value(lowered, COUNTRY_KEYS)
        target_country = self._pick_value(lowered, TARGET_COUNTRY_KEYS)
        action = self._pick_value(lowered, ACTION_KEYS) or "security_event"
        status = self._pick_value(lowered, STATUS_KEYS) or self._infer_status(action, lowered)
        message = self._pick_value(lowered, MESSAGE_KEYS) or " ".join(lowered.values())
        source_system = self._pick_value(lowered, SOURCE_KEYS) or fallback_source
        combined_text = f"{action} {status} {message}".lower()
        event_kind = self._infer_event_kind(combined_text)

        return NormalizedLogEvent(
            event_id=f"EVT-{index:05d}",
            timestamp=timestamp,
            source_system=source_system,
            actor_user=actor_user or "unknown-user",
            affected_entity=affected_entity,
            source_ip=source_ip,
            source_country=source_country,
            target_country=target_country,
            action=action,
            status=status,
            message=message,
            event_kind=event_kind,
            is_admin_action=self._looks_admin_action(combined_text),
            is_privilege_change=self._looks_privilege_change(combined_text),
            is_api_activity=self._looks_api_activity(combined_text),
            raw_data={key: value[:240] for key, value in list(lowered.items())[:12]},
        )

    def _stringify_dict(self, payload: dict) -> dict[str, str]:
        return {
            str(key): "" if value is None else str(value)
            for key, value in payload.items()
        }

    def _pick_value(self, lowered: dict[str, str], keys: Iterable[str]) -> str | None:
        for key in keys:
            value = lowered.get(key)
            if value:
                return value
        return None

    def _parse_timestamp(self, value: str | None) -> datetime:
        if not value:
            return datetime.now(UTC)

        cleaned = value.strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned.replace("Z", "+00:00")

        try:
            return datetime.fromisoformat(cleaned).astimezone(UTC)
        except ValueError:
            pass

        if cleaned.isdigit():
            number = int(cleaned)
            if len(cleaned) >= 13:
                number = number / 1000
            return datetime.fromtimestamp(number, tz=UTC)

        for pattern in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
            try:
                return datetime.strptime(cleaned, pattern).replace(tzinfo=UTC)
            except ValueError:
                continue

        return datetime.now(UTC)

    def _infer_source_from_filename(self, filename: str) -> str:
        lowered = filename.lower()
        if "okta" in lowered:
            return "okta"
        if "cloudtrail" in lowered:
            return "aws_cloudtrail"
        if "entra" in lowered or "azure" in lowered:
            return "microsoft_entra"
        if "github" in lowered:
            return "github_audit_log"
        if "api" in lowered:
            return "api_gateway"
        return "uploaded_log"

    def _infer_status(self, action: str, lowered: dict[str, str]) -> str:
        combined = f"{action} {' '.join(lowered.values())}".lower()
        if any(keyword in combined for keyword in ("fail", "denied", "invalid", "error")):
            return "failure"
        if any(keyword in combined for keyword in ("success", "granted", "allow", "ok")):
            return "success"
        return "unknown"

    def _infer_event_kind(self, combined_text: str) -> NormalizedEventKind:
        if any(keyword in combined_text for keyword in ("privilege", "sudo", "role", "grant", "group membership")):
            return NormalizedEventKind.privilege_change
        if any(keyword in combined_text for keyword in ("api", "graphql", "rest", "endpoint", "request")):
            return NormalizedEventKind.api_activity
        if any(keyword in combined_text for keyword in ("admin", "administrator", "root")):
            return NormalizedEventKind.admin_activity
        if any(keyword in combined_text for keyword in ("login", "signin", "sign-in", "auth", "authentication")):
            return NormalizedEventKind.authentication
        return NormalizedEventKind.generic_security

    def _looks_admin_action(self, combined_text: str) -> bool:
        return any(keyword in combined_text for keyword in ("admin", "administrator", "root", "sudo"))

    def _looks_privilege_change(self, combined_text: str) -> bool:
        return any(keyword in combined_text for keyword in ("privilege", "grant", "role", "group membership", "permission"))

    def _looks_api_activity(self, combined_text: str) -> bool:
        return any(keyword in combined_text for keyword in ("api", "graphql", "rest", "/v1/", "/api/"))

    def _extract_ip_from_text(self, lowered: dict[str, str]) -> str | None:
        combined = " ".join(lowered.values())
        match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", combined)
        return match.group(0) if match else None

    def _extract_user_from_text(self, lowered: dict[str, str]) -> str | None:
        combined = " ".join(lowered.values())
        match = re.search(r"user[=: ]+([A-Za-z0-9._@-]+)", combined, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_timestamp_from_text(self, text: str) -> str | None:
        match = re.search(
            r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?)",
            text,
        )
        if match:
            return match.group(1)
        return None


@lru_cache
def get_log_parser_service() -> LogParserService:
    return LogParserService()
