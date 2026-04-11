from fastapi import APIRouter

# app in içinde core var core un içinde config o file içinden settings func ını import et
from app.core.config import get_settings
# yeni bir router nesnesi oluşturuyoruz ismine de health diyourz
# health etiketi taşıyan bir API router oluştur ve adını router koy.
router = APIRouter(tags=["health"])


# `@router.get("/health")` bir decorator'dır.
# get  HTTP GET isteği için route tanımla ("/health") bu endpoint’in yolu

@router.get("/health")
# health_check adında bir fonksiyon tanımlıyorum. Parametre almıyor. Sonunda string-string sözlük döndürüyor.
def health_check() -> dict[str, str]:
    # Ayarları alıyoruz.
    settings = get_settings()
    # JSON olarak dönecek cevap.
    return {
        # Servis ayakta mı?
        "status": "ok",
        # Uygulamanın adı ne?
        "service": settings.app_name,
        # Hangi açıklama sağlayıcı modu açık?
        "llm_provider": settings.llm_provider,
    }
