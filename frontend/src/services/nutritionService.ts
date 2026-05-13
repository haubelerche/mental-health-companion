import { httpClient } from '../api/httpClient'

export type MealSlot = 'breakfast' | 'lunch' | 'dinner'

export interface MealCheckinRequest {
    meal_slot: MealSlot
    items_text: string
    photo_url?: string
    mood_before?: string
    mood_after?: string
}

export interface MealCheckinResponse {
    checkin_id: string
    reward: {
        granted: boolean
        amount: number
        balance?: number
        reason?: string
    }
}

export interface TodayCheckinsResponse {
    meal_date: string
    claimed_slots: MealSlot[]
    checkins: Array<{
        meal_slot: MealSlot
        items_text: string
        created_at: string
    }>
}

class NutritionService {
    async getTodayCheckins(): Promise<TodayCheckinsResponse> {
        return httpClient.get<TodayCheckinsResponse>('/nutrition/meal-checkins/today')
    }

    async postMealCheckin(data: MealCheckinRequest): Promise<MealCheckinResponse> {
        return httpClient.postWithCsrf<MealCheckinResponse>('/nutrition/meal-checkins', data)
    }
}

export const nutritionService = new NutritionService()
