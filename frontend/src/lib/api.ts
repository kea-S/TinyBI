const fallbackApiBaseUrl = "/api"

function trimTrailingSlash(value: string) {
  return value.replace(/\/+$/, "")
}

export const apiBaseUrl = trimTrailingSlash(
  import.meta.env.VITE_API_BASE_URL ?? fallbackApiBaseUrl
)

function createApiUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`
  return `${apiBaseUrl}${normalizedPath}`
}

async function readErrorMessage(response: Response) {
  const contentType = response.headers.get("content-type") || ""

  if (contentType.includes("application/json")) {
    const payload = (await response.json()) as { detail?: string }
    if (payload.detail) {
      return payload.detail
    }

    return JSON.stringify(payload)
  }

  return response.text()
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit
): Promise<T | string> {
  const response = await fetch(createApiUrl(path), {
    ...init,
    headers: {
      Accept: "application/json, text/plain;q=0.9, */*;q=0.8",
      ...init?.headers,
    },
  })

  if (!response.ok) {
    const message = await readErrorMessage(response)
    throw new Error(message || `Request failed with status ${response.status}.`)
  }

  const contentType = response.headers.get("content-type") || ""
  if (contentType.includes("application/json")) {
    return (await response.json()) as T
  }

  return response.text()
}

export function pingBackend() {
  return apiRequest<Record<string, unknown>>("/health")
}

export type ColumnVectorIndexEntryPayload = Record<string, unknown>

export type ColumnVectorIndexEntryRequest = {
  entry_id: number
  table_name: string
  column_name: string
  source_key: string
  description?: string | null
  data_format?: string | null
  statistical_type: string
  categorical_values?: Record<string, string[]>
  aliases: string[]
  sample_values: string[]
  payload: ColumnVectorIndexEntryPayload
  references?: string | null
}

export type BatchColumnVectorIndexEntriesRequest = {
  entries: ColumnVectorIndexEntryRequest[]
}

export type BatchColumnVectorIndexResponse = {
  embedding_model: string
  entry_count: number
  table_names: string[]
  vector_index_path: string
  metadata_path: string
}

export function submitDefaultVectorIndexEntries(
  payload: BatchColumnVectorIndexEntriesRequest
) {
  return apiRequest<BatchColumnVectorIndexResponse>("/vector/index-entries/batch", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })
}

export function fetchCurrentVectorIndexEntries() {
  return apiRequest<ColumnVectorIndexEntryRequest[]>("/vector/index-entries/current")
}

export type Message = {
  role: "user" | "assistant"
  content: string
}

export type QueryRequest = {
  messages: Message[]
  model?: string
  local?: boolean
}

export type QueryResponse = {
  message: string
  sql?: string | null
  data?: Record<string, unknown>[] | null
}

export type LocalLLMConfig = {
  model: string
  base_url: string
}

export type RemoteLLMConfig = {
  model: string
  api_key: string
}

export type EmbeddingConfig = {
  model: string
  base_url: string
  api_key: string
}

export type ConfigPayload = {
  active_llm: "local" | "remote"
  local_llm: LocalLLMConfig
  remote_llm: RemoteLLMConfig
  embedding: EmbeddingConfig
}

export type ConfigResponse = {
  configured: boolean
  config: ConfigPayload | null
}

export function fetchEngineConfig() {
  return apiRequest<ConfigResponse>("/config")
}

export function saveEngineConfig(payload: ConfigPayload) {
  return apiRequest<{ success: boolean }>("/config", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })
}

export function submitQuery(payload: QueryRequest) {
  return apiRequest<QueryResponse>("/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })
}

export type OverviewStats = {
  overallAccuracy: number
  meanLatencyMs: number
  meanTokens: number
  totalTokens: number
  lastRun?: string | null
}

export function fetchOverviewStats() {
  return apiRequest<OverviewStats>("/monitoring/overview")
}

export type DifficultyBreakdownStats = {
  difficulty: string
  accuracy: number
  latencyMs: number
  tokens: number
}

export function fetchDifficultyBreakdown() {
  return apiRequest<DifficultyBreakdownStats[]>("/monitoring/difficulty-breakdown")
}

export type DifficultySegregatedStats = {
  provider: string
  difficulty: string
  accuracy: number
  latencyMs: number
  tokens: number
}

export function fetchDifficultySegregated() {
  return apiRequest<DifficultySegregatedStats[]>("/monitoring/difficulty-segregated")
}

export type ProviderComparisonStats = {
  provider: string
  accuracy: number
  tokens: number
  correct: number
  fail: number
  error: number
}

export function fetchProviderComparison() {
  return apiRequest<ProviderComparisonStats[]>("/monitoring/provider-comparison")
}
