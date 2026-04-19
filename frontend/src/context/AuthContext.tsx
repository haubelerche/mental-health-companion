import { createContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { authService } from '../services/authService'
import type { SignupPayload, SignupResponse } from '../services/authService'

type AuthUser = {
    userId: string
    email: string
    displayName: string
}

type AuthContextValue = {
    user: AuthUser | null
    isLoading: boolean
    signup: (payload: SignupPayload) => Promise<SignupResponse>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

type AuthProviderProps = {
    children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
    const [user, setUser] = useState<AuthUser | null>(null)
    const [isLoading, setIsLoading] = useState(false)

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

    const value = useMemo(
        () => ({ user, isLoading, signup }),
        [user, isLoading],
    )

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
