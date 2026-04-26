import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { AuthContext } from './authContextValue'
import type { AuthUser } from './authContextValue'
import { authService } from '../services/authService'
import type {
    LoginPayload,
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

    useEffect(() => {
        let mounted = true
        authService
            .me()
            .then((data) => {
                if (!mounted) return
                setUser({
                    userId: data.user_id,
                    email: data.email,
                    displayName: data.display_name,
                })
            })
            .catch(() => {
                if (!mounted) return
                setUser(null)
            })
            .finally(() => {
                if (!mounted) return
                setIsLoading(false)
            })
        return () => {
            mounted = false
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
            const displayNameFromEmail = payload.email.split('@')[0] || payload.email

            setUser({
                userId: data.user_id,
                email: payload.email,
                displayName: displayNameFromEmail,
            })

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

    const value = useMemo(
        () => ({ user, isLoading, signup, login, logout, guestSession, startGuestSession, clearGuestSession }),
        [user, isLoading, guestSession, startGuestSession, clearGuestSession],
    )

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
