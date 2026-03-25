<script setup lang="ts">
defineProps<{
  query: string
  total: number
  answer: string
  queryTime: string | null
}>()
</script>

<template>
  <section class="section-card answer-card">
    <div class="section-head">
      <div>
        <span class="section-kicker">查询结果</span>
        <h2>围绕“{{ query }}”的回答</h2>
      </div>
      <div class="answer-badges">
        <span class="status-chip">{{ total }} 条记录</span>
        <span v-if="queryTime" class="status-chip subtle">{{ queryTime }}</span>
      </div>
    </div>

    <p class="answer-text">{{ answer }}</p>
  </section>
</template>

<style scoped>
.answer-card {
  display: grid;
  gap: 0.85rem;
}

.answer-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  padding: 0.45rem 0.8rem;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.1);
  color: #0f766e;
  font-size: 0.9rem;
  font-weight: 600;
}

.status-chip.subtle {
  background: rgba(116, 143, 166, 0.1);
  color: var(--text-muted);
}

.answer-text {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.02rem;
  line-height: 1.9;
}
</style>
