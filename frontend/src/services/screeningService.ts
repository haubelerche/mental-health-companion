import { httpClient } from '../api/httpClient'

export type ScreeningId = 'phq9' | 'gad7' | 'dass21' | 'mdq' | 'pcl5'

export type ScreeningInstrument = {
  id: ScreeningId
  title: string
  item_count: number
}

export type ScreeningResult = {
  instrument_id: ScreeningId
  raw_score: number
  severity_label: 'minimal' | 'mild' | 'moderate' | 'moderately_severe' | 'severe' | 'assessed' | 'positive' | 'negative' | 'high_risk' | 'low_risk'
  saved: boolean
  assessment_updated_at: string
}

/** Safe result from GET /screenings/latest — no raw_score exposed. */
export type ScreeningLatestEntry = {
  instrument_id: ScreeningId
  severity_label: ScreeningResult['severity_label']
  assessment_updated_at: string | null
}

export const screeningService = {
  getCatalog: () =>
    httpClient.get<{ instruments: ScreeningInstrument[] }>('/screenings/catalog'),

  submit: (payload: { instrument_id: ScreeningId; answers: Record<string, number> }) =>
    httpClient.postWithCsrf<ScreeningResult>('/screenings/submit', payload),

  /** Fetch latest screening results for all instruments from backend DB. */
  getLatest: () =>
    httpClient.get<{ results: Record<ScreeningId, ScreeningLatestEntry | null> }>('/screenings/latest'),
}
