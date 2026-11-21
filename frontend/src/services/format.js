const inteiro = new Intl.NumberFormat('pt-BR')
const decimal = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 })
const data = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
const moedas = {
  'US Dollar': 'USD',
  Euro: 'EUR',
  'UK Pound': 'GBP',
  'Brazil Real': 'BRL',
  'Canadian Dollar': 'CAD',
  'Australian Dollar': 'AUD',
  'Swiss Franc': 'CHF',
  Yen: 'JPY',
  Yuan: 'CNY',
  Rupee: 'INR',
  'Mexican Peso': 'MXN',
}

export const num = (value) => (value == null ? '—' : inteiro.format(value))
export const pct = (value) => decimal.format(value * 100) + '%'
const pontuacao = new Intl.NumberFormat('pt-BR', { maximumSignificantDigits: 4 })
const pontuacaoPequena = new Intl.NumberFormat('pt-BR', {
  notation: 'scientific',
  maximumSignificantDigits: 4,
})
export const score = (value) => {
  if (value == null) return '—'
  return (value > 0 && value < 0.0001 ? pontuacaoPequena : pontuacao).format(value)
}
export const instante = (value) => data.format(new Date(value))
export const codigo = (prefixo, id) => prefixo + '-' + String(id).padStart(3, '0')
export function duracao(minutos) {
  const dias = Math.floor(minutos / 1440)
  const horas = Math.floor(minutos / 60) % 24
  const partes = [
    dias && dias + ' d',
    horas && horas + ' h',
    minutos % 60 && (minutos % 60) + ' min',
  ]
  return partes.filter(Boolean).join(' ') || '0 min'
}

export function valor(amount, moeda) {
  const currency = moedas[moeda]
  return currency
    ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency }).format(amount)
    : decimal.format(amount) + ' ' + moeda
}

export const volume = (totais) =>
  Object.entries(totais || {})
    .map(([m, v]) => valor(v, m))
    .join(' · ') || '—'
