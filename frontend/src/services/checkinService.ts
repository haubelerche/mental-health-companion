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

export type CheckinQuickResponse = {
  checkin_id: string
  logged_at: string
}

export const checkinService = {
  quickCheckin: (payload: CheckinQuickPayload) =>
    httpClient.postWithCsrf<CheckinQuickResponse>('/checkin/quick', payload),
}
