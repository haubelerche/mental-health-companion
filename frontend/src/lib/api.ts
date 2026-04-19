export type ApiEnvelope<T> = {
  success: boolean
  data: T
  error: { code: string; message: string } | null
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  withCsrf?: boolean
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || 'http://127.0.0.1:8000'
let csrfToken: string | null = null

async function ensureCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken
  const resp = await fetch(`${API_BASE}/v1/auth/csrf-token`, {
    method: 'GET',
    credentials: 'include',
  })
  const payload = (await resp.json()) as ApiEnvelope<{ csrf_token: string }>
  csrfToken = payload.data.csrf_token
  return csrfToken
}

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (options.withCsrf && method !== 'GET') {
    const token = await ensureCsrfToken()
    headers['X-CSRF-Token'] = token
  }

  const resp = await fetch(`${API_BASE}${path}`, {
    method,
    credentials: 'include',
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  })
  const payload = (await resp.json()) as ApiEnvelope<T>
  if (!resp.ok || !payload.success) {
    throw new Error(payload.error?.message || 'Request failed')
  }
  return payload.data
}

export const api = {
  ensureCsrfToken,
  signup: (body: { display_name: string; email: string; password: string; disclaimer_accepted: boolean }) =>
    apiRequest<{ user_id: string; expires_in: number }>('/v1/auth/signup', { method: 'POST', body }),
  login: (body: { email: string; password: string }) =>
    apiRequest<{ user_id: string; expires_in: number }>('/v1/auth/login', { method: 'POST', body }),
  sendMessage: (body: { message: string; session_id?: string | null }) =>
    apiRequest<Record<string, unknown>>('/v1/chat/message', { method: 'POST', body, withCsrf: true }),
  getVoiceJob: (ttsJobId: string) => apiRequest<{ tts_job_id: string; status: string; audio_url: string | null }>(`/v1/chat/voice-jobs/${ttsJobId}`),
  getCurrentPolicy: () => apiRequest<{ version: string; title: string; summary: string }>('/v1/policies/current'),
  acknowledgePolicy: (policyVersion: string) =>
    apiRequest<{ policy_version: string; acknowledged_at: string }>('/v1/policies/acknowledge', {
      method: 'POST',
      body: { policy_version: policyVersion },
      withCsrf: true,
    }),
  getVoiceConsent: () => apiRequest<{ voice_consent: boolean }>('/v1/policies/voice-consent'),
  setVoiceConsent: (consent: boolean) =>
    apiRequest<{ voice_consent: boolean }>('/v1/policies/voice-consent', { method: 'POST', body: { consent }, withCsrf: true }),
}
