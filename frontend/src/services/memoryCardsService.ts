import { httpClient } from '../api/httpClient'

export type MemoryCard = {
    card_id: string
    memory_type: string
    title: string
    content: string
    confidence?: number | null
    status: string
    safety_review_status: string
    personalization_disabled: boolean
    source_session_id?: string | null
    created_at: string
    updated_at: string
}

export type MemoryCardAction = 'keep' | 'edit' | 'delete' | 'disable_personalization'

export const memoryCardsService = {
    list: () => httpClient.get<{ cards: MemoryCard[] }>('/chat/memory-cards'),
    applyAction: (
        cardId: string,
        action: MemoryCardAction,
        opts?: { new_title?: string; new_content?: string },
    ) =>
        httpClient.postWithCsrf<{ card: MemoryCard }>(
            `/chat/memory-cards/${cardId}`,
            { action, ...opts },
            { method: 'PATCH' },
        ),
}
