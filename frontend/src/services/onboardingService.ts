import { httpClient } from '../api/httpClient'
import { ROUTE_PATHS } from '../routes/paths'

export type EmotionalState = 'difficult_recently' | 'ongoing_challenges' | 'doing_okay'

export type SupportLevel = 'excellent' | 'good' | 'limited' | 'poor'

export type OnboardingProfile = {
    disclaimer_accepted: boolean
    nickname: string
    age_group: string
    emotional_state: EmotionalState
    primary_concern: string | null
    support_level: SupportLevel | null
    stress_level: number
    wake_time: string
    bed_time: string
    practice_ids: string[]
    completed_at?: string
    skipped?: boolean
}

export type DailyPlanItem = {
    id: string
    label: string
    icon: string
    route: string
}

type DailyPlanTemplate = {
    id: string
    icon: string
    label: string
    route: string
}

const PRACTICE_PLAN_MAP: Record<string, DailyPlanTemplate> = {
    breathing: { id: 'breathing', icon: '🌬️', label: 'Thở hộp 4-4-4', route: `${ROUTE_PATHS.exercises}?exercise=box_breath` },
    meditation: { id: 'meditation', icon: '🧘', label: 'Thiền 5 phút', route: `${ROUTE_PATHS.exercises}?type=meditation&id=morning_5` },
    journaling: { id: 'journaling', icon: '📓', label: 'Viết 3 dòng biết ơn', route: `${ROUTE_PATHS.checkin}?variant=evening` },
    mood_tracking: { id: 'mood_tracking', icon: '🙂', label: 'Check-in cảm xúc', route: ROUTE_PATHS.checkin },
    gratitude: { id: 'gratitude', icon: '💛', label: 'Ghi 1 điều biết ơn', route: `${ROUTE_PATHS.checkin}?variant=gratitude` },
    physical_activity: { id: 'physical_activity', icon: '🚶', label: 'Đi bộ 10 phút', route: `${ROUTE_PATHS.exercises}?type=movement` },
    better_sleep: { id: 'better_sleep', icon: '🌙', label: 'Bài thở trước giờ ngủ', route: `${ROUTE_PATHS.exercises}?exercise=sleep_breath` },
    productivity: { id: 'productivity', icon: '🎯', label: 'Tập trung Pomodoro 10 phút', route: `${ROUTE_PATHS.exercises}?type=focus` },
}

const DEFAULT_PLAN: DailyPlanItem[] = [
    { id: 'checkin_morning', label: 'Check-in sáng', icon: '🌅', route: ROUTE_PATHS.checkin },
    { id: 'meditation', label: 'Thiền 5 phút', icon: '🧘', route: `${ROUTE_PATHS.exercises}?type=meditation&id=morning_5` },
    { id: 'journal_evening', label: 'Nhật ký tối', icon: '📓', route: `${ROUTE_PATHS.checkin}?variant=evening` },
]

const EXCLUDED_TODAY_PRACTICES = new Set(['breathing', 'mood_tracking'])

function dedupe<T>(items: T[]): T[] {
    return [...new Set(items)]
}

function hasEveningPractice(practiceIds: string[]): boolean {
    return practiceIds.some((id) => id === 'journaling' || id === 'gratitude' || id === 'better_sleep')
}

export function buildDailyPlan(profile: OnboardingProfile | null | undefined): DailyPlanItem[] {
    if (!profile) return DEFAULT_PLAN

    const picks: DailyPlanItem[] = []

    picks.push({
        id: 'checkin_morning',
        label: `Check-in sáng (${profile.wake_time || '07:30'})`,
        icon: '🌅',
        route: ROUTE_PATHS.checkin,
    })

    const priorities = dedupe(profile.practice_ids || [])
    for (const practiceId of priorities) {
        if (EXCLUDED_TODAY_PRACTICES.has(practiceId)) continue
        const mapped = PRACTICE_PLAN_MAP[practiceId]
        if (!mapped) continue
        if (!picks.some((item) => item.id === mapped.id)) {
            picks.push(mapped)
        }
        if (picks.length >= 3) break
    }

    if (picks.length < 3) {
        if (hasEveningPractice(priorities)) {
            picks.push({
                id: 'journal_evening',
                label: `Nhìn lại cuối ngày (${profile.bed_time || '22:30'})`,
                icon: '🌙',
                route: `${ROUTE_PATHS.checkin}?variant=evening`,
            })
        } else {
            picks.push({
                id: 'checkin_evening',
                label: 'Check-in buổi tối',
                icon: '📓',
                route: `${ROUTE_PATHS.checkin}?variant=evening`,
            })
        }
    }

    while (picks.length < 3) {
        const nextFallback = DEFAULT_PLAN[picks.length]
        if (!picks.some((item) => item.id === nextFallback.id)) {
            picks.push(nextFallback)
        } else {
            break
        }
    }

    return picks.slice(0, 3)
}

export function buildPlanReason(profile: OnboardingProfile | null | undefined): string {
    if (!profile) return 'Bắt đầu nhẹ nhàng với 3 bước nhỏ để ổn định nhịp ngày.'
    if (profile.emotional_state === 'difficult_recently') {
        return 'Hôm nay mình ưu tiên các bước ngắn để giảm quá tải và lấy lại nhịp.'
    }
    if (profile.emotional_state === 'ongoing_challenges') {
        return 'Kế hoạch hôm nay tập trung vào thói quen đều đặn để bạn đỡ mệt hơn mỗi ngày.'
    }
    return 'Bạn đang làm tốt, kế hoạch này giúp duy trì trạng thái tích cực một cách bền vững.'
}

export const onboardingService = {
    getState: () =>
        httpClient.get<{ completed: boolean; skipped: boolean; profile: OnboardingProfile | null }>('/onboarding/state'),
    complete: (payload: Omit<OnboardingProfile, 'completed_at' | 'skipped'>) =>
        httpClient.postWithCsrf<{ completed: boolean; profile: OnboardingProfile }>('/onboarding/complete', payload),
    skip: () =>
        httpClient.postWithCsrf<{ completed: boolean; skipped: boolean; profile: OnboardingProfile }>('/onboarding/skip'),
}
