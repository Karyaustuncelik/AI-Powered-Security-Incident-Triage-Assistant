# `from ... import ...` Python'a "şuradan bu şeyi al" der.
from fastapi import FastAPI
# CORS middleware tarayıcıdaki frontend'in backend ile konuşmasına izin vermek için kullanılır.
from fastapi.middleware.cors import CORSMiddleware

# `router as health_router` demek:
# `router` adını burada daha açıklayıcı bir isimle kullanalım.
from app.api.routes.explain import router as explain_router
from app.api.routes.filters import router as filters_router
from app.api.routes.health import router as health_router
# Incident listeleme ve detay route'ları.
from app.api.routes.incidents import router as incidents_router
from app.api.routes.review import router as review_router
# Dashboard istatistik route'ları.
from app.api.routes.stats import router as stats_router
from app.api.routes.uploads import router as uploads_router
from app.api.routes.pentest import router as pentest_router
# Red team / pentester streaming copilot route'ları.
from app.api.routes.red_team import router as red_team_router
# AI Security Agent route'ları.
from app.api.routes.agent import router as agent_router
# Detection engineering (SIGMA, compliance, anomaly) route'ları.
from app.api.routes.sigma import router as sigma_router
# Ayarları tek yerden okumak için kendi yazdığımız fonksiyonu alıyoruz.
from app.core.config import get_settings


# `def` Python'da fonksiyon tanımlamak için kullanılır.
# `create_app` ismini biz verdik; anlamı "uygulamayı oluştur".
# `-> FastAPI` bu fonksiyonun sonunda bir FastAPI nesnesi döndürmesini beklediğimizi söyler.
def create_app() -> FastAPI:
    # Fonksiyonu çağırıp ayarları alıyoruz.
    settings = get_settings()

    # `FastAPI(...)` ile backend uygulamasının kendisini oluşturuyoruz.
    app = FastAPI(
        # Başlık, otomatik API dokümantasyonunda görünür.
        title=settings.app_name,
        # Bu uygulamanın sürümü.
        version="0.1.0",
        # Uygulamanın kısa açıklaması.
        description="Security incident triage backend for local portfolio development.",
    )

    # Middleware, istek ile uygulama arasına giren yardımcı katmandır.
    app.add_middleware(
        # Kullanacağımız middleware türü CORS middleware.
        CORSMiddleware,
        # Bu adreslerden gelen frontend isteklerine izin ver.
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        # Gerekirse cookie/auth gibi kimlik bilgilerine de izin ver.
        allow_credentials=True,
        # Tüm HTTP methodlarına izin ver: GET, POST, PUT, DELETE...
        allow_methods=["*"],
        # Tüm header'lara izin ver.
        allow_headers=["*"],
    )

    # `health.py` içindeki route'ları uygulamaya ekliyoruz.
    app.include_router(health_router)
    # Explanation üretme route'larını da ekliyoruz.
    app.include_router(explain_router)
    # Filtre seçenek route'larını da ekliyoruz.
    app.include_router(filters_router)
    # Incident route'larını da ekliyoruz.
    app.include_router(incidents_router)
    # Upload edilen gerçek log route'larını da ekliyoruz.
    app.include_router(uploads_router)
    # Analyst review route'larını da ekliyoruz.
    app.include_router(review_router)
    # Stats route'larını da ekliyoruz.
    app.include_router(stats_router)
    # Red team copilot route'larını da ekliyoruz.
    app.include_router(red_team_router)
    app.include_router(pentest_router)
    # AI Security Agent route'larını da ekliyoruz.
    app.include_router(agent_router)
    # Detection engineering route'larını da ekliyoruz.
    app.include_router(sigma_router)
    # Fonksiyonun sonunda oluşturduğumuz uygulamayı geri veriyoruz.
    return app


# Dosya import edildiğinde gerçek FastAPI uygulaması burada oluşturulur.
app = create_app()
