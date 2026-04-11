# Bu dosya tarih-saat filtrelerini güvenli biçimde normalize etmek için kullanılır.

from datetime import UTC, datetime


# Dışarıdan gelen tarih-saat değerini UTC aware hale getir.
def normalize_optional_datetime(value: datetime | None) -> datetime | None:
    # Hiç değer yoksa olduğu gibi None döndür.
    if value is None:
        return None

    # Tarayıcıdaki datetime-local input'lar timezone taşımayabilir.
    # Böyle bir durumda değeri UTC kabul ederek karşılaştırma hatasını önlüyoruz.
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    # Timezone bilgisi varsa tek standarda çekmek için UTC'ye çeviriyoruz.
    return value.astimezone(UTC)
