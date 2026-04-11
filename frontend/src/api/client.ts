// Bu dosya backend'e istek atmak için ortak fetch yardımcısını içerir.

// Vite ortam değişkeninden backend adresini alıyoruz.
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

// Verilen endpoint'e GET isteği atıp sonucu JSON olarak döndür.
export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)

  // HTTP hatası varsa anlaşılır bir mesaj üret.
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`)
  }

  return (await response.json()) as T
}

// Verilen endpoint'e POST isteği atıp sonucu JSON olarak döndür.
export async function apiPost<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`)
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
    throw new Error(`API request failed: ${response.status} ${response.statusText}`)
  }

  return (await response.json()) as T
}
