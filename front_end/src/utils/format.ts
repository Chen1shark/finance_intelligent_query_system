export function formatNumber(value: number, maximumFractionDigits = 0) {
  return new Intl.NumberFormat('zh-CN', {
    maximumFractionDigits,
  }).format(value)
}

export function formatDecimal(value: number, digits = 2) {
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
}

export function formatPrice(value: number) {
  return formatDecimal(value, 3)
}

export function formatPercent(value: number) {
  return `${formatDecimal(value, 2)}%`
}

export function formatCurrency(value: number) {
  return `¥${formatNumber(value, 2)}`
}

export function formatCompactNumber(value: number) {
  if (Math.abs(value) >= 100000000) {
    return `${formatDecimal(value / 100000000, 2)} 亿`
  }
  if (Math.abs(value) >= 10000) {
    return `${formatDecimal(value / 10000, 2)} 万`
  }
  return formatNumber(value, 2)
}

export function formatDateTime(value: string) {
  if (!value) {
    return '--'
  }

  const parsed = new Date(value.replace(' ', 'T'))
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(parsed)
}
