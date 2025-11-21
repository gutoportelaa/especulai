import { useState } from 'react'
import { predictImovel } from '../api/prediction'
import { PREDICTION_DEFAULTS } from '../features/prediction/constants'
import { normalizePredictionPayload } from '../features/prediction/utils'

const createDefaultForm = () => ({ ...PREDICTION_DEFAULTS })

export function usePrediction() {
  const [formData, setFormData] = useState(() => createDefaultForm())
  const [prediction, setPrediction] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setPrediction(null)
    
    try {
      const payload = normalizePredictionPayload(formData)
      const data = await predictImovel(payload)
      setPrediction(data)
    } catch (err) {
      setError(err.message || 'Não foi possível obter a predição')
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setFormData(createDefaultForm())
    setPrediction(null)
    setError(null)
  }

  return {
    formData,
    prediction,
    loading,
    error,
    handleChange,
    handleSubmit,
    reset
  }
}

