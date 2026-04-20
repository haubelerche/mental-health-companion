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
}

export type LoginPayload = {
    email: string
    password: string
}

export type LoginResponse = {
    user_id: string
    expires_in: number
}

export const authService = {
    signup: (payload: SignupPayload) =>
        httpClient.post<SignupResponse>('/auth/signup', payload),
    login: (payload: LoginPayload) =>
        httpClient.post<LoginResponse>('/auth/login', payload),
}
