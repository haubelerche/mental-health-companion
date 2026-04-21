import { httpClient } from '../api/httpClient'

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
    error_code?: string | null
    error_message?: string | null
}

export const chatService = {
    sendMessage: (payload: ChatMessageRequest) =>
        httpClient.postWithCsrf<Record<string, unknown>>('/chat/message', payload),
    sendMessageStream: (payload: ChatMessageRequest) => httpClient.postStreamWithCsrf('/chat/message/stream', payload),
    sendGuestMessage: (payload: GuestChatMessageRequest) =>
        httpClient.postWithCsrf<Record<string, unknown>>('/chat/guest-message', payload),
    getVoiceJob: (ttsJobId: string) =>
        httpClient.get<VoiceJobResponse>(`/chat/voice-jobs/${ttsJobId}`),
}
