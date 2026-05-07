import { httpClient } from '../api/httpClient'

export type AdminDashboardAggregate = {
    period: { from: string; to: string }
    total_sessions: number
    avg_session_depth: number
    mood_distribution: Record<string, number>
    sos_events: number
    top_resource_categories: string[]
}

export type AdminLatencySla = {
    window: number
    success_rate: number
    avg_ms: number
    p95_ms: number
    target_p95_ms: number
    within_sla: boolean
}

export type AdminAuthLatencyResponse = {
    login: AdminLatencySla
    signup: AdminLatencySla
}

export type AdminCostDashboardResponse = {
    chat_cost: {
        total_turns: number
        total_input_tokens: number
        total_output_tokens: number
        total_tokens: number
        estimated_cost_usd: number
    }
}

export type AdminCrisisLog = {
    log_id: string
    session_id: string
    triggered_at: string
    muc_do: string
    reviewed: boolean
}

export type AdminCrisisLogsResponse = {
    logs: AdminCrisisLog[]
    total: number
    has_more: boolean
}

export type AdminCrisisReviewPayload = {
    reviewed: boolean
    note?: string | null
}

export type AdminResource = {
    resource_id: string
    category: string
    title: string
    description?: string | null
    format: string
    duration_sec: number
    storage_key: string
    external_url?: string | null
    thumbnail_key?: string | null
    tags: string[]
    is_active: boolean
    created_at: string
}

export type AdminResourceListResponse = {
    items: AdminResource[]
    total: number
    has_more: boolean
}

export type AdminResourceCreatePayload = {
    category: string
    title: string
    description?: string | null
    format: string
    duration_sec: number
    storage_key?: string | null
    external_url?: string | null
    thumbnail_key?: string | null
    tags: string[]
    is_active: boolean
}

export type AdminResourceUpdatePayload = Partial<AdminResourceCreatePayload>

export const ADMIN_RESOURCE_CATEGORIES = ['meditate', 'sleep', 'music', 'work_study', 'wisdom', 'movement'] as const
export const ADMIN_RESOURCE_FORMATS = ['audio', 'video', 'article'] as const

export const adminService = {
    login: (payload: { email: string; password: string; totp_code: string }) =>
        httpClient.post<any>('/admin/auth/login', payload),
    getDashboardAggregate: () => httpClient.get<AdminDashboardAggregate>('/admin/dashboard/aggregate'),
    getAuthLatencySla: () => httpClient.get<AdminAuthLatencyResponse>('/admin/auth/latency-sla'),
    getCostDashboard: () => httpClient.get<AdminCostDashboardResponse>('/admin/cost-dashboard'),
    getCrisisLogs: () => httpClient.get<AdminCrisisLogsResponse>('/admin/crisis-logs'),
    reviewCrisisLog: (logId: string, payload: AdminCrisisReviewPayload) =>
        httpClient.patch<{ log_id: string; reviewed: boolean; reviewed_at: string | null; reviewed_by: string | null; note?: string | null }>(
            `/admin/crisis-logs/${encodeURIComponent(logId)}/review`,
            payload,
        ),
    listResources: (params?: { category?: string; include_inactive?: boolean; limit?: number; offset?: number }) => {
        const query = new URLSearchParams()
        if (params?.category) query.set('category', params.category)
        if (typeof params?.include_inactive === 'boolean') query.set('include_inactive', String(params.include_inactive))
        if (typeof params?.limit === 'number') query.set('limit', String(params.limit))
        if (typeof params?.offset === 'number') query.set('offset', String(params.offset))
        const qs = query.toString()
        return httpClient.get<AdminResourceListResponse>(`/admin/resources${qs ? `?${qs}` : ''}`)
    },
    createResource: (payload: AdminResourceCreatePayload) =>
        httpClient.post<{ resource_id: string; created_at: string }>('/admin/resources', payload),
    updateResource: (resourceId: string, payload: AdminResourceUpdatePayload) =>
        httpClient.patch<{ resource_id: string; updated_at: string }>(
            `/admin/resources/${encodeURIComponent(resourceId)}`,
            payload,
        ),
    deleteResource: (resourceId: string) =>
        httpClient.delete<{ resource_id: string; deleted_at: string }>(`/admin/resources/${encodeURIComponent(resourceId)}`),
    agentCrawlResources: (payload: { category: string; limit: number }) =>
        httpClient.postStreamWithCsrf('/admin/resources/agent-crawl', payload),

    // Task 3.1: User Management
    listUsers: (params?: { is_active?: boolean; query?: string; limit?: number; offset?: number }) => {
        const query = new URLSearchParams()
        if (typeof params?.is_active === 'boolean') query.set('is_active', String(params.is_active))
        if (params?.query) query.set('query', params.query)
        if (typeof params?.limit === 'number') query.set('limit', String(params.limit))
        if (typeof params?.offset === 'number') query.set('offset', String(params.offset))
        return httpClient.get<{ users: any[]; total: number }>(`/admin/users?${query.toString()}`)
    },
    getUserDetail: (userId: string) => httpClient.get<any>(`/admin/users/${encodeURIComponent(userId)}/detail`),
    updateUser: (userId: string, payload: { is_active?: boolean; display_name?: string }) =>
        httpClient.patch<any>(`/admin/users/${encodeURIComponent(userId)}`, payload),

    // Task 3.2-3.4: Analytics
    getMoodAnalytics: (days: number = 30) => httpClient.get<any>(`/admin/analytics/mood-distribution?days=${days}`),
    getMoodTrend: (days: number = 30) => httpClient.get<any>(`/admin/analytics/mood-trend?days=${days}`),
    getClinicalAnalytics: () => httpClient.get<any>('/admin/analytics/clinical-overview'),
    getResourceAnalytics: () => httpClient.get<any>('/admin/analytics/resources'),
    getHeartAnalytics: (days: number = 30) => httpClient.get<any>(`/admin/analytics/hearts?days=${days}`),

    // Task 3.5: Letter Management
    listLetters: (params?: { status?: string; query?: string; limit?: number; offset?: number }) => {
        const query = new URLSearchParams()
        if (params?.status) query.set('status', params.status)
        if (params?.query) query.set('query', params.query)
        if (typeof params?.limit === 'number') query.set('limit', String(params.limit))
        if (typeof params?.offset === 'number') query.set('offset', String(params.offset))
        return httpClient.get<{ letters: any[]; total: number }>(`/admin/letters?${query.toString()}`)
    },
    reviewLetter: (letterId: string, action: 'keep' | 'delete') =>
        httpClient.patch<any>(`/admin/letters/${encodeURIComponent(letterId)}/review?action=${action}`, {}),
    aiAnalyzeLetter: (letterId: string) =>
        httpClient.post<any>(`/admin/letters/${encodeURIComponent(letterId)}/ai-analyze`, {}),

    // Task 3.6: Emotion-Driven Agent
    getEmotionResourceSuggestion: () => httpClient.get<any>('/admin/analytics/emotion-resource-suggestion'),
    // Task 3.7: Audit Logs
    listAuditLogs: (params?: { limit?: number; offset?: number }) => {
        const query = new URLSearchParams()
        if (typeof params?.limit === 'number') query.set('limit', String(params.limit))
        if (typeof params?.offset === 'number') query.set('offset', String(params.offset))
        return httpClient.get<{ items: any[]; total: number }>(`/admin/audit-logs?${query.toString()}`)
    },

    // Task 3.8: AI Letter Responder
    runAiResponder: (hours: number = 6) => httpClient.post<any>(`/admin/run-ai-responder?hours=${hours}`, {}),

    // Task 3.10: Bulk Notifications
    broadcastNotification: (payload: { title?: string; body: string; category?: string }) =>
        httpClient.post<any>('/admin/notifications/broadcast', payload),

    // Task 3.11: Automation (Milestone 7)
    getAutomationStatus: () => httpClient.get<Record<string, any>>('/admin/automation/status'),
    toggleWorker: (worker_name: string, active: boolean) => 
        httpClient.post<any>('/admin/automation/toggle', { worker_name, active }),
    updateWorkerConfig: (worker_name: string, interval_min?: number, daily_time?: string) =>
        httpClient.patch<any>('/admin/automation/config', { worker_name, interval_min, daily_time }),
    runWorkerNow: (worker_name: string) =>
        httpClient.post<any>('/admin/automation/run-now', { worker_name }),
}
