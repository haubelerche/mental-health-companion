import { httpClient } from '../api/httpClient'

export type ScreeningInstrument = {
  id: 'phq9' | 'gad7'
  title: string
  item_count: number
}

export type ScreeningResult = {
  instrument_id: string
  raw_score: number
  severity_label: 'minimal' | 'mild' | 'moderate' | 'moderately_severe' | 'severe'
  saved: boolean
  assessment_updated_at: string
}

export const screeningService = {
  getCatalog: () =>
    httpClient.get<{ instruments: ScreeningInstrument[] }>('/screenings/catalog'),

  submit: (payload: { instrument_id: 'phq9' | 'gad7'; answers: Record<string, number> }) =>
    httpClient.postWithCsrf<ScreeningResult>('/screenings/submit', payload),
}
