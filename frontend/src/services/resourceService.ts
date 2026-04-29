import { httpClient } from '../api/httpClient'

export type ResourceCategory = { id: string; label: string; icon: string }

export type ResourceItem = {
    id: string
    category: string
    title: string
    description?: string | null
    duration_sec: number
    format: string
    url: string
    thumbnail?: string | null
    bookmarked: boolean
    tags?: string[]
}

export const resourceService = {
    getCategories: () =>
        httpClient.get<{ categories: ResourceCategory[] }>('/resources/categories'),

    list: (category?: string, limit = 20, offset = 0) => {
        const params = new URLSearchParams()

        if (category && category !== 'all') {
            params.append('category', category)
        }

        params.append('limit', String(limit))
        params.append('offset', String(offset))

        return httpClient.get<{ items: ResourceItem[]; total: number; has_more: boolean }>(
            `/resources?${params.toString()}`,
        )
    },

    listExercises: () =>
        httpClient.get<{ items: unknown[] }>('/resources/exercises'),
}