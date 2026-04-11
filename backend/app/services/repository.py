# JSON dosyasını Python list/dict yapısına çevirmek için kullanılır.
# repsitory: veriyi alan organ,ize eden , dış dünyadan veriyi saklayan yapı, bizim yapıda: json dosyasını açıyo,
import json
# Tek repository nesnesini tekrar kullanmak için.
from functools import lru_cache
# Dosya yollarını güvenli kurmak için.
from pathlib import Path
# pathlib Python’ın dosya yollarıyla çalışmak için modülü

# JSON kayıtlarını doğrulamak için veri modelimizi alıyoruz.
from app.models.domain import RawIncidentRecord


# `__file__` mevcut dosyanın yoludur mesela şu an repository.py.
# `.resolve()` tam dosya yolunu bulur.
# `.parents[2]` ile backend klasörüne çıkarız.
# Sonra `data/incidents.json` yolunu ekleriz.
# parents[0]-> bir üst ; parents[1]-> iki üst .... yani kök dosyaya dogru yukarı çıkıyoruz yani burda app e çıkıyo app data kısmına ordan dataya gidip json dosyasını buluyo
DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "incidents.json"


# Repository, veri okuma işini tek yerde toplayan yapıdır.
class IncidentRepository:
    """Loads curated incident records from the local dataset."""

    # İstersek dışarıdan farklı bir data yolu verebiliriz.
    def __init__(self, data_path: Path | None = None) -> None:
        # Yeni bir IncidentRepository oluşturulunca bu başlangıç fonksiyonu çalışsın. İstersek dışarıdan bir dosya yolu verebiliriz, vermezsek boş kabul edilir
        self.data_path = data_path or DATA_PATH

    # Tüm incident kayıtlarını yükle.
    def list_incidents(self) -> list[RawIncidentRecord]:
        # Dosyayı oku.
        # read text kısmı : bu dosyanın içeriğini yazı olarak oku, json.loads-> json stringi python verisine çevir
        payload = json.loads(self.data_path.read_text(encoding="utf-8"))
        # Her kaydı modelimize göre doğrula.
        # payload içindeki her elemanı sırayla al, adına item de (for item in payload)
        return [RawIncidentRecord.model_validate(item) for item in payload]

    # Tek bir incident'i id ile bul.
    def get_incident(self, incident_id: str) -> RawIncidentRecord | None:
        return next(
            (incident for incident in self.list_incidents()
             if incident.incident_id == incident_id),
            None,
        )


# Bu fonksiyon repository'nin tek bir kopyasını döndürür.
@lru_cache
def get_incident_repository() -> IncidentRepository:
    return IncidentRepository()
