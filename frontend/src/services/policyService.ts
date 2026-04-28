import { httpClient } from '../api/httpClient'

export const policyService = {
    getVoiceConsent: () =>
        httpClient.get<{ voice_consent: boolean }>('/policies/voice-consent'),
    setVoiceConsent: (consent: boolean) =>
        httpClient.postWithCsrf<{ voice_consent: boolean }>('/policies/voice-consent', { consent }),
    acknowledge: async () => {
        const current = await httpClient.get<{ version: string }>('/policies/current')
        return httpClient.postWithCsrf<{ policy_version: string; acknowledged_at: string }>('/policies/acknowledge', {
            policy_version: current.version,
        })
    },
}
