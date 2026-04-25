import { httpClient } from '../api/httpClient'

export type CheckinQuickPayload = {
  mood: string
  stress_level?: number | null
  sleep_hours?: number | null
  study_hours?: number | null
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
