<script setup lang="ts">
import type { DisplayMetric } from '@/types/api'

defineProps<{
  metrics: DisplayMetric[]
}>()
</script>

<template>
  <section class="metrics-grid">
    <article v-for="metric in metrics" :key="metric.label" class="metric-card" :class="metric.tone">
      <span class="metric-label">{{ metric.label }}</span>
      <strong class="metric-value">{{ metric.value }}</strong>
    </article>
  </section>
</template>

<style scoped>
.metrics-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.metric-card {
  padding: 1.15rem 1.2rem;
  border-radius: 20px;
  background: var(--panel-strong);
  border: 1px solid rgba(116, 143, 166, 0.12);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.55);
}

.metric-label {
  display: block;
  margin-bottom: 0.65rem;
  font-size: 0.92rem;
  color: var(--text-muted);
}

.metric-value {
  display: block;
  font-size: 1.4rem;
  color: var(--text-primary);
}

.metric-card.rise .metric-value {
  color: var(--rise-color);
}

.metric-card.fall .metric-value {
  color: var(--fall-color);
}
</style>
