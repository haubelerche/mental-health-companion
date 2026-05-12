import { httpClient } from '../api/httpClient'

export type OnboardingTourStatus =
    | 'not_started'
    | 'available'
    | 'in_progress'
    | 'paused_for_safety'
    | 'completed'
    | 'skipped'
    | 'dismissed'

export type OnboardingTourActionKind =
    | 'read_only'
    | 'navigate'
    | 'optional_try'
    | 'complete_real_action'

export type OnboardingTourStep = {
    step_id: string
    route: string
    target_anchor_id: string | null
    title: string
    body: string
    primary_cta: string
    secondary_cta?: string | null
    allow_skip: boolean
    requires_navigation: boolean
    action_kind: OnboardingTourActionKind
}

export type OnboardingTourState = {
    status: OnboardingTourStatus
    current_step_id: string | null
    steps: OnboardingTourStep[]
    completed_step_ids: string[]
    skipped_step_ids: string[]
    variant: string
    safe_profile_summary?: {
        display_name?: string
        support_goal?: string
        preferred_style?: string
    }
}

export const onboardingTourService = {
    getState: () => httpClient.get<OnboardingTourState>('/onboarding/tour'),
    start: (variant = 'first_run') =>
        httpClient.postWithCsrf<OnboardingTourState>('/onboarding/tour/start', { variant }),
    progress: (payload: { step_id: string; skipped?: boolean; next_step_id?: string | null }) =>
        httpClient.patchWithCsrf<OnboardingTourState>('/onboarding/tour/progress', payload),
    complete: () => httpClient.postWithCsrf<OnboardingTourState>('/onboarding/tour/complete', {}),
    skip: () => httpClient.postWithCsrf<OnboardingTourState>('/onboarding/tour/skip', {}),
    dismiss: () => httpClient.postWithCsrf<OnboardingTourState>('/onboarding/tour/dismiss', {}),
}
