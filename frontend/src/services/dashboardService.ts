import { httpClient } from '../api/httpClient'
import { ROUTE_PATHS } from '../routes/paths'

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
    category?: string
    title: string
    user_safe_summary: string
    interpretation?: string | null
    evidence?: Array<Record<string, unknown>>
    evidence_count: number
    evidence_sources: string[]
    confidence: 'low' | 'medium' | 'high' | number
    severity_band: 'neutral' | 'watch' | 'informational' | 'low' | 'medium' | 'high'
    suggested_action: string | null
    recommended_actions?: string[]
    missing_data?: string[]
    evidence_window_start: string | null
    evidence_window_end: string | null
    updated_at: string
}

export type WellnessDimension = {
    dimension: 'emotion' | 'sleep' | 'mindfulness' | 'connection' | 'body' | 'growth' | 'nutrition' | 'screening'
    label: string
    status: 'unknown' | 'limited_data' | 'steady' | 'needs_attention' | 'improving'
    score: number | null
    explanation: string
    evidence_count: number
    suggested_action: string | null
}

export type ReflectRange = '7d' | '14d' | '30d'
export type ReflectPeriod = 'morning' | 'afternoon' | 'evening' | 'unknown'
export type ReflectDataQualityLevel = 'no_data' | 'low_data' | 'early_signal' | 'clear_signal'

export type ReflectCountLabel = {
    label: string
    count: number
}

export type ReflectDataQuality = {
    checkin_count: number
    enough_for_trend: boolean
    enough_for_patterns: boolean
    label: 'limited' | 'fair' | 'good'
    quality: ReflectDataQualityLevel
    badge_label: string
    confidence_label: string
    user_message: string
}

export type ReflectSuggestedAction = {
    label: string
    route: string
    reason: string
    action_type?: 'checkin' | 'meal_log' | 'journal' | 'chat' | 'resource'
}

export type ReflectOverview = {
    state_label: string
    summary: string
    trend_label: string
    primary_factor?: string
    suggested_action?: ReflectSuggestedAction
}

export type ReflectMoodSeriesPoint = {
    date: string
    mood_score: number | null
    energy_score?: number | null
    checkin_count: number
    top_emotions: string[]
    top_triggers: string[]
    note_excerpt?: string
}

export type ReflectWellnessDimension = WellnessDimension & {
    trend_delta?: number | null
    evidence_text: string
    reason?: string
}

export type ReflectInsight = {
    insight_id: string
    category?: string
    hypothesis_type: string
    title: string
    user_safe_summary: string
    interpretation?: string | null
    confidence_label: string
    severity_label: string
    evidence_count: number
    evidence_window_start: string | null
    evidence_window_end: string | null
    suggested_action?: string | null
    recommended_actions?: string[]
    missing_data?: string[]
}

export type TriggerEmotionMatrixCell = {
    trigger: string
    emotion: string
    count: number
    strength: 'low' | 'medium' | 'high'
}

export type MoodByPeriodItem = {
    period: ReflectPeriod
    label: string
    avg_mood: number | null
    avg_energy: number | null
    count: number
}

export type ReflectRecentCheckin = {
    id: string
    date: string
    period: ReflectPeriod
    mood_score: number | null
    energy_score?: number | null
    emotions: string[]
    triggers: string[]
    note_excerpt?: string
}

export type ReflectDashboardSummary = {
    range_days: 7 | 14 | 30
    last_updated_at: string
    data_quality: ReflectDataQualityLevel
    checkin_count: number
    period_coverage: Record<ReflectPeriod, number>
    mood_average?: number
    mood_min?: number
    mood_max?: number
    top_triggers: ReflectCountLabel[]
    top_emotions: ReflectCountLabel[]
    missing_data: string[]
    primary_observation?: string
    recommended_action?: ReflectSuggestedAction
}

export type ReflectDashboardResponse = {
    range: ReflectRange
    generated_at: string
    data_quality: ReflectDataQuality
    overview: ReflectOverview
    summary: ReflectDashboardSummary
    mood_series: ReflectMoodSeriesPoint[]
    mood_by_period: MoodByPeriodItem[]
    dimensions: ReflectWellnessDimension[]
    insights: ReflectInsight[]
    trigger_emotion_matrix: TriggerEmotionMatrixCell[]
    recent_checkins: ReflectRecentCheckin[]
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
    days: number | null
    history: CheckinHistoryDay[]
}

const RANGE_DAYS: Record<ReflectRange, 7 | 14 | 30> = {
    '7d': 7,
    '14d': 14,
    '30d': 30,
}

function daysForRange(range: ReflectRange): 7 | 14 | 30 {
    return RANGE_DAYS[range]
}

function isoDateOnly(value: string): string {
    return value.slice(0, 10)
}

function dateWindowStart(range: ReflectRange): string {
    const d = new Date()
    d.setHours(0, 0, 0, 0)
    d.setDate(d.getDate() - daysForRange(range) + 1)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
}

function withinRange(date: string, range: ReflectRange): boolean {
    return isoDateOnly(date) >= dateWindowStart(range)
}

function toTenPointMood(score: number | null | undefined): number | null {
    if (typeof score !== 'number' || Number.isNaN(score)) return null
    if (score <= 5) return Math.round(score * 2)
    return Math.round(Math.max(1, Math.min(10, score)))
}

function truncateNote(note: string | null | undefined, maxLength = 80): string | undefined {
    const clean = (note || '').trim()
    if (!clean) return undefined
    return clean.length > maxLength ? `${clean.slice(0, maxLength - 3)}...` : clean
}

function periodFromBucket(bucket: CheckinHistoryItem['time_bucket']): ReflectPeriod {
    if (bucket === 'morning' || bucket === 'afternoon' || bucket === 'evening') return bucket
    return 'unknown'
}

function topCounts(items: string[], limit = 3): ReflectCountLabel[] {
    const counts = new Map<string, number>()
    for (const raw of items) {
        const label = raw.trim()
        if (!label) continue
        counts.set(label, (counts.get(label) || 0) + 1)
    }
    return [...counts.entries()]
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .slice(0, limit)
        .map(([label, count]) => ({ label, count }))
}

function topLabels(items: string[], limit = 3): string[] {
    return topCounts(items, limit).map((item) => item.label)
}

function flattenRecentCheckins(history: CheckinHistoryDay[], range: ReflectRange): ReflectRecentCheckin[] {
    return history
        .filter((day) => withinRange(day.date, range))
        .flatMap((day) =>
            day.checkins.map((item) => ({
                id: item.checkin_id,
                date: isoDateOnly(item.date || item.logged_at),
                period: periodFromBucket(item.time_bucket),
                mood_score: toTenPointMood(item.mood_score),
                energy_score: null,
                emotions: item.emotions || [],
                triggers: item.triggers || [],
                note_excerpt: truncateNote(item.note),
            })),
        )
        .sort((a, b) => b.date.localeCompare(a.date))
}

function buildMoodSeriesFromHistory(history: CheckinHistoryDay[], range: ReflectRange): ReflectMoodSeriesPoint[] {
    return history
        .filter((day) => withinRange(day.date, range))
        .sort((a, b) => a.date.localeCompare(b.date))
        .map((day) => {
            const scored = day.checkins
                .map((item) => toTenPointMood(item.mood_score))
                .filter((score): score is number => typeof score === 'number')
            const allEmotions = day.checkins.flatMap((item) => item.emotions || [])
            const allTriggers = day.checkins.flatMap((item) => item.triggers || [])
            const note = day.checkins.find((item) => item.note)?.note
            return {
                date: isoDateOnly(day.date),
                mood_score: scored.length ? Math.round(scored.reduce((sum, score) => sum + score, 0) / scored.length) : null,
                energy_score: null,
                checkin_count: day.checkins.length,
                top_emotions: topLabels(allEmotions),
                top_triggers: topLabels(allTriggers),
                note_excerpt: truncateNote(note),
            }
        })
}

function confidenceLabel(confidence: InsightCard['confidence']): string {
    if (typeof confidence === 'number') {
        if (confidence < 0.35) return 'Dữ liệu còn ít'
        if (confidence < 0.65) return 'Dữ liệu mức vừa'
        if (confidence <= 0.85) return 'Khá rõ'
        return 'Rất nhất quán'
    }
    if (confidence === 'high') return 'Khá rõ'
    if (confidence === 'medium') return 'Dữ liệu mức vừa'
    return 'Dữ liệu còn ít'
}

function severityLabel(severity: InsightCard['severity_band'] | string): string {
    if (severity === 'watch' || severity === 'medium') return 'Nên chăm thêm một chút'
    if (severity === 'high') return 'Nên ưu tiên nghỉ và tìm hỗ trợ phù hợp'
    return 'Nhẹ, chỉ cần để ý'
}

export function adaptInsights(insights: InsightCard[]): ReflectInsight[] {
    return insights.map((insight) => ({
        insight_id: insight.insight_id,
        category: insight.category,
        hypothesis_type: insight.category || insight.evidence_sources?.[0] || 'safe_dashboard_insight',
        title: insight.title,
        user_safe_summary: insight.user_safe_summary,
        interpretation: insight.interpretation,
        confidence_label: confidenceLabel(insight.confidence),
        severity_label: severityLabel(insight.severity_band),
        evidence_count: insight.evidence_count,
        evidence_window_start: insight.evidence_window_start,
        evidence_window_end: insight.evidence_window_end,
        suggested_action: insight.suggested_action,
        recommended_actions: insight.recommended_actions || (insight.suggested_action ? [insight.suggested_action] : []),
        missing_data: insight.missing_data || [],
    }))
}

function buildMatrix(checkins: ReflectRecentCheckin[]): TriggerEmotionMatrixCell[] {
    const counts = new Map<string, { trigger: string; emotion: string; count: number }>()
    for (const checkin of checkins) {
        const triggers = checkin.triggers.length ? checkin.triggers : ['Không rõ']
        const emotions = checkin.emotions.length ? checkin.emotions : []
        for (const trigger of triggers) {
            for (const emotion of emotions) {
                const key = `${trigger}:::${emotion}`
                const current = counts.get(key)
                counts.set(key, { trigger, emotion, count: (current?.count || 0) + 1 })
            }
        }
    }
    const maxCount = Math.max(1, ...[...counts.values()].map((item) => item.count))
    return [...counts.values()]
        .sort((a, b) => b.count - a.count || a.trigger.localeCompare(b.trigger))
        .slice(0, 42)
        .map((item) => ({
            ...item,
            strength: item.count / maxCount >= 0.67 ? 'high' : item.count / maxCount >= 0.34 ? 'medium' : 'low',
        }))
}

function buildPeriodCoverage(checkins: ReflectRecentCheckin[]): Record<ReflectPeriod, number> {
    return checkins.reduce<Record<ReflectPeriod, number>>(
        (acc, checkin) => {
            acc[checkin.period] += 1
            return acc
        },
        { morning: 0, afternoon: 0, evening: 0, unknown: 0 },
    )
}

function missingData(checkins: ReflectRecentCheckin[]): string[] {
    if (checkins.length === 0) return ['Chưa có check-in', 'Chưa có năng lượng', 'Chưa có log bữa ăn']
    const coverage = buildPeriodCoverage(checkins)
    const missing: string[] = []
    if (!checkins.some((item) => typeof item.energy_score === 'number')) missing.push('Chưa có năng lượng')
    if (coverage.evening === 0) missing.push('Chưa có check-in tối')
    if (!checkins.some((item) => item.note_excerpt)) missing.push('Chưa có ghi chú ngắn')
    missing.push('Chưa có log bữa ăn')
    return [...new Set(missing)].slice(0, 4)
}

function dataQuality(checkins: ReflectRecentCheckin[], range: ReflectRange): ReflectDataQuality {
    const count = checkins.length
    const activeDays = new Set(checkins.map((item) => item.date)).size
    const enoughForTrend = activeDays >= 3 || count >= 5
    const enoughForPatterns = count >= 5 && checkins.some((item) => item.triggers.length && item.emotions.length)
    const quality: ReflectDataQualityLevel =
        count === 0 ? 'no_data' : count < 3 ? 'low_data' : enoughForTrend && enoughForPatterns ? 'clear_signal' : 'early_signal'
    const label = quality === 'clear_signal' ? 'good' : quality === 'early_signal' ? 'fair' : 'limited'
    const badgeLabel =
        quality === 'no_data'
            ? 'Chưa có dữ liệu'
            : quality === 'low_data'
              ? 'Dữ liệu còn ít'
              : quality === 'early_signal'
                ? 'Đủ quan sát sơ bộ'
                : 'Có xu hướng rõ'
    const confidenceLabelText =
        quality === 'clear_signal' ? 'Độ tin cậy: khá rõ' : quality === 'early_signal' ? 'Độ tin cậy: sơ bộ' : 'Độ tin cậy: thấp'
    return {
        checkin_count: count,
        enough_for_trend: enoughForTrend,
        enough_for_patterns: enoughForPatterns,
        label,
        quality,
        badge_label: badgeLabel,
        confidence_label: confidenceLabelText,
        user_message: `Dữ liệu hiện có: ${count} check-in trong ${daysForRange(range)} ngày. Các quan sát chỉ dùng để tự theo dõi, không phải chẩn đoán y khoa.`,
    }
}

function moodStats(checkins: ReflectRecentCheckin[]) {
    const scores = checkins
        .map((item) => item.mood_score)
        .filter((score): score is number => typeof score === 'number')
    if (!scores.length) return {}
    const total = scores.reduce((sum, score) => sum + score, 0)
    return {
        mood_average: Math.round((total / scores.length) * 10) / 10,
        mood_min: Math.min(...scores),
        mood_max: Math.max(...scores),
    }
}

function primaryObservation(checkins: ReflectRecentCheckin[]): string {
    const scores = checkins
        .map((item) => item.mood_score)
        .filter((score): score is number => typeof score === 'number')
    if (checkins.length === 0) return 'Chưa có check-in nào trong khoảng này.'
    if (scores.length === 0) return `${checkins.length} check-in gần nhất chưa có điểm mood để tổng hợp.`
    if (scores.length <= 2 && Math.min(...scores) === Math.max(...scores)) {
        return `Mood đang ổn định ở ${scores[0]}/10 trong ${scores.length} lần check-in gần nhất.`
    }
    const avg = Math.round((scores.reduce((sum, score) => sum + score, 0) / scores.length) * 10) / 10
    return `Mood trung bình ${avg}/10, dao động từ ${Math.min(...scores)} đến ${Math.max(...scores)} trong khoảng đã chọn.`
}

function trendLabel(series: ReflectMoodSeriesPoint[]): string {
    const scored = series.filter((point) => typeof point.mood_score === 'number') as Array<
        ReflectMoodSeriesPoint & { mood_score: number }
    >
    if (scored.length < 4) return 'Xu hướng sơ bộ'
    const midpoint = Math.floor(scored.length / 2)
    const first = scored.slice(0, midpoint)
    const second = scored.slice(midpoint)
    const avg = (rows: Array<{ mood_score: number }>) => rows.reduce((sum, row) => sum + row.mood_score, 0) / rows.length
    const delta = avg(second) - avg(first)
    if (delta >= 1) return 'Ổn hơn giai đoạn trước'
    if (delta <= -1) return 'Thấp hơn giai đoạn trước'
    return 'Khá ổn định'
}

function recommendAction(checkins: ReflectRecentCheckin[], insights: ReflectInsight[]): ReflectSuggestedAction {
    const gaps = missingData(checkins)
    const topTrigger = topCounts(checkins.flatMap((item) => item.triggers), 1)[0]
    const topEmotion = topCounts(checkins.flatMap((item) => item.emotions), 1)[0]

    if (checkins.length === 0) {
        return {
            label: 'Tạo check-in đầu tiên',
            route: ROUTE_PATHS.checkin,
            reason: 'Ghi một check-in ngắn để bắt đầu theo dõi mood, trigger và cảm xúc trong dashboard.',
            action_type: 'checkin',
        }
    }
    if (gaps.includes('Chưa có check-in tối')) {
        return {
            label: 'Check-in buổi tối',
            route: ROUTE_PATHS.checkin,
            reason: 'Bổ sung một check-in cuối ngày để so sánh mood buổi tối với các lần ghi nhận trước.',
            action_type: 'checkin',
        }
    }
    if (gaps.includes('Chưa có năng lượng')) {
        return {
            label: 'Bổ sung mức năng lượng',
            route: ROUTE_PATHS.checkin,
            reason: 'Thêm mức năng lượng giúp phân biệt mood ổn định với trạng thái còn sức hay đã cạn sức.',
            action_type: 'checkin',
        }
    }
    if (topTrigger) {
        return {
            label: `Ghi nhanh trigger ${topTrigger.label}`,
            route: ROUTE_PATHS.chat,
            reason: `Trigger "${topTrigger.label}" đã xuất hiện trong dữ liệu. Một ghi chú ngắn sẽ giúp làm rõ bối cảnh.`,
            action_type: 'chat',
        }
    }
    if (topEmotion?.label.toLowerCase().includes('biết ơn')) {
        return {
            label: 'Lưu một điều biết ơn',
            route: ROUTE_PATHS.checkin,
            reason: 'Nhãn “Biết ơn” xuất hiện trong check-in gần đây; lưu lại một ví dụ cụ thể sẽ làm evidence rõ hơn.',
            action_type: 'journal',
        }
    }
    return {
        label: insights[0]?.suggested_action || 'Check-in ngắn hôm nay',
        route: ROUTE_PATHS.checkin,
        reason: 'Một ghi nhận mới sẽ giúp dashboard phân biệt tín hiệu nhất thời với xu hướng lặp lại.',
        action_type: 'checkin',
    }
}

const PERIOD_LABELS: Record<ReflectPeriod, string> = {
    morning: 'Buổi sáng',
    afternoon: 'Buổi chiều',
    evening: 'Buổi tối',
    unknown: 'Không rõ',
}

function buildMoodByPeriod(checkins: ReflectRecentCheckin[]): MoodByPeriodItem[] {
    const groups: Record<ReflectPeriod, { moods: number[]; energies: number[] }> = {
        morning: { moods: [], energies: [] },
        afternoon: { moods: [], energies: [] },
        evening: { moods: [], energies: [] },
        unknown: { moods: [], energies: [] },
    }
    for (const checkin of checkins) {
        const g = groups[checkin.period]
        if (typeof checkin.mood_score === 'number') g.moods.push(checkin.mood_score)
        if (typeof checkin.energy_score === 'number') g.energies.push(checkin.energy_score)
    }
    const avg = (nums: number[]): number | null =>
        nums.length ? Math.round((nums.reduce((s, v) => s + v, 0) / nums.length) * 10) / 10 : null

    return (['morning', 'afternoon', 'evening'] as ReflectPeriod[]).map((period) => ({
        period,
        label: PERIOD_LABELS[period],
        avg_mood: avg(groups[period].moods),
        avg_energy: avg(groups[period].energies),
        count: groups[period].moods.length,
    }))
}

function buildReflectSummary(
    range: ReflectRange,
    generatedAt: string,
    quality: ReflectDataQuality,
    checkins: ReflectRecentCheckin[],
    insights: ReflectInsight[],
): ReflectDashboardSummary {
    return {
        range_days: daysForRange(range),
        last_updated_at: generatedAt,
        data_quality: quality.quality,
        checkin_count: checkins.length,
        period_coverage: buildPeriodCoverage(checkins),
        ...moodStats(checkins),
        top_triggers: topCounts(checkins.flatMap((item) => item.triggers), 3),
        top_emotions: topCounts(checkins.flatMap((item) => item.emotions), 3),
        missing_data: missingData(checkins),
        primary_observation: primaryObservation(checkins),
        recommended_action: recommendAction(checkins, insights),
    }
}

function overviewState(quality: ReflectDataQuality, dimensions: WellnessDimension[], trend: string): string {
    if (quality.quality === 'no_data' || quality.quality === 'low_data') return quality.badge_label
    if (trend.includes('Ổn hơn')) return 'Đang cải thiện'
    if (dimensions.some((d) => d.status === 'needs_attention')) return 'Cần chăm thêm'
    return 'Khá ổn'
}

function buildOverview(
    quality: ReflectDataQuality,
    dimensions: WellnessDimension[],
    series: ReflectMoodSeriesPoint[],
    checkins: ReflectRecentCheckin[],
    insights: ReflectInsight[],
): ReflectOverview {
    const trend = trendLabel(series)
    const action = recommendAction(checkins, insights)
    const lifeState = insights.find((insight) => insight.category === 'weekly_life_state')
    const summary = lifeState?.interpretation || lifeState?.user_safe_summary || primaryObservation(checkins)
    return {
        state_label: lifeState ? lifeState.title : overviewState(quality, dimensions, trend),
        summary,
        trend_label: trend,
        primary_factor: topLabels(checkins.flatMap((item) => item.triggers), 1)[0],
        suggested_action: action,
    }
}

function adaptDimensions(dimensions: WellnessDimension[], series: ReflectMoodSeriesPoint[]): ReflectWellnessDimension[] {
    const trend = trendLabel(series)
    return dimensions.map((dimension) => ({
        ...dimension,
        trend_delta: null,
        evidence_text:
            dimension.evidence_count > 0
                ? `Dựa trên ${dimension.evidence_count} ghi nhận gần đây`
                : 'Dữ liệu còn ít, chỉ nên đọc như quan sát sơ bộ',
        reason: dimension.dimension === 'emotion' ? `Xu hướng cảm xúc: ${trend.toLowerCase()}.` : undefined,
    }))
}

export const dashboardService = {
    getNutritionDailyTip: () => httpClient.get<NutritionDailyTip>('/dashboard/nutrition-daily'),

    getReflectSummary: () => httpClient.get<DashboardReflectSummary>('/dashboard/reflect-summary'),

    getReflectDashboard: async (range: ReflectRange = '7d'): Promise<ReflectDashboardResponse> => {
        const [summary, safeInsights, history] = await Promise.all([
            dashboardService.getReflectSummary(),
            dashboardService.getSafeInsights(range),
            dashboardService.getCheckinHistory('30d'),
        ])
        const generatedAt = new Date().toISOString()
        const recentCheckins = flattenRecentCheckins(history.history, range)
        const moodSeries = buildMoodSeriesFromHistory(history.history, range)
        const insights = adaptInsights(safeInsights.insights.length ? safeInsights.insights : summary.top_insights)
        const quality = dataQuality(recentCheckins, range)
        const dimensions = adaptDimensions(summary.wellness_dimensions, moodSeries)
        return {
            range,
            generated_at: generatedAt,
            data_quality: quality,
            overview: buildOverview(quality, summary.wellness_dimensions, moodSeries, recentCheckins, insights),
            summary: buildReflectSummary(range, generatedAt, quality, recentCheckins, insights),
            mood_series: moodSeries,
            mood_by_period: buildMoodByPeriod(recentCheckins),
            dimensions,
            insights,
            trigger_emotion_matrix: buildMatrix(recentCheckins),
            recent_checkins: recentCheckins.slice(0, 7),
        }
    },

    getCheckinHistory: (range: '30d' | '90d' | 'all' = '30d') =>
        httpClient.get<CheckinHistoryResponse>(`/dashboard/checkin-history?range=${range}`),

    getSafeInsights: (window: ReflectRange = '7d') => httpClient.get<SafeInsightsPayload>(`/dashboard/safe-insights?window=${window}`),
}
