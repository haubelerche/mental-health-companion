import { httpClient } from '../api/httpClient'

export type MoodCheckinPayload = {
    mood: string
    emoji?: string
    note?: string
}

export type HomeFeed = {
    quote_of_day: { text: string; author?: string | null }
    mood_today: { checked_in: boolean; mood: string | null; emoji: string | null }
    dynamic_suggestion?: { type: string; reason: string; message: string } | null
}

export const homeService = {
    checkin: (payload: MoodCheckinPayload) =>
        httpClient.postWithCsrf<{ checkin_id: string; logged_at: string }>('/mood/checkin', payload),
    feed: () => httpClient.get<HomeFeed>('/home/feed'),
}
