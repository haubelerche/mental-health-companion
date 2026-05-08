import { httpClient } from '../api/httpClient'

export type DashboardReadinessLevel =
    | 'no_data'
    | 'first_signals'
    | 'early_insight'
    | 'weekly_trend'
    | 'stable_pattern'

export type DashboardSufficiency = {
    readiness_level: DashboardReadinessLevel
    active_days: number
    mood_checkin_count: number
    total_session_count: number
    deep_session_count: number
    calendar_days_observed: number
    evidence_window_start: string | null
    evidence_window_end: string | null
    message: string
    next_data_needed: string[]
}

export type InsightCard = {
    insight_id: string
    title: string
    user_safe_summary: string
    evidence_count: number
    evidence_sources: string[]
    confidence: 'low' | 'medium' | 'high'
    severity_band: 'neutral' | 'watch' | 'supportive_attention'
    suggested_action: string | null
    evidence_window_start: string | null
    evidence_window_end: string | null
    updated_at: string
}

export type WellnessDimension = {
    dimension: 'emotion' | 'sleep' | 'mindfulness' | 'connection' | 'body' | 'growth'
    label: string
    status: 'unknown' | 'limited_data' | 'steady' | 'needs_attention' | 'improving'
    score: number | null
    explanation: string
    evidence_count: number
    suggested_action: string | null
}

export type CheckinHistoryItem = {
    checkin_id: string
    logged_at: string
    date: string
    time_bucket: 'morning' | 'afternoon' | 'evening' | 'other'
    mood_label: string | null
    mood_score: number | null
    emotions: string[]
    triggers: string[]
    note: string | null
    reward_granted: boolean | null
}

export type CheckinHistoryDay = {
    date: string
    completed: boolean
    checkins: CheckinHistoryItem[]
    streak_day_index: number | null
}

export type MoodSeriesPoint = {
    date: string
    mood_score: number
    mood_score_pct: number
    label: string
    checkin_count: number
}

export type DashboardProgressSnapshot = {
    streak_days: number
    total_sessions: number
    days_active_last_30: number
    breathing_sessions: number
    effective_rate: number | null
    is_today_completed: boolean
    completed_days?: number[]
}

export type DashboardReflectSummary = {
    sufficiency: DashboardSufficiency
    top_insights: InsightCard[]
    wellness_dimensions: WellnessDimension[]
    mood_series: MoodSeriesPoint[]
    checkin_history_preview: CheckinHistoryDay[]
    radar_available: boolean
    progress: DashboardProgressSnapshot
}

export type NutritionDailyTip = {
    day_index: number
    dish: string
    benefit: string
    tip: string
    timezone: string
}

export type SafeInsightsPayload = {
    sufficiency: DashboardSufficiency
    insights: InsightCard[]
}

export type CheckinHistoryResponse = {
    timezone: string
    range: string
    history: CheckinHistoryDay[]
}

export const dashboardService = {
    getNutritionDailyTip: () => httpClient.get<NutritionDailyTip>('/dashboard/nutrition-daily'),

    getReflectSummary: () => httpClient.get<DashboardReflectSummary>('/dashboard/reflect-summary'),

    getCheckinHistory: (range: '30d' | '90d' | 'all' = '90d') =>
        httpClient.get<CheckinHistoryResponse>(`/dashboard/checkin-history?range=${range}`),

    getSafeInsights: () => httpClient.get<SafeInsightsPayload>('/dashboard/safe-insights'),
}
