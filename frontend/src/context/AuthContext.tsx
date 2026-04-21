import { createContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { authService } from '../services/authService'
import type {
    LoginPayload,
    LoginResponse,
    SignupPayload,
    SignupResponse,
} from '../services/authService'

type AuthUser = {
    userId: string
    email: string
    displayName: string
}

type AuthContextValue = {
    user: AuthUser | null
    isLoading: boolean
    signup: (payload: SignupPayload) => Promise<SignupResponse>
    login: (payload: LoginPayload) => Promise<LoginResponse>
    logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)

type AuthProviderProps = {
    children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
    const [user, setUser] = useState<AuthUser | null>(null)
    const [isLoading, setIsLoading] = useState(true)

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

    const logout = () => {
        setUser(null)
    }

    const value = useMemo(
        () => ({ user, isLoading, signup, login, logout }),
        [user, isLoading],
    )

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
