import type { ApiEnvelope } from './types'
import { ApiRequestError } from './types'

/** Production / khi chạy FE tách host — trỏ thẳng FastAPI. */
const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000/v1'

function resolveApiBaseUrl(): string {
    const fromEnv = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim()
    if (fromEnv) return fromEnv
    /** Dev: cùng origin + proxy Vite → tránh CORS và dễ chạy song song `npm run dev` + uvicorn. */
    if (import.meta.env.DEV) return '/v1'
    return DEFAULT_API_BASE_URL
}

const API_BASE_URL = resolveApiBaseUrl()
export const HTTP_UNAUTHORIZED_EVENT = 'serene:http-unauthorized'

export function getApiBaseUrl(): string {
    return API_BASE_URL
}

/** Dùng cho `<Audio src>` khi `audio_url` là path tương đối `/v1/...`. */
export function resolveMediaUrl(path: string): string {
    if (path.startsWith('http://') || path.startsWith('https://')) return path
    if (API_BASE_URL.startsWith('http')) {
        const origin = API_BASE_URL.replace(/\/v1\/?$/, '')
        return `${origin}${path.startsWith('/') ? path : `/${path}`}`
    }
    if (typeof window !== 'undefined') {
        return `${window.location.origin}${path.startsWith('/') ? path : `/${path}`}`
    }
    return path
}

let csrfToken: string | null = null
let lastUnauthorizedAt = 0

function readCookie(name: string): string | null {
    if (typeof document === 'undefined') return null
    const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`))
    return match ? decodeURIComponent(match[1]) : null
}

function isEnvelope<T>(value: unknown): value is ApiEnvelope<T> {
    return typeof value === 'object' && value !== null && 'success' in value && 'data' in value
}

async function parseJsonSafely(response: Response): Promise<unknown> {
    try {
        return await response.clone().json()
    } catch {
        return null
    }
}

let isRefreshing = false
let refreshSubscribers: ((error: Error | null) => void)[] = []

function onRefreshed(error: Error | null) {
    refreshSubscribers.forEach((cb) => cb(error))
    refreshSubscribers = []
}

async function fetchWithRetry(url: string, options: RequestInit, path: string): Promise<Response> {
    let response = await fetch(url, options)

    if (
        response.status === 401 &&
        !path.startsWith('/auth/')
    ) {
        if (!isRefreshing) {
            isRefreshing = true
            try {
                const token = await ensureCsrfToken()
                const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'X-CSRF-Token': token,
                    },
                })

                if (refreshResponse.ok) {
                    onRefreshed(null)
                    // Update CSRF token if the original request used it
                    if (options.headers) {
                        const headers = new Headers(options.headers)
                        if (headers.has('X-CSRF-Token')) {
                            headers.set('X-CSRF-Token', await ensureCsrfToken())
                            options.headers = headers
                        }
                    }
                    response = await fetch(url, options)
                } else {
                    const error = new Error('Refresh token expired')
                    onRefreshed(error)
                }
            } catch (error) {
                onRefreshed(error as Error)
            } finally {
                isRefreshing = false
            }
        } else {
            return new Promise<Response>((resolve, reject) => {
                refreshSubscribers.push(async (error) => {
                    if (error) {
                        resolve(response)
                    } else {
                        try {
                            if (options.headers) {
                                const headers = new Headers(options.headers)
                                if (headers.has('X-CSRF-Token')) {
                                    headers.set('X-CSRF-Token', await ensureCsrfToken())
                                    options.headers = headers
                                }
                            }
                            resolve(await fetch(url, options))
                        } catch (err) {
                            reject(err)
                        }
                    }
                })
            })
        }
    }

    return response
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers || {})
    if (!headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json')
    }

    let response: Response
    try {
        response = await fetchWithRetry(`${API_BASE_URL}${path}`, {
            credentials: 'include',
            ...init,
            headers,
        }, path)
    } catch (err) {
        const isNetwork =
            err instanceof TypeError ||
            (err instanceof Error && /Failed to fetch|NetworkError|Load failed/i.test(err.message))
        if (isNetwork) {
            throw new ApiRequestError(
                'Không kết nối được máy chủ API. Hãy bật backend (ví dụ: trong thư mục backend chạy `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`), rồi tải lại trang.',
                { code: 'NETWORK_ERROR', status: 0 },
            )
        }
        throw err
    }

    const payload = await parseJsonSafely(response)

    if (!response.ok) {
        if (response.status === 401 && typeof window !== 'undefined') {
            const now = Date.now()
            // Debounce unauthorized broadcast to avoid event storms when many calls fail together.
            if (now - lastUnauthorizedAt > 1200) {
                lastUnauthorizedAt = now
                window.dispatchEvent(
                    new CustomEvent<{ path: string; status: number }>(HTTP_UNAUTHORIZED_EVENT, {
                        detail: { path, status: response.status },
                    }),
                )
            }
        }

        if (isEnvelope<T>(payload) && payload.error) {
            throw new ApiRequestError(payload.error.message, {
                code: payload.error.code,
                status: response.status,
            })
        }

        throw new ApiRequestError('Không thể kết nối đến máy chủ.', {
            status: response.status,
        })
    }

    if (isEnvelope<T>(payload)) {
        if (!payload.success) {
            throw new ApiRequestError(payload.error?.message || 'Yêu cầu không thành công.', {
                code: payload.error?.code,
                status: response.status,
            })
        }

        if (payload.data === null) {
            throw new ApiRequestError('API không trả về dữ liệu hợp lệ.', {
                status: response.status,
            })
        }

        return payload.data
    }

    return payload as T
}

async function ensureCsrfToken(forceRefresh = false): Promise<string> {
    const tokenFromCookie = readCookie('csrf_token')
    if (!forceRefresh && tokenFromCookie) {
        csrfToken = tokenFromCookie
        return tokenFromCookie
    }
    if (!forceRefresh && csrfToken) return csrfToken
    const data = await request<{ csrf_token: string }>('/auth/csrf-token', { method: 'GET' })
    csrfToken = data.csrf_token
    return csrfToken
}

function resetCsrfToken(): void {
    csrfToken = null
}

async function postWithCsrf<T>(path: string, body?: unknown, init: RequestInit = {}): Promise<T> {
    const token = await ensureCsrfToken()
    const headers = new Headers(init.headers || {})
    headers.set('X-CSRF-Token', token)
    return request<T>(path, {
        method: 'POST',
        body: body !== undefined ? JSON.stringify(body) : undefined,
        ...init,
        headers,
    })
}

async function postStreamWithCsrf(path: string, body?: unknown, init: RequestInit = {}): Promise<Response> {
    const token = await ensureCsrfToken()
    const headers = new Headers(init.headers || {})
    headers.set('Content-Type', 'application/json')
    headers.set('X-CSRF-Token', token)

    const response = await fetchWithRetry(`${API_BASE_URL}${path}`, {
        method: 'POST',
        credentials: 'include',
        body: body !== undefined ? JSON.stringify(body) : undefined,
        ...init,
        headers,
    }, path)
    return response
}

export const httpClient = {
    ensureCsrfToken,
    resetCsrfToken,
    get: <T>(path: string, init?: RequestInit) => request<T>(path, { method: 'GET', ...init }),
    post: <T>(path: string, body?: unknown, init?: RequestInit) =>
        request<T>(path, {
            method: 'POST',
            body: body !== undefined ? JSON.stringify(body) : undefined,
            ...init,
        }),
    patch: <T>(path: string, body?: unknown, init?: RequestInit) =>
        request<T>(path, {
            method: 'PATCH',
            body: body !== undefined ? JSON.stringify(body) : undefined,
            ...init,
        }),
    delete: <T>(path: string, init?: RequestInit) => request<T>(path, { method: 'DELETE', ...init }),
    postWithCsrf,
    postStreamWithCsrf,
}
