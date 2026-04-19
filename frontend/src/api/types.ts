export type ApiErrorPayload = {
    code: string
    message: string
}

export type ApiEnvelope<T> = {
    success: boolean
    data: T | null
    error: ApiErrorPayload | null
}

export class ApiRequestError extends Error {
    code?: string
    status?: number

    constructor(message: string, options?: { code?: string; status?: number }) {
        super(message)
        this.name = 'ApiRequestError'
        this.code = options?.code
        this.status = options?.status
    }
}
