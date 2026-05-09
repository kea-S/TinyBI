const fallbackApiBaseUrl = "/api"

function trimTrailingSlash(value: string) {
  return value.replace(/\/+$/, "")
}

export const apiBaseUrl = trimTrailingSlash(
  import.meta.env.VITE_API_BASE_URL || fallbackApiBaseUrl
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

export type QueryRequest = {
  question: string
  model?: string
  local?: boolean
}

export type QueryResponse = {
  sql: string
  data: Record<string, unknown>[]
  explanation?: string | null
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
