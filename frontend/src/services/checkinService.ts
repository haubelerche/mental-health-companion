import { httpClient } from '../api/httpClient'

export type MoodValue = 'awesome' | 'good' | 'fine' | 'bad' | 'terrible'

export type CheckinQuickPayload = {
  mood: MoodValue
  stress_level?: number | null
  sleep_hours?: number | null
  study_hours?: number | null
  emotions?: string[]
  triggers?: string[]
  note?: string | null
}

export type CheckinRewardResult = {
  granted: boolean
  amount: number
  reason: string
  balance: number
}

export type CheckinStreakResult = {
  current: number
  bonus_granted: boolean
  bonus_amount: number
}

export type CheckinQuickResponse = {
  checkin_id: string
  logged_at?: string
  updated?: boolean
  summary?: string
  reward?: CheckinRewardResult
  streak?: CheckinStreakResult
}

export const checkinService = {
  quickCheckin: (payload: CheckinQuickPayload) =>
    httpClient.postWithCsrf<CheckinQuickResponse>('/checkin/quick', payload),
}
