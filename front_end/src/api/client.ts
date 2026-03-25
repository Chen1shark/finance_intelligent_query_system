import type { ApiResponse, CrawlResult, DataStatus, QueryResult } from '@/types/api'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')
const DEFAULT_TIMEOUT = 30_000

interface RequestOptions extends RequestInit {
  timeoutMs?: number
}

async function requestApiResponse<T>(path: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), options.timeoutMs ?? DEFAULT_TIMEOUT)

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    })

    const raw = await response.text()
    const payload = raw ? JSON.parse(raw) : null

    if (!response.ok) {
      const message = payload?.detail || payload?.msg || `请求失败（${response.status}）`
      throw new Error(message)
    }

    const data = payload as ApiResponse<T> | null
    if (!data || typeof data.code !== 'number') {
      throw new Error('接口返回格式不正确')
    }

    return data
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('请求超时，请稍后重试')
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
  }
}

async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const data = await requestApiResponse<T>(path, options)
  if (data.code !== 200) {
    throw new Error(data.msg || '业务处理失败')
  }
  return data.data
}

export function fetchDataStatus() {
  return requestJson<DataStatus>('/api/data_status')
}

export function crawlLatestData() {
  return requestApiResponse<CrawlResult>('/api/crawl_50etf', { method: 'GET', timeoutMs: 180_000 })
}

export function queryByText(text: string) {
  return requestJson<QueryResult>('/api/query', {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
}
