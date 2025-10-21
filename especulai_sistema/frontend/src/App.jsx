import { useState } from 'react'

function App() {
  const [formData, setFormData] = useState({
    area: '', quartos: '', banheiros: '', tipo: '', bairro: '', cidade: ''
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

  return (
    <div>
      <h1>Especulai</h1>
      <form onSubmit={handleSubmit}>
        <input name="area" value={formData.area} onChange={handleChange} placeholder="Área" />
        <input name="quartos" value={formData.quartos} onChange={handleChange} placeholder="Quartos" />
        <input name="banheiros" value={formData.banheiros} onChange={handleChange} placeholder="Banheiros" />
        <input name="tipo" value={formData.tipo} onChange={handleChange} placeholder="Tipo" />
        <input name="bairro" value={formData.bairro} onChange={handleChange} placeholder="Bairro" />
        <input name="cidade" value={formData.cidade} onChange={handleChange} placeholder="Cidade" />
        <button type="submit" disabled={loading}>Enviar</button>
      </form>
      {error && <p>{error}</p>}
      {prediction && (
        <div>
          <p>Preço estimado: R$ {prediction.preco_estimado?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</p>
          <p>Confiança: {prediction.confianca}</p>
        </div>
      )}
    </div>
  )
}

export default App


