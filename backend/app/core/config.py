# `lru_cache` aynı sonucu tekrar tekrar üretmemek için hafızada tutar.
from functools import lru_cache

# `BaseSettings` ayarları çevre değişkenlerinden ve `.env` dosyasından okumayı kolaylaştırır.
from pydantic_settings import BaseSettings, SettingsConfigDict


# `class` Python'da yeni bir yapı tanımlamak için kullanılır.
# `Settings`, uygulama ayarlarını tutacak sınıfımız.
class Settings(BaseSettings):
    # Uygulamanın varsayılan adı.
    app_name: str = "AI-Powered Security Incident Triage Assistant"
    # Backend'in dinleyeceği host.
    api_host: str = "127.0.0.1"
    # Backend'in çalışacağı port.
    api_port: int = 8000
    # Açıklama sistemi için şimdilik hangi provider kullanılacak?
    llm_provider: str = "mock"
    # OpenAI-compatible veya Azure OpenAI istekleri için tam endpoint adresi.
    llm_api_url: str | None = None
    # LLM isteğinde kullanılacak API anahtarı.
    llm_api_key: str | None = None
    # OpenAI-compatible servislerde kullanılacak model adı.
    llm_model: str | None = None
    # Ağ isteği çok uzun sürmesin diye timeout süresi.
    llm_timeout_seconds: float = 20.0

    # Bu blok Pydantic'e ayarları nasıl okuyacağını söyler.
    model_config = SettingsConfigDict(
        # `.env` dosyasını da oku.
        env_file=".env",
        # Dosya UTF-8 olsun.
        env_file_encoding="utf-8",
        # Büyük-küçük harf farkına çok takılma.
        case_sensitive=False,
        # Fazladan bilinmeyen alan varsa hata verme, görmezden gel.
        extra="ignore",
    )


# `@lru_cache` bu fonksiyonun sonucunu saklar.
@lru_cache
# Ayarları tek noktadan almak için kullandığımız fonksiyon.
def get_settings() -> Settings:
    # `Settings()` yeni ayar nesnesi oluşturur ve gerekirse `.env` dosyasından okur.
    return Settings()
