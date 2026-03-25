export type Primitive = string | number | boolean | null

export interface ApiResponse<T> {
  code: number
  msg: string
  data: T
}

export interface DataStatus {
  latest_update_time: string | null
  latest_record_count: number
}

export interface CrawlResult extends DataStatus {
  total: number
}

export interface QueryRow {
  [key: string]: Primitive
}

export interface QueryResult {
  normalized_text: string
  core_need: string | null
  sql: string
  rows: QueryRow[]
  total: number
  result_mode: 'detail' | 'list'
}

export interface FeedbackMessage {
  type: 'success' | 'error' | 'info'
  message: string
}

export interface DisplayMetric {
  label: string
  value: string
  tone?: 'neutral' | 'rise' | 'fall'
}

export interface TableColumn {
  key: string
  label: string
  align?: 'left' | 'center' | 'right'
}
