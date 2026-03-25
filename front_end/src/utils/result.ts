import type { EChartsOption } from 'echarts'

import type { DisplayMetric, QueryRow, TableColumn } from '@/types/api'
import { formatCompactNumber, formatCurrency, formatDateTime, formatNumber, formatPercent, formatPrice } from '@/utils/format'

export interface ChartConfig {
  key: string
  title: string
  description: string
  option: EChartsOption
}

export const FIELD_LABELS: Record<string, string> = {
  contract_code: '合约代码',
  contract_name: '合约名称',
  latest_price: '最新价',
  price_change: '涨跌额',
  price_change_rate: '涨跌幅',
  volume: '成交量',
  turnover: '成交额',
  position_volume: '持仓量',
  strike_price: '行权价',
  remain_days: '剩余天数',
  position_change: '持仓变化',
  settlement_price_yesterday: '昨结价',
  open_price_today: '今开价',
  etf_type: '标的',
  create_time: '更新时间',
}

const HIDDEN_FIELDS = new Set(['id'])
const PRICE_FIELDS = new Set(['latest_price', 'price_change', 'strike_price', 'settlement_price_yesterday', 'open_price_today'])
const PERCENT_FIELDS = new Set(['price_change_rate'])
const CURRENCY_FIELDS = new Set(['turnover'])
const INTEGER_FIELDS = new Set(['volume', 'position_volume', 'position_change', 'remain_days'])

const FIELD_ORDER = [
  'contract_name',
  'contract_code',
  'latest_price',
  'price_change_rate',
  'price_change',
  'volume',
  'position_volume',
  'turnover',
  'strike_price',
  'remain_days',
  'position_change',
  'settlement_price_yesterday',
  'open_price_today',
  'etf_type',
  'create_time',
]

function asNumber(value: QueryRow[string]) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : undefined
  }
  return undefined
}

function getNumericValues(rows: QueryRow[], key: string) {
  return rows
    .map((row) => asNumber(row[key]))
    .filter((value): value is number => typeof value === 'number')
}

function sumField(rows: QueryRow[], key: string) {
  const values = getNumericValues(rows, key)
  if (!values.length) {
    return undefined
  }
  return values.reduce((total, item) => total + item, 0)
}

function averageField(rows: QueryRow[], key: string) {
  const values = getNumericValues(rows, key)
  if (!values.length) {
    return undefined
  }
  return values.reduce((total, item) => total + item, 0) / values.length
}

function topRowsByField(rows: QueryRow[], key: string, size = 10, byAbsolute = false) {
  return rows
    .filter((row) => typeof asNumber(row[key]) === 'number' && typeof row.contract_name === 'string')
    .sort((left, right) => {
      const leftValue = asNumber(left[key]) || 0
      const rightValue = asNumber(right[key]) || 0
      return byAbsolute ? Math.abs(rightValue) - Math.abs(leftValue) : rightValue - leftValue
    })
    .slice(0, size)
}

function inferOptionType(contractName: string | undefined) {
  if (!contractName) {
    return '未知'
  }
  if (contractName.includes('购')) {
    return '认购'
  }
  if (contractName.includes('沽')) {
    return '认沽'
  }
  return '未知'
}

function buildBarOption(
  rows: QueryRow[],
  key: string,
  color: string,
  formatter: (value: number) => string,
  colorByValue?: (value: number) => string,
): EChartsOption {
  const labels = rows.map((row) => String(row.contract_name))
  const values = rows.map((row) => asNumber(row[key]) || 0)

  return {
    grid: { top: 24, right: 88, bottom: 12, left: 24, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (value) => formatter(Number(value)),
    },
    xAxis: {
      type: 'value',
      min: (range: { min: number }) => (range.min < 0 ? range.min * 1.15 : 0),
      max: (range: { max: number }) => (range.max > 0 ? range.max * 1.15 : 0),
      axisLabel: { color: '#52607a' },
      splitLine: { lineStyle: { color: 'rgba(82, 96, 122, 0.12)' } },
    },
    yAxis: {
      type: 'category',
      data: labels,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: {
        color: '#172033',
        width: 180,
        overflow: 'truncate',
      },
    },
    series: [
      {
        type: 'bar',
        data: values,
        barWidth: 18,
        itemStyle: {
          borderRadius: [0, 8, 8, 0],
          color: (params: { value: number }) => (colorByValue ? colorByValue(params.value) : color),
        },
        label: {
          show: true,
          position: 'inside',
          align: 'center',
          verticalAlign: 'middle',
          color: '#ffffff',
          fontWeight: 700,
          formatter: (params: { value: number }) => formatter(params.value),
        },
      },
    ],
  }
}

export function getDisplayColumns(rows: QueryRow[]): TableColumn[] {
  const keySet = new Set<string>()
  rows.forEach((row) => {
    Object.keys(row).forEach((key) => {
      if (!HIDDEN_FIELDS.has(key)) {
        keySet.add(key)
      }
    })
  })

  const keys = Array.from(keySet)
  const orderedKeys = [
    ...FIELD_ORDER.filter((key) => keys.includes(key)),
    ...keys.filter((key) => !FIELD_ORDER.includes(key)).sort(),
  ]

  return orderedKeys.map((key) => ({
    key,
    label: FIELD_LABELS[key] || key.replaceAll('_', ' '),
    align: PRICE_FIELDS.has(key) || PERCENT_FIELDS.has(key) || CURRENCY_FIELDS.has(key) || INTEGER_FIELDS.has(key) ? 'right' : 'left',
  }))
}

export function formatCell(field: string, value: QueryRow[string]) {
  if (value === null || value === undefined || value === '') {
    return '--'
  }

  const numeric = asNumber(value)
  if (typeof numeric === 'number') {
    if (PRICE_FIELDS.has(field)) {
      return formatPrice(numeric)
    }
    if (PERCENT_FIELDS.has(field)) {
      return formatPercent(numeric)
    }
    if (CURRENCY_FIELDS.has(field)) {
      return formatCurrency(numeric)
    }
    if (INTEGER_FIELDS.has(field)) {
      return field === 'remain_days' ? `${formatNumber(numeric)} 天` : formatNumber(numeric)
    }
  }

  if (field === 'create_time' && typeof value === 'string') {
    return formatDateTime(value)
  }

  return String(value)
}

export function buildAnswerText(query: string, rows: QueryRow[], resultMode: 'detail' | 'list' = 'list') {
  if (!rows.length) {
    return `没有查到与“${query}”直接匹配的结果。可以补充认购/认沽、到期时间或成交量阈值，让条件更具体。`
  }

  if (rows.length === 1) {
    const row = rows[0]
    const contractName = String(row.contract_name || '目标合约')
    const latestPrice = typeof asNumber(row.latest_price) === 'number' ? `最新价 ${formatPrice(asNumber(row.latest_price) || 0)}` : null
    const changeRate = typeof asNumber(row.price_change_rate) === 'number' ? `涨跌幅 ${formatPercent(asNumber(row.price_change_rate) || 0)}` : null
    const volume = typeof asNumber(row.volume) === 'number' ? `成交量 ${formatNumber(asNumber(row.volume) || 0)}` : null
    const position = typeof asNumber(row.position_volume) === 'number' ? `持仓量 ${formatNumber(asNumber(row.position_volume) || 0)}` : null
    const remainDays = typeof asNumber(row.remain_days) === 'number' ? `剩余 ${formatNumber(asNumber(row.remain_days) || 0)} 天到期` : null
    const segments = [latestPrice, changeRate, volume, position, remainDays].filter(Boolean)

    if (resultMode === 'detail') {
      return `已定位到 ${contractName} 的完整信息${segments.length ? `，当前重点包括 ${segments.join('、')}` : ''}，下方展示该期权的全部字段。`
    }

    return `为你定位到 ${contractName}${segments.length ? `，重点包括 ${segments.join('、')}` : ''}。`
  }

  const averagePrice = averageField(rows, 'latest_price')
  const totalVolume = sumField(rows, 'volume')
  const totalPosition = sumField(rows, 'position_volume')
  const topVolume = topRowsByField(rows, 'volume', 1)[0]

  const segments = [`共找到 ${formatNumber(rows.length)} 条合约`]
  if (typeof averagePrice === 'number') {
    segments.push(`平均最新价 ${formatPrice(averagePrice)}`)
  }
  if (typeof totalVolume === 'number') {
    segments.push(`累计成交量 ${formatCompactNumber(totalVolume)}`)
  }
  if (typeof totalPosition === 'number') {
    segments.push(`累计持仓量 ${formatCompactNumber(totalPosition)}`)
  }
  if (topVolume?.contract_name) {
    segments.push(`成交最活跃的是 ${String(topVolume.contract_name)}`)
  }

  return `${segments.join('，')}。`
}

export function buildMetrics(rows: QueryRow[]): DisplayMetric[] {
  if (!rows.length) {
    return []
  }

  const metrics: DisplayMetric[] = [
    {
      label: '结果数量',
      value: `${formatNumber(rows.length)} 条`,
    },
  ]

  const averagePrice = averageField(rows, 'latest_price')
  if (typeof averagePrice === 'number') {
    metrics.push({
      label: '平均最新价',
      value: formatPrice(averagePrice),
    })
  }

  const totalVolume = sumField(rows, 'volume')
  if (typeof totalVolume === 'number') {
    metrics.push({
      label: '总成交量',
      value: formatCompactNumber(totalVolume),
    })
  }

  const totalPosition = sumField(rows, 'position_volume')
  if (typeof totalPosition === 'number') {
    metrics.push({
      label: '总持仓量',
      value: formatCompactNumber(totalPosition),
    })
  }

  const averageChangeRate = averageField(rows, 'price_change_rate')
  if (typeof averageChangeRate === 'number') {
    metrics.push({
      label: '平均涨跌幅',
      value: formatPercent(averageChangeRate),
      tone: averageChangeRate > 0 ? 'rise' : averageChangeRate < 0 ? 'fall' : 'neutral',
    })
  }

  return metrics
}

export function buildCharts(rows: QueryRow[]): ChartConfig[] {
  if (rows.length < 2) {
    return []
  }

  const charts: ChartConfig[] = []

  const topVolumeRows = topRowsByField(rows, 'volume')
  if (topVolumeRows.length > 1) {
    charts.push({
      key: 'volume',
      title: '成交量 Top 合约',
      description: '按当前结果里的成交量排序，快速识别最活跃的期权合约。',
      option: buildBarOption(topVolumeRows, 'volume', '#0f766e', (value) => formatCompactNumber(value)),
    })
  }

  const topPositionRows = topRowsByField(rows, 'position_volume')
  if (topPositionRows.length > 1) {
    charts.push({
      key: 'position-volume',
      title: '持仓量 Top 合约',
      description: '持仓量越高，通常代表该合约的关注度和存量仓位越高。',
      option: buildBarOption(topPositionRows, 'position_volume', '#1d4ed8', (value) => formatCompactNumber(value)),
    })
  }

  const topChangeRows = topRowsByField(rows, 'price_change_rate', 10, true)
  if (topChangeRows.length > 1) {
    charts.push({
      key: 'change-rate',
      title: '涨跌幅分布',
      description: '对比本次结果里涨跌幅最显著的合约，红涨绿跌。',
      option: buildBarOption(
        topChangeRows,
        'price_change_rate',
        '#d04a3a',
        (value) => formatPercent(value),
        (value) => (value >= 0 ? '#d04a3a' : '#0f9f6f'),
      ),
    })
  }

  const strikeRows = rows
    .filter((row) => typeof asNumber(row.strike_price) === 'number' && typeof asNumber(row.latest_price) === 'number' && typeof row.contract_name === 'string')
    .slice(0, 24)

  if (strikeRows.length > 1) {
    charts.push({
      key: 'strike-vs-price',
      title: '行权价与最新价对照',
      description: '观察查询结果中行权价和最新价的相对分布。',
      option: {
        grid: { top: 24, right: 16, bottom: 28, left: 18, containLabel: true },
        tooltip: {
          trigger: 'item',
          formatter: (params: { data: [number, number, string] }) => {
            const [strikePrice, latestPrice, name] = params.data
            return `${name}<br/>行权价：${formatPrice(strikePrice)}<br/>最新价：${formatPrice(latestPrice)}`
          },
        },
        xAxis: {
          type: 'value',
          name: '行权价',
          nameTextStyle: { color: '#52607a' },
          axisLabel: { color: '#52607a' },
          splitLine: { lineStyle: { color: 'rgba(82, 96, 122, 0.12)' } },
        },
        yAxis: {
          type: 'value',
          name: '最新价',
          nameTextStyle: { color: '#52607a' },
          axisLabel: { color: '#52607a' },
          splitLine: { lineStyle: { color: 'rgba(82, 96, 122, 0.12)' } },
        },
        series: [
          {
            type: 'scatter',
            symbolSize: 14,
            data: strikeRows.map((row) => [
              asNumber(row.strike_price) || 0,
              asNumber(row.latest_price) || 0,
              String(row.contract_name),
            ]),
            itemStyle: {
              color: '#d97706',
              shadowBlur: 12,
              shadowColor: 'rgba(217, 119, 6, 0.18)',
            },
          },
        ],
      },
    })
  }

  const typeCounter = new Map<string, number>()
  rows.forEach((row) => {
    const type = inferOptionType(typeof row.contract_name === 'string' ? row.contract_name : undefined)
    typeCounter.set(type, (typeCounter.get(type) || 0) + 1)
  })

  if (typeCounter.size > 1 && typeCounter.has('认购') && typeCounter.has('认沽')) {
    charts.push({
      key: 'option-type',
      title: '认购 / 认沽占比',
      description: '统计本次结果里认购和认沽合约的数量分布。',
      option: {
        tooltip: { trigger: 'item' },
        legend: { bottom: 0, textStyle: { color: '#52607a' } },
        series: [
          {
            type: 'pie',
            radius: ['42%', '70%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 10,
              borderColor: '#fff',
              borderWidth: 4,
            },
            label: {
              show: true,
              formatter: '{b}: {d}%',
              color: '#172033',
            },
            data: [
              { value: typeCounter.get('认购') || 0, name: '认购', itemStyle: { color: '#d04a3a' } },
              { value: typeCounter.get('认沽') || 0, name: '认沽', itemStyle: { color: '#0f9f6f' } },
            ],
          },
        ],
      },
    })
  }

  return charts.slice(0, 4)
}
