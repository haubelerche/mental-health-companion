import { httpClient } from '../api/httpClient'

/** Subset of `/auth/me` used for persona. */
export type AuthMePersonaFields = {
    persona_id: string | null
    persona_selected_at?: string | null
}

export const personasService = {
    /** Current user profile — includes selected persona id. */
    getMe: () => httpClient.get<AuthMePersonaFields & Record<string, unknown>>('/auth/me'),

    /** Canonical persona selection (core + unlockables). */
    select: (personaId: string) =>
        httpClient.postWithCsrf<{ persona_id: string; persona_selected_at?: string }>('/auth/me/persona', {
            persona_id: personaId,
        }),
}
