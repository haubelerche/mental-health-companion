import { httpClient } from '../api/httpClient'
import { ApiRequestError } from '../api/types'

export type ChatMessageRequest = {
    message: string
    session_id?: string | null
}

export type GuestChatMessageRequest = {
    message: string
    guest_session_id?: string | null
}

export type VoiceJobResponse = {
    tts_job_id: string
    status: string
    audio_url: string | null
    audio_data_uri?: string | null
    error_code?: string | null
    error_message?: string | null
}

export type GuestSessionStartResponse = {
    guest_session_id: string
    max_duration_sec: number
}

export type SessionSummary = {
    session_id: string
    last_message_at: string
    preview: string | null
}

export type SessionMessage = {
    message_id: string
    role: 'user' | 'assistant'
    content: string
    created_at: string
}

export const chatService = {
    sendMessage: (payload: ChatMessageRequest) =>
        httpClient.postWithCsrf<Record<string, unknown>>('/chat/message', payload),
    sendMessageStream: async (payload: ChatMessageRequest) => {
        const response = await httpClient.postStreamWithCsrf('/chat/message/stream', payload)
        if (response.ok) return response

        let message = 'Streaming chat thất bại'
        let code: string | undefined
        try {
            const payload = (await response.json()) as {
                error?: { message?: string; code?: string }
                detail?: string
            }
            if (payload?.error?.message) message = payload.error.message
            else if (typeof payload?.detail === 'string' && payload.detail.trim()) message = payload.detail
            if (payload?.error?.code) code = payload.error.code
        } catch {
            // keep fallback message
        }
        throw new ApiRequestError(message, { code, status: response.status })
    },
    sendGuestMessage: (payload: GuestChatMessageRequest) =>
        httpClient.postWithCsrf<Record<string, unknown>>('/chat/guest-message', payload),
    startGuestSession: () => httpClient.postWithCsrf<GuestSessionStartResponse>('/guest/session/start'),
    getVoiceJob: (ttsJobId: string) =>
        httpClient.get<VoiceJobResponse>(`/chat/voice-jobs/${ttsJobId}`),
    getSessions: () => httpClient.get<{ sessions: SessionSummary[] }>('/chat/sessions'),
    getSessionMessages: (sessionId: string, limit = 40, offset = 0) =>
        httpClient.get<{ session_id: string; messages: SessionMessage[]; total: number; has_more: boolean }>(
            `/chat/sessions/${sessionId}/messages?limit=${limit}&offset=${offset}`,
        ),
    deleteSession: (sessionId: string, hard = false) =>
        httpClient.postWithCsrf<{ deleted_at: string; hard_delete_at: string }>(
            `/chat/sessions/${sessionId}?hard=${hard ? 'true' : 'false'}`,
            undefined,
            { method: 'DELETE' },
        ),
    getGreeting: (personaId?: string) =>
        httpClient.get<{ text: string; persona_id: string }>(
            `/chat/greeting${personaId ? `?persona_id=${encodeURIComponent(personaId)}` : ''}`,
        ),
}
