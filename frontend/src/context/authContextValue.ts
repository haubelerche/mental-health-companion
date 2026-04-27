import { createContext } from 'react'
import type {
    LoginPayload,
    LoginResponse,
    SignupPayload,
    SignupResponse,
} from '../services/authService'

export type AuthUser = {
    userId: string
    email: string
    displayName: string
    onboardingCompleted: boolean
    onboardingSkipped: boolean
}

export type AuthContextValue = {
    user: AuthUser | null
    isLoading: boolean
    signup: (payload: SignupPayload) => Promise<SignupResponse>
    login: (payload: LoginPayload) => Promise<LoginResponse>
    logout: () => void
    refreshUser: () => Promise<void>
    markOnboardingCompleted: (skipped?: boolean) => void
    guestSession: { guest_session_id: string; expiresAt: number } | null
    startGuestSession: () => Promise<void>
    clearGuestSession: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
