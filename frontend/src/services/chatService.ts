import { httpClient } from '../api/httpClient'

export type ChatMessageRequest = {
    message: string
    session_id?: string | null
}

export type VoiceJobResponse = {
    tts_job_id: string
    status: string
    audio_url: string | null
}

export const chatService = {
    sendMessage: (payload: ChatMessageRequest) =>
        httpClient.postWithCsrf<Record<string, unknown>>('/chat/message', payload),
    getVoiceJob: (ttsJobId: string) =>
        httpClient.get<VoiceJobResponse>(`/chat/voice-jobs/${ttsJobId}`),
}
