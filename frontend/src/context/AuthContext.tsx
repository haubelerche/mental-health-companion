import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { AuthContext } from './authContextValue'
import type { AuthUser } from './authContextValue'
import { authService } from '../services/authService'
import { HTTP_UNAUTHORIZED_EVENT } from '../api/httpClient'
import type {
    LoginPayload,
    PersonaId,
    SignupPayload,
} from '../services/authService'
import { chatService } from '../services/chatService'

type AuthProviderProps = {
    children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
    const [user, setUser] = useState<AuthUser | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [guestSession, setGuestSession] = useState<{
        guest_session_id: string
        expiresAt: number
    } | null>(null)

    const startGuestSession = useCallback(async () => {
        try {
            const data = await chatService.startGuestSession()
            setGuestSession({
                guest_session_id: data.guest_session_id,
                expiresAt: Date.now() + data.max_duration_sec * 1000,
            })
        } catch (error) {
            console.error('Failed to start guest session:', error)
            throw error
        }
    }, [])

    const clearGuestSession = useCallback(() => setGuestSession(null), [])

    const refreshUser = useCallback(async () => {
        try {
            const data = await authService.me()
            setUser({
                userId: data.user_id,
                email: data.email,
                displayName: data.display_name,
                onboardingCompleted: Boolean(data.onboarding_completed),
                onboardingSkipped: Boolean(data.onboarding_skipped),
                personaId: data.persona_id ?? null,
                personaSelectedAt: data.persona_selected_at ?? null,
            })
        } catch {
            setUser(null)
        } finally {
            setIsLoading(false)
        }
    }, [])

    useEffect(() => {
        void refreshUser()
    }, [refreshUser])

    useEffect(() => {
        const handleUnauthorized = () => {
            setUser(null)
            setIsLoading(false)
        }

        window.addEventListener(HTTP_UNAUTHORIZED_EVENT, handleUnauthorized as EventListener)
        return () => {
            window.removeEventListener(HTTP_UNAUTHORIZED_EVENT, handleUnauthorized as EventListener)
        }
    }, [])

    const signup = async (payload: SignupPayload) => {
        setIsLoading(true)
        try {
            const data = await authService.signup(payload)
            setUser({
                userId: data.user_id,
                email: payload.email,
                displayName: payload.display_name,
                onboardingCompleted: false,
                onboardingSkipped: false,
                personaId: null,
                personaSelectedAt: null,
            })
            return data
        } finally {
            setIsLoading(false)
        }
    }

    const login = async (payload: LoginPayload) => {
        setIsLoading(true)
        try {
            const data = await authService.login(payload)
            const me = await authService.me().catch(() => null)
            if (me) {
                setUser({
                    userId: me.user_id,
                    email: me.email,
                    displayName: me.display_name,
                    onboardingCompleted: Boolean(me.onboarding_completed),
                    onboardingSkipped: Boolean(me.onboarding_skipped),
                    personaId: me.persona_id ?? null,
                    personaSelectedAt: me.persona_selected_at ?? null,
                })
            } else {
                const displayNameFromEmail = payload.email.split('@')[0] || payload.email
                setUser({
                    userId: data.user_id,
                    email: payload.email,
                    displayName: displayNameFromEmail,
                    onboardingCompleted: false,
                    onboardingSkipped: false,
                    personaId: null,
                    personaSelectedAt: null,
                })
            }

            return data
        } finally {
            setIsLoading(false)
        }
    }

    const logout = async () => {
        setIsLoading(true)
        try {
            await authService.logout()
            setUser(null)
        } catch (error) {
            console.error('Error occurred while logging out:', error)
        } finally {
            setIsLoading(false)
        }
    }

    const markOnboardingCompleted = useCallback((skipped = false) => {
        setUser((prev) => (prev ? { ...prev, onboardingCompleted: true, onboardingSkipped: skipped } : prev))
    }, [])

    const updatePersona = useCallback(async (personaId: PersonaId) => {
        const data = await authService.updatePersona(personaId)
        setUser((prev) =>
            prev
                ? {
                    ...prev,
                    personaId: data.persona_id,
                    personaSelectedAt: data.persona_selected_at,
                }
                : prev,
        )
    }, [])

    const value = useMemo(
        () => ({
            user,
            isLoading,
            signup,
            login,
            logout,
            refreshUser,
            updatePersona,
            markOnboardingCompleted,
            guestSession,
            startGuestSession,
            clearGuestSession,
        }),
        [user, isLoading, refreshUser, updatePersona, markOnboardingCompleted, guestSession, startGuestSession, clearGuestSession],
    )

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
