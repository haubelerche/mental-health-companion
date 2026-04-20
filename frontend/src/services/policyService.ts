import { httpClient } from '../api/httpClient'

export const policyService = {
    getVoiceConsent: () =>
        httpClient.get<{ voice_consent: boolean }>('/policies/voice-consent'),
    setVoiceConsent: (consent: boolean) =>
        httpClient.postWithCsrf<{ voice_consent: boolean }>('/policies/voice-consent', { consent }),
}
