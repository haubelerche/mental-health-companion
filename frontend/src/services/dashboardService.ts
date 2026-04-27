import { httpClient } from '../api/httpClient'

export type NutritionDailyTip = {
    day_index: number
    dish: string
    benefit: string
    tip: string
    timezone: string
}

export const dashboardService = {
    getNutritionDailyTip: () => httpClient.get<NutritionDailyTip>('/dashboard/nutrition-daily'),
}
