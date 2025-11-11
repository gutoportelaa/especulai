import { useState } from 'react'

export function usePrediction() {
  const [formData, setFormData] = useState({
    area: '',
    quartos: '',
    banheiros: '',
    tipo: '',
    bairro: '',
    cidade: ''
  })
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
      const res = await fetch('http://localhost:8000/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          area: parseFloat(formData.area),
          quartos: parseInt(formData.quartos),
          banheiros: parseInt(formData.banheiros),
          tipo: formData.tipo,
          bairro: formData.bairro,
          cidade: formData.cidade
        })
      })
      
      if (!res.ok) throw new Error('Erro ao obter predição')
      const data = await res.json()
      setPrediction(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setFormData({
      area: '',
      quartos: '',
      banheiros: '',
      tipo: '',
      bairro: '',
      cidade: ''
    })
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

