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

export interface MealHistoryItem {
    meal_slot: MealSlot
    meal_date: string
    items_text: string
    created_at: string
}

export interface MealHistoryResponse {
    checkins: MealHistoryItem[]
}

class NutritionService {
    async getTodayCheckins(): Promise<TodayCheckinsResponse> {
        return httpClient.get<TodayCheckinsResponse>('/nutrition/meal-checkins/today')
    }

    async getMealHistory(limit = 50): Promise<MealHistoryResponse> {
        return httpClient.get<MealHistoryResponse>(`/nutrition/meal-checkins?limit=${limit}`)
    }

    async postMealCheckin(data: MealCheckinRequest): Promise<MealCheckinResponse> {
        return httpClient.postWithCsrf<MealCheckinResponse>('/nutrition/meal-checkins', data)
    }
}

export const nutritionService = new NutritionService()
