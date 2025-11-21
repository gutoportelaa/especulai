import { apiFetch } from './client'

export function predictImovel(payload) {
  return apiFetch('/predict', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

