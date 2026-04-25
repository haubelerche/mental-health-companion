import { httpClient } from '../api/httpClient'

// Fields hold the user's free-text answer (e.g. "Có" / "Không"). Backend accepts any string.
export type SafetyCheckPayload = {
  overwhelmed: string
  unsafe: string
  need_help_now: string
}

export type SafetyCheckResult = {
  risk_score: number
  risk_level: number
  should_route_crisis: boolean
  recommended_next_step: 'chat_de_escalation' | 'checkin_or_chat'
}

export type Hotline = {
  name: string
  number: string
  available: string
  note: string | null
}

export type ReferralOption = {
  type: 'counselor' | 'trusted_contact' | 'clinic'
}

export const safetyService = {
  check: (payload: SafetyCheckPayload) =>
    httpClient.postWithCsrf<SafetyCheckResult>('/intake/safety-check', payload),

  getHotlines: () =>
    httpClient.get<{ hotlines: Hotline[] }>('/safety/hotlines'),

  getReferralOptions: () =>
    httpClient.get<{ options: ReferralOption[] }>('/safety/referrals/options'),
}
