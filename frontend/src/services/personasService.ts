import { httpClient } from '../api/httpClient'

export type PersonaState = {
    active_persona_id: string
    display_name: string
    style_note?: string | null
    safety_override: boolean
}

export const personasService = {
    getState: () => httpClient.get<PersonaState>('/personas/state'),
    select: (personaId: string) =>
        httpClient.postWithCsrf<PersonaState>('/personas/select', { persona_id: personaId }),
}
