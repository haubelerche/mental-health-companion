import { chatService, type VoiceJobResponse } from './chatService'

export const voiceService = {
    getVoiceJob: (ttsJobId: string): Promise<VoiceJobResponse> => chatService.getVoiceJob(ttsJobId),
}
