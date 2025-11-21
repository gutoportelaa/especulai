const DEFAULT_BASE_URL = 'http://localhost:8000'

const API_BASE_URL = import.meta.env.VITE_API_URL?.replace(/\/$/, '') || DEFAULT_BASE_URL

export async function apiFetch(path, options = {}) {
  const url = `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    },
    ...options
  }

  const response = await fetch(url, config)
  const payload = await parseJSON(response)

  if (!response.ok) {
    const message = payload?.detail || payload?.message || 'Erro ao comunicar com o servidor'
    throw new Error(message)
  }

  return payload
}

async function parseJSON(response) {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

