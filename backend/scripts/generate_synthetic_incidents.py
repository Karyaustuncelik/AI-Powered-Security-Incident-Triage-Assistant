# Bu satır bazı tip ipuçlarını daha rahat yazabilmek için gelecekteki davranışı açar.
from __future__ import annotations

# JSON dosyası yazmak için kullanılır.
import json
# Rastgele ama kontrollü veri üretmek için.
import random
# Python'ın modül arama yoluna klasör eklemek için.
import sys
# Zaman üretmek için gerekli araçlar.
from datetime import UTC, datetime, timedelta
# Dosya yollarını güvenli kurmak için.
from pathlib import Path

# Bu script'in olduğu yerden backend klasörünü buluyoruz.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
# Eğer backend klasörü Python'ın arama yolunda yoksa ekle.
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Veri üretirken kullanacağımız tipleri içe al.
from app.models.domain import IncidentEventType, LoginTimeBucket, RawIncidentRecord


# Üretilen dosyanın nereye yazılacağını belirliyoruz.
OUTPUT_PATH = BACKEND_ROOT / "data" / "incidents.json"
# Aynı veriyi tekrar üretebilmek için sabit random seed.
RANDOM_SEED = 7
# Kaç incident üretileceği.
INCIDENT_COUNT = 24

# Örnek kullanıcılar.
USERS = [
    "j.smith",
    "m.chen",
    "ops-admin",
    "finance.lead",
    "sre-oncall",
    "a.khan",
    "support.bot",
    "security.analyst",
]

# Kullanıcıdan etkilenen entity'ye eşleme.
ENTITY_MAP = {
    "j.smith": "j.smith",
    "m.chen": "m.chen",
    "ops-admin": "infra-admin-group",
    "finance.lead": "finance-data-lake",
    "sre-oncall": "production-kubernetes",
    "a.khan": "a.khan",
    "support.bot": "support-automation-service",
    "security.analyst": "security-operations",
}

# Olayın gelebileceği kaynak sistemler.
SOURCE_SYSTEMS = [
    "okta",
    "microsoft_entra",
    "aws_cloudtrail",
    "github_audit_log",
    "internal_api_gateway",
]

# Kullanacağımız ülke havuzu.
COUNTRIES = ["US", "DE", "GB", "TR", "NL", "CA", "SG", "JP"]

# Desteklediğimiz olay tiplerinin listesi.
EVENT_TYPES = [
    IncidentEventType.multiple_failed_login_attempts,
    IncidentEventType.repeated_authentication_failures,
    IncidentEventType.risky_sign_in_pattern,
    IncidentEventType.abnormal_access_outside_hours,
    IncidentEventType.impossible_travel_pattern,
    IncidentEventType.unusual_privilege_escalation,
    IncidentEventType.suspicious_api_activity,
]


# Rastgele IP adresi üret.
def random_ip(rng: random.Random) -> str:
    return ".".join(str(rng.randint(10, 220)) for _ in range(4))


# Olay tipine göre daha mantıklı bir zaman dilimi seç.
def choose_time_bucket(event_type: IncidentEventType, rng: random.Random) -> LoginTimeBucket:
    if event_type == IncidentEventType.abnormal_access_outside_hours:
        return rng.choice([LoginTimeBucket.after_hours, LoginTimeBucket.overnight])
    if event_type == IncidentEventType.unusual_privilege_escalation:
        return rng.choice([LoginTimeBucket.business_hours, LoginTimeBucket.after_hours])
    return rng.choice(list(LoginTimeBucket))


# Olay tipine göre kısa bir açıklama üret.
def build_notes(event_type: IncidentEventType, actor_country: str, target_country: str | None) -> str:
    notes_map = {
        IncidentEventType.multiple_failed_login_attempts: (
            "Burst of sign-in failures from a new source IP within a short time window."
        ),
        IncidentEventType.repeated_authentication_failures: (
            "Authentication failures persisted across multiple retries and source contexts."
        ),
        IncidentEventType.risky_sign_in_pattern: (
            "Sign-in pattern matched a known risky access pattern based on velocity and context."
        ),
        IncidentEventType.abnormal_access_outside_hours: (
            "Access occurred outside the user's normal working hours and deviated from recent behavior."
        ),
        IncidentEventType.impossible_travel_pattern: (
            f"Access sequence suggested travel between {actor_country} and {target_country} faster than realistically possible."
        ),
        IncidentEventType.unusual_privilege_escalation: (
            "Role or permission elevation activity exceeded the user's recent baseline."
        ),
        IncidentEventType.suspicious_api_activity: (
            "API volume and request pattern deviated sharply from the service account baseline."
        ),
    }
    return notes_map[event_type]


# Tek bir incident kaydı üret.
def build_record(index: int, event_type: IncidentEventType, rng: random.Random) -> RawIncidentRecord:
    actor_user = rng.choice(USERS)
    source_system = rng.choice(SOURCE_SYSTEMS)
    actor_country = rng.choice(COUNTRIES)
    target_country = rng.choice([country for country in COUNTRIES if country != actor_country])
    timestamp = datetime.now(UTC) - timedelta(hours=index * 5 + rng.randint(0, 4))
    login_time_bucket = choose_time_bucket(event_type, rng)

    # Başlangıçta tüm sayısal alanları nötr değerlerle başlat.
    failed_login_count = 0
    privilege_change_count = 0
    api_request_count = 0
    is_admin_action = False
    geo_distance_km = 0
    impossible_travel_flag = False
    after_hours_flag = login_time_bucket in {LoginTimeBucket.after_hours, LoginTimeBucket.overnight}

    # Olay tipine göre ilgili alanları doldur.
    if event_type == IncidentEventType.multiple_failed_login_attempts:
        failed_login_count = rng.randint(8, 18)
    elif event_type == IncidentEventType.repeated_authentication_failures:
        failed_login_count = rng.randint(5, 11)
    elif event_type == IncidentEventType.risky_sign_in_pattern:
        failed_login_count = rng.randint(2, 6)
        geo_distance_km = rng.randint(500, 3500)
    elif event_type == IncidentEventType.abnormal_access_outside_hours:
        failed_login_count = rng.randint(1, 4)
        is_admin_action = rng.choice([True, False])
    elif event_type == IncidentEventType.impossible_travel_pattern:
        failed_login_count = rng.randint(1, 3)
        geo_distance_km = rng.randint(6500, 12500)
        impossible_travel_flag = True
    elif event_type == IncidentEventType.unusual_privilege_escalation:
        privilege_change_count = rng.randint(3, 9)
        is_admin_action = True
    elif event_type == IncidentEventType.suspicious_api_activity:
        api_request_count = rng.randint(900, 4000)

    # Sonunda doğrulanmış bir kayıt oluştur.
    return RawIncidentRecord(
        incident_id=f"INC-{1000 + index}",
        timestamp=timestamp,
        source_system=source_system,
        affected_entity=ENTITY_MAP[actor_user],
        actor_user=actor_user,
        actor_ip=random_ip(rng),
        actor_country=actor_country,
        target_country=target_country if impossible_travel_flag else None,
        event_type=event_type,
        failed_login_count=failed_login_count,
        privilege_change_count=privilege_change_count,
        api_request_count=api_request_count,
        login_time_bucket=login_time_bucket,
        is_admin_action=is_admin_action,
        geo_distance_km=geo_distance_km,
        impossible_travel_flag=impossible_travel_flag,
        after_hours_flag=after_hours_flag,
        notes=build_notes(event_type, actor_country, target_country),
    )


# Tüm dataset'i üret.
def generate_incidents() -> list[RawIncidentRecord]:
    rng = random.Random(RANDOM_SEED)
    incidents: list[RawIncidentRecord] = []

    # Her olay ailesinden en az bir tane üret.
    for index, event_type in enumerate(EVENT_TYPES, start=1):
        incidents.append(build_record(index, event_type, rng))

    # Kalan kayıtları da olay türlerini karıştırarak doldur.
    for index in range(len(incidents) + 1, INCIDENT_COUNT + 1):
        incidents.append(build_record(index, rng.choice(EVENT_TYPES), rng))

    # En yeni kayıtları üstte göstermek için sırala.
    incidents.sort(key=lambda item: item.timestamp, reverse=True)
    return incidents


# Üretilen kayıtları JSON dosyasına yaz.
def write_dataset(records: list[RawIncidentRecord]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = [record.model_dump(mode="json") for record in records]
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# Script'in ana akışı.
def main() -> None:
    records = generate_incidents()
    write_dataset(records)
    print(f"Wrote {len(records)} incidents to {OUTPUT_PATH}")


# Bu dosya terminalden direkt çalıştırılırsa `main()` fonksiyonunu çağır.
if __name__ == "__main__":
    main()
