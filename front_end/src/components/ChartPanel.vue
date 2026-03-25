<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { EChartsOption, EChartsType } from '@/utils/echarts'

const props = defineProps<{
  title: string
  description: string
  option: EChartsOption
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const renderError = ref<string | null>(null)

let chart: EChartsType | null = null
let echartsModule: typeof import('@/utils/echarts') | null = null

async function ensureChart() {
  if (!containerRef.value) {
    return
  }

  if (!echartsModule) {
    echartsModule = await import('@/utils/echarts')
  }

  if (!chart) {
    const existingInstance = echartsModule.getInstanceByDom(containerRef.value)
    chart = existingInstance || echartsModule.init(containerRef.value)
  }
}

async function renderChart() {
  try {
    renderError.value = null
    await ensureChart()

    if (!chart) {
      return
    }

    chart.setOption(props.option, true)
    chart.resize()
  } catch (error) {
    renderError.value = error instanceof Error ? error.message : '图表加载失败'
  }
}

function resizeChart() {
  chart?.resize()
}

onMounted(async () => {
  await nextTick()
  await renderChart()
  window.addEventListener('resize', resizeChart)
})

watch(
  () => props.option,
  async () => {
    await nextTick()
    await renderChart()
  },
  { deep: true },
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
  chart = null
})
</script>

<template>
  <article class="section-card chart-card">
    <div class="chart-head">
      <h3>{{ title }}</h3>
      <p>{{ description }}</p>
    </div>

    <p class="chart-tip">左右滚动可查看完整图表</p>

    <div class="chart-scroll">
      <div v-if="renderError" class="chart-fallback">
        <strong>图表加载失败</strong>
        <span>{{ renderError }}</span>
      </div>
      <div v-else ref="containerRef" class="chart-canvas" />
    </div>
  </article>
</template>

<style scoped>
.chart-card {
  display: grid;
  gap: 0.75rem;
  overflow: visible;
}

.chart-head h3 {
  margin: 0;
  font-size: 1.05rem;
  color: var(--text-primary);
}

.chart-head p {
  margin: 0.35rem 0 0;
  color: var(--text-muted);
  line-height: 1.65;
}

.chart-tip {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.9rem;
}

.chart-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 0.3rem;
  scrollbar-gutter: stable both-edges;
}

.chart-canvas,
.chart-fallback {
  width: max(100%, 560px);
  min-width: 560px;
  height: 320px;
}

.chart-fallback {
  display: grid;
  place-content: center;
  gap: 0.5rem;
  border-radius: 18px;
  background: rgba(248, 251, 251, 0.9);
  border: 1px dashed rgba(208, 74, 58, 0.3);
  color: var(--text-secondary);
  text-align: center;
  padding: 1rem;
}

.chart-fallback strong {
  color: #9d3124;
}

@media (max-width: 960px) {
  .chart-canvas,
  .chart-fallback {
    width: max(100%, 680px);
    min-width: 680px;
  }
}

@media (max-width: 768px) {
  .chart-canvas,
  .chart-fallback {
    min-width: 680px;
  }
}
</style>
