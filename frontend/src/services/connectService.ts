import { httpClient } from '../api/httpClient'

export type HotlineItem = { name: string; number: string; available?: string | null; note?: string | null }
export type ClinicItem = {
    name: string
    address?: string
    phone?: string
    lat?: number
    lng?: number
}

export const connectService = {
    hotlines: () => httpClient.get<{ hotlines: HotlineItem[] }>('/connect/hotlines'),
    clinics: (payload?: { lat?: number; lng?: number; radius_km?: number }) =>
        httpClient.post<{ clinics: ClinicItem[] }>('/connect/clinics', payload || {}),
}
