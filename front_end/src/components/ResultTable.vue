<script setup lang="ts">
import { computed } from 'vue'

import type { QueryRow } from '@/types/api'
import { formatCell, getDisplayColumns } from '@/utils/result'

const props = defineProps<{
  rows: QueryRow[]
}>()

const columns = computed(() => getDisplayColumns(props.rows))

function getRowKey(row: QueryRow, index: number) {
  return String(row.contract_code || row.contract_name || index)
}
</script>

<template>
  <div class="table-shell">
    <p class="table-tip">左右滚动可查看完整数据</p>
    <table class="result-table">
      <thead>
        <tr>
          <th
            v-for="column in columns"
            :key="column.key"
            :class="column.align"
            :data-field="column.key"
          >
            {{ column.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, rowIndex) in rows" :key="getRowKey(row, rowIndex)">
          <td
            v-for="column in columns"
            :key="column.key"
            :class="column.align"
            :data-field="column.key"
            :title="String(formatCell(column.key, row[column.key]))"
          >
            {{ formatCell(column.key, row[column.key]) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-shell {
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 0.25rem;
  border-radius: 18px;
  border: 1px solid rgba(116, 143, 166, 0.14);
  background: rgba(255, 255, 255, 0.88);
  scrollbar-gutter: stable both-edges;
}

.table-tip {
  margin: 0;
  padding: 0.75rem 1rem 0;
  color: var(--text-muted);
  font-size: 0.9rem;
}

.result-table {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
}

.result-table th,
.result-table td {
  min-width: 108px;
  padding: 0.95rem 1rem;
  border-bottom: 1px solid rgba(116, 143, 166, 0.1);
  color: var(--text-primary);
  font-size: 0.94rem;
  white-space: nowrap;
}

.result-table thead th {
  position: sticky;
  top: 0;
  background: rgba(245, 248, 250, 0.98);
  z-index: 1;
  color: var(--text-muted);
  font-weight: 600;
}

.result-table tbody tr:hover {
  background: rgba(15, 118, 110, 0.04);
}

.result-table th.right,
.result-table td.right {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.result-table th.center,
.result-table td.center {
  text-align: center;
}

.result-table th[data-field='contract_name'],
.result-table td[data-field='contract_name'] {
  min-width: 180px;
  max-width: 260px;
  white-space: normal;
  word-break: break-word;
}

.result-table th[data-field='create_time'],
.result-table td[data-field='create_time'] {
  min-width: 168px;
}

.result-table tbody tr:last-child td {
  border-bottom: none;
}
</style>
