import type { ApiEnvelope } from './types'
import { ApiRequestError } from './types'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000/v1'

const API_BASE_URL =
    (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || DEFAULT_API_BASE_URL

function isEnvelope<T>(value: unknown): value is ApiEnvelope<T> {
    return typeof value === 'object' && value !== null && 'success' in value && 'data' in value
}

async function parseJsonSafely(response: Response): Promise<unknown> {
    try {
        return await response.json()
    } catch {
        return null
    }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        credentials: 'include',
        ...init,
        headers: {
            'Content-Type': 'application/json',
            ...(init.headers || {}),
        },
    })

    const payload = await parseJsonSafely(response)

    if (!response.ok) {
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

export const httpClient = {
    get: <T>(path: string, init?: RequestInit) => request<T>(path, { method: 'GET', ...init }),
    post: <T>(path: string, body?: unknown, init?: RequestInit) =>
        request<T>(path, {
            method: 'POST',
            body: body !== undefined ? JSON.stringify(body) : undefined,
            ...init,
        }),
}
