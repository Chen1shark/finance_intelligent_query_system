<script setup lang="ts">
defineProps<{
  modelValue: string
  isLoading: boolean
  examples: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  submit: []
  useExample: [value: string]
}>()

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    emit('submit')
  }
}
</script>

<template>
  <section class="section-card query-card">
    <div class="section-head">
      <div>
        <span class="section-kicker">自然语言查询</span>
        <h2>告诉系统你想看的 50ETF 期权条件</h2>
      </div>
      <span class="section-note">回车发送，Shift + Enter 换行</span>
    </div>

    <textarea
      class="query-input"
      :value="modelValue"
      placeholder="例如：帮我找一下持仓量最大的认沽期权"
      rows="4"
      :disabled="isLoading"
      @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
      @keydown="handleKeydown"
    />

    <div class="query-actions">
      <button class="primary-button" type="button" :disabled="isLoading || !modelValue.trim()" @click="emit('submit')">
        {{ isLoading ? '正在查询…' : '开始查询' }}
      </button>
      <p class="query-tip">支持自然语言表达排序、阈值、认购/认沽和到期条件。</p>
    </div>

    <div class="example-list">
      <button
        v-for="example in examples"
        :key="example"
        class="ghost-chip"
        type="button"
        :disabled="isLoading"
        @click="emit('useExample', example)"
      >
        {{ example }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.query-card {
  display: grid;
  gap: 1rem;
}

.query-input {
  width: 100%;
  min-height: 144px;
  resize: vertical;
  border: 1px solid rgba(116, 143, 166, 0.24);
  border-radius: 20px;
  padding: 1rem 1.1rem;
  background: rgba(252, 253, 253, 0.94);
  color: var(--text-primary);
  font: inherit;
  line-height: 1.7;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.query-input:focus {
  outline: none;
  border-color: rgba(15, 118, 110, 0.38);
  box-shadow: 0 0 0 4px rgba(15, 118, 110, 0.08);
  transform: translateY(-1px);
}

.query-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.9rem;
}

.query-tip {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.95rem;
}

.example-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}

@media (max-width: 640px) {
  .query-actions {
    align-items: stretch;
  }
}
</style>
