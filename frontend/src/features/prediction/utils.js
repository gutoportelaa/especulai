const TITLE_CASE_EXCEPTIONS = ['do', 'da', 'dos', 'das', 'de']

const toNumber = (value, parser = parseFloat) => {
  const num = parser(value)
  return Number.isFinite(num) ? num : 0
}

const titleCase = (value) => {
  return value
    .toLowerCase()
    .split(' ')
    .filter(Boolean)
    .map((word, index) => {
      if (index !== 0 && TITLE_CASE_EXCEPTIONS.includes(word)) return word
      return word.charAt(0).toUpperCase() + word.slice(1)
    })
    .join(' ')
}

export function normalizePredictionPayload(formData) {
  const area = toNumber(formData.area)
  const quartos = toNumber(formData.quartos, parseInt)
  const banheiros = toNumber(formData.banheiros, parseInt)
  const tipo = (formData.tipo || 'apartamento').toLowerCase()

  return {
    area,
    quartos,
    banheiros,
    tipo,
    bairro: titleCase(formData.bairro || ''),
    cidade: titleCase(formData.cidade || '')
  }
}

