import { httpClient } from '../api/httpClient'

export type UserMemory = {
    id: string
    memory_id: string
    card_id?: string
    memory_type: string
    display_category?: string
    display_text?: string
    mention_count?: number
    status?: string
    is_selected?: boolean
    created_at?: string | null
    last_mentioned_at?: string | null
    expires_at?: string | null
    can_personalize?: boolean
    personalization_disabled?: boolean
    // Compatibility fields from the previous display-ready response.
    badge_label?: string
    title?: string
    body?: string
    content?: string
    source?: string | null
    updated_at?: string | null
    metadata?: Record<string, unknown>
    review_prompt?: string
}

export const memoryService = {
    list: async () => {
        const data = await httpClient.get<{ cards?: UserMemory[]; memory_cards?: UserMemory[]; memories?: UserMemory[] }>('/chat/memory-cards')
        return { memories: Array.isArray(data.cards) ? data.cards : (Array.isArray(data.memory_cards) ? data.memory_cards : (data.memories ?? [])) }
    },
    action: (memoryId: string, action: 'keep' | 'edit' | 'delete' | 'disable_personalization', newContent?: string) =>
        httpClient.postWithCsrf<{ memory_card: UserMemory }>(`/chat/memory-cards/${memoryId}/actions`, {
            action,
            new_content: newContent,
        }),
    delete: (memoryId: string) => memoryService.action(memoryId, 'delete'),
    keep: (memoryId: string) => memoryService.action(memoryId, 'keep'),
    edit: (memoryId: string, newContent: string) => memoryService.action(memoryId, 'edit', newContent),
    disablePersonalization: (memoryId: string) => memoryService.action(memoryId, 'disable_personalization'),
}
