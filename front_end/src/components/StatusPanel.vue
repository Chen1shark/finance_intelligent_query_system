<script setup lang="ts">
import type { FeedbackMessage } from '@/types/api'

defineProps<{
  latestUpdateTime: string | null
  latestRecordCount: number | null
  isRefreshing: boolean
  feedback: FeedbackMessage | null
}>()

defineEmits<{
  refresh: []
}>()
</script>

<template>
  <section class="section-card status-panel">
    <div class="section-head">
      <div>
        <span class="section-kicker">数据更新</span>
        <h2>数据更新与库内最新状态</h2>
      </div>
      <button class="primary-button" type="button" :disabled="isRefreshing" @click="$emit('refresh')">
        {{ isRefreshing ? '正在更新数据…' : '更新数据' }}
      </button>
    </div>

    <p class="status-copy">更新数据，请勿过于频繁</p>

    <div class="status-grid">
      <article class="status-stat">
        <span class="status-label">最近更新时间</span>
        <strong>{{ latestUpdateTime || '尚未同步' }}</strong>
      </article>
      <article class="status-stat">
        <span class="status-label">当前记录数</span>
        <strong>{{ latestRecordCount === null ? '--' : `${latestRecordCount} 条` }}</strong>
      </article>
    </div>

    <p v-if="feedback" class="feedback-banner" :class="feedback.type">
      {{ feedback.message }}
    </p>
  </section>
</template>

<style scoped>
.status-panel {
  display: grid;
  gap: 1rem;
}

.status-copy {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.75;
}

.status-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.status-stat {
  padding: 1.1rem 1.2rem;
  border-radius: 18px;
  background: rgba(248, 251, 251, 0.9);
  border: 1px solid rgba(116, 143, 166, 0.15);
}

.status-label {
  display: block;
  margin-bottom: 0.45rem;
  color: var(--text-muted);
  font-size: 0.92rem;
}

.status-stat strong {
  font-size: 1.15rem;
  color: var(--text-primary);
}
</style>
