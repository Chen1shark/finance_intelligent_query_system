<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { crawlLatestData, fetchDataStatus, queryByText } from '@/api/client'
import AnswerPanel from '@/components/AnswerPanel.vue'
import ChartPanel from '@/components/ChartPanel.vue'
import MetricsGrid from '@/components/MetricsGrid.vue'
import QueryPanel from '@/components/QueryPanel.vue'
import ResultTable from '@/components/ResultTable.vue'
import SingleResultCard from '@/components/SingleResultCard.vue'
import StatusPanel from '@/components/StatusPanel.vue'
import { QUERY_EXAMPLES } from '@/constants/examples'
import type { DataStatus, FeedbackMessage, QueryResult } from '@/types/api'
import { formatDateTime } from '@/utils/format'
import { buildAnswerText, buildCharts, buildMetrics } from '@/utils/result'

const queryText = ref('')
const status = ref<DataStatus | null>(null)
const statusFeedback = ref<FeedbackMessage | null>(null)
const queryError = ref<string | null>(null)
const queryResult = ref<QueryResult | null>(null)
const lastSubmittedQuery = ref('')
const lastQueryTime = ref<string | null>(null)

const isLoadingStatus = ref(false)
const isRefreshingData = ref(false)
const isQuerying = ref(false)

const rows = computed(() => queryResult.value?.rows ?? [])
const resultMode = computed(() => queryResult.value?.result_mode ?? 'list')
const hasResult = computed(() => queryResult.value !== null)
const hasRows = computed(() => rows.value.length > 0)
const isSingleResult = computed(() => rows.value.length === 1)
const answerText = computed(() => buildAnswerText(lastSubmittedQuery.value, rows.value, resultMode.value))
const metrics = computed(() => buildMetrics(rows.value))
const sql = computed(() => queryResult.value?.sql ?? '')
const charts = computed(() => buildCharts(rows.value))

async function loadStatus(silent = false) {
  if (!silent) {
    isLoadingStatus.value = true
  }

  try {
    status.value = await fetchDataStatus()
    if (!silent) {
      statusFeedback.value = null
    }
  } catch {
    statusFeedback.value = {
      type: 'error',
      message: '读取数据状态失败',
    }
  } finally {
    if (!silent) {
      isLoadingStatus.value = false
    }
  }
}

async function refreshData() {
  if (isRefreshingData.value) {
    return
  }

  isRefreshingData.value = true
  statusFeedback.value = null

  try {
    const response = await crawlLatestData()
    if (response.code === 200) {
      status.value = {
        latest_update_time: response.data.latest_update_time,
        latest_record_count: response.data.latest_record_count,
      }
      statusFeedback.value = {
        type: 'success',
        message: `最新数据已更新，本次共写入 ${response.data.total} 条记录。`,
      }
      return
    }

    if (!status.value) {
      status.value = {
        latest_update_time: response.data.latest_update_time,
        latest_record_count: response.data.latest_record_count,
      }
    }
    statusFeedback.value = {
      type: response.code === 42901 ? 'info' : 'error',
      message: response.msg || '数据更新失败，请稍后重试',
    }
  } catch (err: any) {
    statusFeedback.value = {
      type: 'error',
      message: err?.message || '数据更新失败，请稍后重试',
    }
  } finally {
    isRefreshingData.value = false
  }
}

async function submitQuery(inputText = queryText.value) {
  const content = inputText.trim()
  if (!content || isQuerying.value) {
    return
  }

  queryText.value = content
  isQuerying.value = true
  queryError.value = null
  queryResult.value = null
  lastSubmittedQuery.value = content

  try {
    queryResult.value = await queryByText(content)
    lastQueryTime.value = formatDateTime(new Date().toISOString())
  } catch (error) {
    queryError.value = error instanceof Error ? error.message : '查询失败，请稍后重试'
  } finally {
    isQuerying.value = false
  }
}

function useExample(example: string) {
  queryText.value = example
  void submitQuery(example)
}

onMounted(() => {
  void loadStatus()
})
</script>

<template>
  <div class="dashboard-page">
    <div class="background-orb orb-left" />
    <div class="background-orb orb-right" />

    <main class="page-shell">
      <QueryPanel
        v-model="queryText"
        :is-loading="isQuerying"
        :examples="QUERY_EXAMPLES"
        @submit="submitQuery()"
        @use-example="useExample"
      />

      <section class="result-stack">
        <section v-if="isQuerying" class="section-card loading-card">
          <span class="section-kicker">查询中</span>
          <h2>正在解析自然语言并查询数据库</h2>
          <p>系统会依次完成语义理解、SQL 生成和数据库查询，通常需要几秒钟。</p>
          <div class="loading-bars">
            <span />
            <span />
            <span />
          </div>
        </section>

        <section v-else-if="queryError" class="section-card feedback-card error">
          <span class="section-kicker">查询失败</span>
          <h2>{{ queryError }}</h2>
          <p>可以稍后重试，或换一个更直接的问法，例如“成交量最大的认购期权”。</p>
        </section>

        <template v-else-if="hasResult">
          <section v-if="!hasRows" class="section-card empty-card">
            <span class="section-kicker">没有命中结果</span>
            <h2>当前条件没有返回可展示的数据</h2>
            <p>建议补充认购/认沽、到期时间、成交量或行权价范围，让条件更聚焦。</p>
            <div class="example-list">
              <button v-for="example in QUERY_EXAMPLES.slice(0, 4)" :key="example" class="ghost-chip" type="button" @click="useExample(example)">
                {{ example }}
              </button>
            </div>
          </section>

          <template v-else>
            <AnswerPanel
              :query="lastSubmittedQuery"
              :total="rows.length"
              :answer="answerText"
              :query-time="lastQueryTime"
            />

            <section v-if="sql" class="section-card sql-card">
              <div class="section-head">
                <div>
                  <span class="section-kicker">生成SQL</span>
                  <h2>实际执行的SQL语句</h2>
                </div>
              </div>
              <pre class="sql-code">{{ sql }}</pre>
            </section>

            <SingleResultCard v-if="isSingleResult" :row="rows[0]" />

            <MetricsGrid v-if="metrics.length" :metrics="metrics" />

            <section v-if="charts.length" class="visual-grid">
              <ChartPanel
                v-for="chart in charts"
                :key="chart.key"
                :title="chart.title"
                :description="chart.description"
                :option="chart.option"
              />
            </section>

            <section class="section-card table-card">
              <div class="section-head">
                <div>
                  <span class="section-kicker">结果表格</span>
                  <h2>完整返回数据</h2>
                </div>
                <span class="section-note">{{ rows.length }} 条结果</span>
              </div>
              <ResultTable :rows="rows" />
            </section>
          </template>
        </template>

        <section v-else class="section-card onboarding-card">
          <span class="section-kicker">开始提问</span>
          <h2>直接用自然语言询问 50ETF 期权数据</h2>
          <p>适合直接提问“哪一个最大”“哪些满足条件”“某个区间内有哪些合约”。页面会自动把结果转成摘要、图表和表格。</p>
          <div class="example-list">
            <button v-for="example in QUERY_EXAMPLES" :key="example" class="ghost-chip" type="button" @click="useExample(example)">
              {{ example }}
            </button>
          </div>
        </section>
      </section>

      <StatusPanel
        :latest-update-time="status?.latest_update_time || (isLoadingStatus ? '正在读取…' : null)"
        :latest-record-count="status?.latest_record_count ?? null"
        :is-refreshing="isRefreshingData"
        :feedback="statusFeedback"
        @refresh="refreshData"
      />
    </main>
  </div>
</template>

<style scoped>
.dashboard-page {
  position: relative;
  overflow: hidden;
}

.background-orb {
  position: fixed;
  inset: auto;
  width: 420px;
  height: 420px;
  border-radius: 999px;
  filter: blur(72px);
  pointer-events: none;
  opacity: 0.42;
  z-index: 0;
}

.orb-left {
  top: -120px;
  left: -120px;
  background: rgba(15, 118, 110, 0.18);
}

.orb-right {
  top: 120px;
  right: -120px;
  background: rgba(217, 119, 6, 0.16);
}

.page-shell {
  position: relative;
  z-index: 1;
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 40px 0 56px;
  display: grid;
  gap: 1.25rem;
}

.result-stack {
  display: grid;
  gap: 1.25rem;
}

.visual-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.table-card,
.loading-card,
.feedback-card,
.empty-card,
.onboarding-card {
  display: grid;
  gap: 0.9rem;
}

.table-card {
  overflow: visible;
}

.sql-card {
  background: #f8f9fa;
}

.sql-code {
  margin: 0;
  padding: 1rem;
  background: #1e1e1e;
  color: #d4d4d4;
  border-radius: 8px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9rem;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.loading-card p,
.feedback-card p,
.empty-card p,
.onboarding-card p {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.8;
}

.feedback-card.error {
  border-color: rgba(208, 74, 58, 0.18);
}

.loading-bars {
  display: flex;
  gap: 0.6rem;
  margin-top: 0.25rem;
}

.loading-bars span {
  width: 72px;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(15, 118, 110, 0.16), rgba(15, 118, 110, 0.4));
  animation: pulse 1.2s ease-in-out infinite;
}

.loading-bars span:nth-child(2) {
  animation-delay: 0.16s;
}

.loading-bars span:nth-child(3) {
  animation-delay: 0.32s;
}

.example-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.55;
    transform: scaleX(0.96);
  }
  50% {
    opacity: 1;
    transform: scaleX(1);
  }
}

@media (max-width: 960px) {
  .visual-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-shell {
    width: min(100% - 20px, 1180px);
    padding: 24px 0 40px;
  }
}
</style>
