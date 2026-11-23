// Empty in dev: Vite proxies /api to Django. Set to the backend origin in production.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  status: number
  body: unknown

  constructor(status: number, body: unknown) {
    super(`API request failed with ${status}`)
    this.status = status
    this.body = body
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, init)
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, body)
  return body as T
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path)
}

export function apiPost<T>(path: string, data: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

// DRF errors are either {detail: "..."} or field errors {field: ["..."] | {nested: [...]}}.
function messagesIn(value: unknown): string[] {
  if (typeof value === 'string') return [value]
  if (Array.isArray(value)) return value.flatMap(messagesIn)
  if (value && typeof value === 'object') return Object.values(value).flatMap(messagesIn)
  return []
}

export function apiErrorMessage(error: Error): string {
  if (!(error instanceof ApiError)) return 'Could not reach the server. Check your connection and try again.'
  return messagesIn(error.body).join(' ') || `Something went wrong (HTTP ${error.status}).`
}
