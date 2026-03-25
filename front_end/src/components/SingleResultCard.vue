<script setup lang="ts">
import { computed } from 'vue'

import type { QueryRow } from '@/types/api'
import { formatCell, getDisplayColumns } from '@/utils/result'

const props = defineProps<{
  row: QueryRow
}>()

const keyStats = computed(() => [
  { key: 'latest_price', label: '最新价' },
  { key: 'price_change_rate', label: '涨跌幅' },
  { key: 'volume', label: '成交量' },
  { key: 'position_volume', label: '持仓量' },
])

const detailColumns = computed(() =>
  getDisplayColumns([props.row]).filter((column) => !['contract_name', 'contract_code'].includes(column.key)),
)

const optionTone = computed(() => {
  const priceChangeRate = props.row.price_change_rate
  if (typeof priceChangeRate === 'number') {
    if (priceChangeRate > 0) {
      return 'rise'
    }
    if (priceChangeRate < 0) {
      return 'fall'
    }
  }
  return 'neutral'
})

const optionType = computed(() => {
  const contractName = typeof props.row.contract_name === 'string' ? props.row.contract_name : ''
  if (contractName.includes('购')) {
    return '认购'
  }
  if (contractName.includes('沽')) {
    return '认沽'
  }
  return '50ETF 合约'
})
</script>

<template>
  <section class="section-card detail-card">
    <div class="detail-head">
      <div>
        <span class="section-kicker">单合约详情</span>
        <h2>{{ row.contract_name || '目标合约' }}</h2>
        <p class="detail-code">{{ row.contract_code || '--' }}</p>
      </div>
      <span class="detail-badge" :class="optionTone">{{ optionType }}</span>
    </div>

    <div class="detail-stats">
      <article v-for="stat in keyStats" :key="stat.key" class="detail-stat">
        <span>{{ stat.label }}</span>
        <strong>{{ formatCell(stat.key, row[stat.key]) }}</strong>
      </article>
    </div>

    <div class="detail-grid">
      <div v-for="column in detailColumns" :key="column.key" class="detail-item">
        <span>{{ column.label }}</span>
        <strong>{{ formatCell(column.key, row[column.key]) }}</strong>
      </div>
    </div>
  </section>
</template>

<style scoped>
.detail-card {
  display: grid;
  gap: 1.25rem;
}

.detail-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.detail-head h2 {
  margin: 0.45rem 0 0.25rem;
  font-size: clamp(1.55rem, 3vw, 2.2rem);
  line-height: 1.15;
}

.detail-code {
  margin: 0;
  color: var(--text-muted);
}

.detail-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.55rem 0.85rem;
  border-radius: 999px;
  background: rgba(116, 143, 166, 0.12);
  color: var(--text-primary);
  font-weight: 700;
}

.detail-badge.rise {
  background: rgba(208, 74, 58, 0.12);
  color: var(--rise-color);
}

.detail-badge.fall {
  background: rgba(15, 159, 111, 0.12);
  color: var(--fall-color);
}

.detail-stats {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.detail-stat {
  padding: 1rem 1.05rem;
  border-radius: 18px;
  background: rgba(247, 250, 251, 0.92);
  border: 1px solid rgba(116, 143, 166, 0.12);
}

.detail-stat span,
.detail-item span {
  display: block;
  margin-bottom: 0.45rem;
  color: var(--text-muted);
  font-size: 0.9rem;
}

.detail-stat strong {
  font-size: 1.2rem;
  color: var(--text-primary);
}

.detail-grid {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.detail-item {
  padding: 1rem 1.05rem;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(116, 143, 166, 0.1);
}

.detail-item strong {
  color: var(--text-primary);
}
</style>
