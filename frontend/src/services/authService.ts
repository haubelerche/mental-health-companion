import { httpClient } from '../api/httpClient'

export type SignupPayload = {
    display_name: string
    email: string
    password: string
    disclaimer_accepted: boolean
    voice_consent?: boolean
}

export type SignupResponse = {
    user_id: string
    expires_in?: number
}

export type LoginPayload = {
    email: string
    password: string
}

export type LoginResponse = {
    user_id: string
    expires_in: number
}

export type LogoutResponse = {
    logged_out_at: string
}

export type ForgotPasswordPayload = {
    email: string
}

export type ForgotPasswordResponse = {
    sent: boolean
}

export type ResetPasswordPayload = {
    token: string
    new_password: string
}

export type ResetPasswordResponse = {
    reset: boolean
}

export type MeResponse = {
    user_id: string
    email: string
    display_name: string
}

type CurrentPolicyResponse = {
    version: string
    title: string
    summary: string
}

type PolicyAcknowledgeResponse = {
    policy_version: string
    acknowledged_at: string
}

export const authService = {
    signup: async (payload: SignupPayload) => {
        const data = await httpClient.post<SignupResponse>('/auth/signup', {
            display_name: payload.display_name,
            email: payload.email,
            password: payload.password,
            disclaimer_accepted: payload.disclaimer_accepted,
        })
        httpClient.resetCsrfToken()
        await httpClient.ensureCsrfToken(true)
        const currentPolicy = await httpClient.get<CurrentPolicyResponse>('/policies/current')
        await httpClient.postWithCsrf<PolicyAcknowledgeResponse>('/policies/acknowledge', {
            policy_version: currentPolicy.version,
        })
        if (typeof payload.voice_consent === 'boolean') {
            await httpClient.postWithCsrf<{ voice_consent: boolean }>('/policies/voice-consent', {
                consent: payload.voice_consent,
            })
        }
        return data
    },
    login: async (payload: LoginPayload) => {
        const data = await httpClient.post<LoginResponse>('/auth/login', payload)
        httpClient.resetCsrfToken()
        await httpClient.ensureCsrfToken(true)
        const currentPolicy = await httpClient.get<CurrentPolicyResponse>('/policies/current')
        await httpClient.postWithCsrf<PolicyAcknowledgeResponse>('/policies/acknowledge', {
            policy_version: currentPolicy.version,
        })
        return data
    },
    logout: async () => {
        await httpClient.postWithCsrf<LogoutResponse>('/auth/logout')
        httpClient.resetCsrfToken()
    },
    forgotPassword: (payload: ForgotPasswordPayload) =>
        httpClient.post<ForgotPasswordResponse>('/auth/forgot-password', payload),
    resetPassword: (payload: ResetPasswordPayload) =>
        httpClient.post<ResetPasswordResponse>('/auth/reset-password', payload),
    me: () => httpClient.get<MeResponse>('/auth/me'),
}
