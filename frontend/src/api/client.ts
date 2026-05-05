// Bu dosya backend'e istek atmak için ortak fetch yardımcısını içerir.

// Vite ortam değişkeninden backend adresini alıyoruz.
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

async function buildApiError(response: Response): Promise<Error> {
  let detail = `${response.status} ${response.statusText}`

  try {
    const payload = (await response.json()) as { detail?: string }
    if (payload.detail) {
      detail = payload.detail
    }
  } catch {
    // Bazı endpoint'ler JSON dönmeyebilir; bu durumda varsayılan mesajı koruyoruz.
  }

  return new Error(`API request failed: ${detail}`)
}

// Verilen endpoint'e GET isteği atıp sonucu JSON olarak döndür.
export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)

  // HTTP hatası varsa anlaşılır bir mesaj üret.
  if (!response.ok) {
    throw await buildApiError(response)
  }

  return (await response.json()) as T
}

// Verilen endpoint'e POST isteği atıp sonucu JSON olarak döndür.
export async function apiPost<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw await buildApiError(response)
  }

  return (await response.json()) as T
}

// JSON body ile POST isteği atmak için ortak yardımcı.
export async function apiPostJson<T, B>(path: string, body: B): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw await buildApiError(response)
  }

  return (await response.json()) as T
}

// JSON body ile PUT isteği atmak için ortak yardımcı.
export async function apiPut<T, B>(path: string, body: B): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw await buildApiError(response)
  }

  return (await response.json()) as T
}
