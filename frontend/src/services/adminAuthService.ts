import { httpClient } from '../api/httpClient'

export type AdminLoginPayload = {
    email: string
    password: string
    totp_code: string
}

export type AdminLoginResponse = {
    admin_id: string
    expires_in: number
}

export const adminAuthService = {
    login: (payload: AdminLoginPayload) => httpClient.post<AdminLoginResponse>('/admin/auth/login', payload),
    logout: () => httpClient.post<any>('/admin/auth/logout'),
}