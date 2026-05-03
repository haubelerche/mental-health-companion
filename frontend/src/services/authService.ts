import { httpClient } from '../api/httpClient'

export type SignupPayload = {
    display_name: string
    email: string
    password: string
    disclaimer_accepted: boolean
}

export type SignupResponse = {
    user_id: string
    expires_in?: number
    verification_required?: boolean
    message?: string
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
    onboarding_completed?: boolean
    onboarding_skipped?: boolean
    persona_id?: string | null
    persona_selected_at?: string | null
}

export type PersonaId = 'ban_than' | 'nguoi_yeu' | 'nguoi_thay' | 'nguoi_la' | 'nguoi_than' | 'cun' | 'meo'
export const authService = {
    signup: async (payload: SignupPayload) => {
        const startedAt = performance.now()
        const data = await httpClient.post<SignupResponse>('/auth/signup', {
            display_name: payload.display_name,
            email: payload.email,
            password: payload.password,
            disclaimer_accepted: payload.disclaimer_accepted,
        })
        console.info('[auth-metrics] signup.auth_total_ms', Math.round(performance.now() - startedAt))
        return data
    },

    login: async (payload: LoginPayload) => {
        const startedAt = performance.now()
        const data = await httpClient.post<LoginResponse>('/auth/login', payload)
        console.info('[auth-metrics] login.auth_total_ms', Math.round(performance.now() - startedAt))
        // Policy is auto-acknowledged by the server during login.
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
    updatePersona: (personaId: PersonaId) =>
        httpClient.postWithCsrf<{ persona_id: PersonaId; persona_selected_at: string }>('/auth/me/persona', {
            persona_id: personaId,
        }),
}
