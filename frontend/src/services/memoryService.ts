import { httpClient } from '../api/httpClient'

export type UserMemory = {
    memory_id: string
    content: string
    source?: string | null
    created_at?: string | null
    metadata?: Record<string, unknown>
}

export const memoryService = {
    list: () => httpClient.get<{ memories: UserMemory[] }>('/chat/memories'),
    delete: (memoryId: string) =>
        httpClient.postWithCsrf<{ deleted: boolean; memory_id: string }>(
            `/chat/memories/${memoryId}`,
            {},
            { method: 'DELETE' },
        ),
}
