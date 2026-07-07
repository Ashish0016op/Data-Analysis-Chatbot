export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? 'http://localhost:8000'

const TOKEN_STORAGE_KEY = 'dap.backend.token'

type JsonRecord = Record<string, unknown>

interface RequestOptions extends Omit<RequestInit, 'body' | 'headers'> {
  body?: BodyInit | JsonRecord | JsonRecord[]
  headers?: HeadersInit
}

export class ApiError extends Error {
  status?: number
  payload?: unknown

  constructor(message: string, status?: number, payload?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

export function getStoredToken() {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setStoredToken(token: string | null) {
  if (typeof window === 'undefined') return

  if (token) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY)
  }

  window.dispatchEvent(new Event('backend-auth-change'))
}

function getEndpoint(path: string) {
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
}

function isJsonBody(body: RequestOptions['body']) {
  return (
    body !== undefined &&
    body !== null &&
    typeof body !== 'string' &&
    !(body instanceof FormData) &&
    !(body instanceof URLSearchParams) &&
    !(body instanceof Blob) &&
    !(body instanceof ArrayBuffer)
  )
}

async function parseResponse(response: Response) {
  const text = await response.text()
  if (!text) return null

  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    try {
      return JSON.parse(text)
    } catch {
      return text
    }
  }

  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

function extractErrorMessage(payload: unknown, fallback: string) {
  if (!payload) return fallback
  if (typeof payload === 'string') return payload

  if (typeof payload === 'object') {
    const data = payload as JsonRecord
    const message = data.detail ?? data.error ?? data.message
    if (typeof message === 'string') return message
    if (Array.isArray(message)) return message.map(String).join(', ')
  }

  return fallback
}

export async function apiRequest<T = unknown>(path: string, options: RequestOptions = {}) {
  const headers = new Headers(options.headers)
  const token = getStoredToken()
  const body = options.body

  headers.set('Accept', 'application/json')

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const requestBody = isJsonBody(body) ? JSON.stringify(body) : body

  if (isJsonBody(body) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(getEndpoint(path), {
    ...options,
    body: requestBody as BodyInit | undefined,
    credentials: 'include',
    headers,
  })
  const payload = await parseResponse(response)

  if (!response.ok) {
    throw new ApiError(
      extractErrorMessage(payload, `Request failed with status ${response.status}`),
      response.status,
      payload,
    )
  }

  return payload as T
}

function tokenFromPayload(payload: unknown) {
  if (!payload || typeof payload !== 'object') return null

  const data = payload as JsonRecord
  const token =
    data.access_token ??
    data.token ??
    data.auth_token ??
    data.jwt ??
    (typeof data.data === 'object' && data.data
      ? (data.data as JsonRecord).access_token ?? (data.data as JsonRecord).token
      : null)

  return typeof token === 'string' ? token : null
}

export async function login(email: string, password: string) {
  const form = new URLSearchParams()
  form.set('username', email)
  form.set('password', password)

  let payload: unknown

  try {
    payload = await apiRequest('/login', {
      method: 'POST',
      body: form,
    })
  } catch (error) {
    if (!(error instanceof ApiError) || ![400, 415, 422].includes(error.status ?? 0)) {
      throw error
    }

    payload = await apiRequest('/login', {
      method: 'POST',
      body: { email, password },
    })
  }

  setStoredToken(tokenFromPayload(payload))
  return payload
}

export async function register(payload: JsonRecord) {
  return apiRequest('/register', {
    method: 'POST',
    body: payload,
  })
}

export async function getCurrentUser() {
  return apiRequest('/me')
}

export async function logout() {
  try {
    return await apiRequest('/logout', { method: 'POST' })
  } catch (error) {
    if (error instanceof ApiError && error.status === 405) {
      return apiRequest('/logout')
    }
    throw error
  } finally {
    setStoredToken(null)
  }
}

function withContext(payload: JsonRecord, context?: string) {
  return context ? { ...payload, context } : payload
}

export interface BackendQueryResult {
  text: string
  chartHtml: string | null
  imageFile: string | null
  imageFiles: string[]
  htmlContent: string | null
  hasChart: boolean
  raw: unknown
}

function extractEmbeddedHtmlBlocks(text: string) {
  const htmlBlocks: string[] = []
  const patterns = [
    /<div\b[^>]*class=["'][^"']*\btable-responsive\b[^"']*["'][^>]*>[\s\S]*?<\/div>/gi,
    /<table\b[\s\S]*?<\/table>/gi,
  ]

  let cleanedText = text

  for (const pattern of patterns) {
    cleanedText = cleanedText.replace(pattern, (match) => {
      htmlBlocks.push(match)
      return '\n'
    })
  }

  return {
    text: cleanedText.replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim(),
    htmlContent: htmlBlocks.length > 0 ? htmlBlocks.join('\n') : null,
  }
}

export function parseBackendQueryResponse(payload: unknown): BackendQueryResult {
  if (payload === null || payload === undefined) {
    return { text: 'Backend returned an empty response.', chartHtml: null, imageFile: null, imageFiles: [], htmlContent: null, hasChart: false, raw: payload }
  }

  if (typeof payload !== 'object' || Array.isArray(payload)) {
    const parsedText = extractEmbeddedHtmlBlocks(backendResponseToText(payload))

    return {
      text: parsedText.text,
      chartHtml: null,
      imageFile: null,
      imageFiles: [],
      htmlContent: parsedText.htmlContent,
      hasChart: false,
      raw: payload,
    }
  }

  const data = payload as JsonRecord
  const parsedText = extractEmbeddedHtmlBlocks(backendResponseToText(payload))
  const chartHtml =
    typeof data.chart_html === 'string'
      ? data.chart_html
      : typeof data.chartHtml === 'string'
        ? data.chartHtml
        : null
  const imageFile =
    typeof data.image_file === 'string'
      ? data.image_file
      : typeof data.imageFile === 'string'
        ? data.imageFile
        : null
  const imageFiles =
    Array.isArray(data.image_files)
      ? data.image_files.filter((item): item is string => typeof item === 'string')
      : typeof data.imageFiles === 'object' && Array.isArray(data.imageFiles)
        ? data.imageFiles.filter((item): item is string => typeof item === 'string')
        : imageFile
          ? [imageFile]
          : []
  const htmlContent =
    typeof data.html_content === 'string'
      ? data.html_content
      : typeof data.htmlContent === 'string'
        ? data.htmlContent
        : null
  const finalHtmlContent = htmlContent ?? parsedText.htmlContent
  const hasChart = Boolean(data.is_images ?? data.isImages ?? chartHtml ?? imageFile ?? imageFiles.length > 0)

  return { text: parsedText.text, chartHtml, imageFile, imageFiles, htmlContent: finalHtmlContent, hasChart, raw: payload }
}

export async function queryBackend(prompt: string, context?: string) {
  const payloads = [
    withContext({ query: prompt }, context),
    withContext({ question: prompt }, context),
    withContext({ message: prompt }, context),
  ]
  let lastError: unknown

  for (const payload of payloads) {
    try {
      return await apiRequest('/query/', {
        method: 'POST',
        body: payload,
      })
    } catch (error) {
      lastError = error
      if (!(error instanceof ApiError) || ![400, 415, 422].includes(error.status ?? 0)) {
        throw error
      }
    }
  }

  throw lastError
}

export async function clearBackendChat() {
  try {
    return await apiRequest('/clear_chat/', { method: 'POST' })
  } catch (error) {
    if (error instanceof ApiError && error.status === 405) {
      return apiRequest('/clear_chat/')
    }
    throw error
  }
}

export function backendResponseToText(payload: unknown): string {
  if (payload === null || payload === undefined) return 'Backend returned an empty response.'
  if (typeof payload === 'string') return payload
  if (typeof payload === 'number' || typeof payload === 'boolean') return String(payload)

  if (Array.isArray(payload)) {
    return JSON.stringify(payload, null, 2)
  }

  if (typeof payload === 'object') {
    const data = payload as JsonRecord
    const preferredKeys = [
      'answer',
      'response',
      'result',
      'message',
      'content',
      'text',
      'output',
      'analysis',
    ]

    for (const key of preferredKeys) {
      const value = data[key]
      if (value !== undefined) return backendResponseToText(value)
    }

    return JSON.stringify(payload, null, 2)
  }

  return String(payload)
}

export async function getDatasetInfo() {
  return apiRequest('/dataset-info')
}

export function extractArray<T = JsonRecord>(payload: unknown, keys: string[] = []) {
  if (Array.isArray(payload)) return payload as T[]
  if (!payload || typeof payload !== 'object') return []

  const data = payload as JsonRecord
  const arrayKeys = [...keys, 'items', 'data', 'results', 'datasets', 'models', 'reports']

  for (const key of arrayKeys) {
    const value = data[key]
    if (Array.isArray(value)) return value as T[]
  }

  return []
}
