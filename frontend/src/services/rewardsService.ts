import { httpClient } from '../api/httpClient'

export type RewardStoreItem = {
    item_id: string
    item_type: string
    title: string
    subtitle?: string | null
    description?: string | null
    price_hearts: number
    tier: number
    icon_key?: string | null
    requirements?: Record<string, unknown>
}

export type RewardShelf = {
    shelf: string
    items: RewardStoreItem[]
}

export type StoreResponse = {
    shelves: RewardShelf[]
    balance: number
}

export type PurchaseResult = {
    inventory_id: string
    item_id: string
    idempotent: boolean
    new_balance: number
}

export type InventoryItem = {
    inventory_id: string
    item_id: string
    acquired_source: string
    acquired_at: string
}

export type PersonaProgress = {
    persona_id: string
    unlocked: boolean
    price_hearts: number
    is_core?: boolean
    progress?: number
    requirements?: Record<string, unknown>
}

export const rewardsService = {
    getStore: () => httpClient.get<StoreResponse>('/rewards/store'),
    getBalance: () => httpClient.get<{ balance: number }>('/rewards/balance'),
    purchase: (itemId: string) =>
        httpClient.postWithCsrf<PurchaseResult>(`/rewards/items/${itemId}/purchase`, {}),
    getInventory: () => httpClient.get<{ items: InventoryItem[] }>('/rewards/inventory'),
    getPersonasProgress: () =>
        httpClient.get<{ personas: PersonaProgress[] }>('/rewards/personas/progress'),
    getCrushBoundaryIntro: () =>
        httpClient.get<{ intro_text: string; key_points: string[]; acceptance_required: boolean }>(
            '/rewards/personas/crush/boundary-intro',
        ),
    acceptCrushBoundary: () =>
        httpClient.postWithCsrf<{ accepted: boolean }>('/rewards/personas/crush/boundary-accept', {}),
}
