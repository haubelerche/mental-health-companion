import { useState } from 'react'
import { httpClient } from '../../api/httpClient'
import { ApiRequestError } from '../../api/types'

type MealSlot = 'breakfast' | 'lunch' | 'dinner'

const SLOT_LABELS: Record<MealSlot, string> = {
    breakfast: 'Bữa sáng',
    lunch: 'Bữa trưa',
    dinner: 'Bữa tối',
}

type CheckInResult = {
    meal_slot: MealSlot
    meal_date: string
    reward?: { granted: boolean; amount: number } | null
}

type Props = {
    claimedSlots?: MealSlot[]
    onCheckin?: (slot: MealSlot, result: CheckInResult) => void
}

export default function MealCheckInCard({ claimedSlots = [], onCheckin }: Props) {
    const [busy, setBusy] = useState<MealSlot | null>(null)
    const [localClaimed, setLocalClaimed] = useState<Set<MealSlot>>(new Set(claimedSlots))
    const [error, setError] = useState<string | null>(null)

    async function handleCheckin(slot: MealSlot) {
        if (localClaimed.has(slot)) return
        setBusy(slot)
        setError(null)
        try {
            const result = await httpClient.postWithCsrf<CheckInResult>('/nutrition/meal-checkins', {
                meal_slot: slot,
            })
            setLocalClaimed((prev) => new Set([...prev, slot]))
            onCheckin?.(slot, result)
        } catch (err) {
            if (err instanceof ApiRequestError && err.code === 'already_claimed') {
                setLocalClaimed((prev) => new Set([...prev, slot]))
            } else {
                setError('Không thể ghi nhận bữa ăn lúc này.')
            }
        } finally {
            setBusy(null)
        }
    }

    return (
        <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-sm font-semibold text-gray-700 mb-3">Ghi nhận bữa ăn hôm nay</p>
            <div className="flex gap-2">
                {(Object.keys(SLOT_LABELS) as MealSlot[]).map((slot) => {
                    const claimed = localClaimed.has(slot)
                    return (
                        <button
                            key={slot}
                            type="button"
                            disabled={claimed || busy === slot}
                            onClick={() => handleCheckin(slot)}
                            className="flex-1 rounded-lg border py-2 text-xs font-medium transition-colors
                                disabled:cursor-default
                                data-[claimed=true]:border-green-300 data-[claimed=true]:bg-green-50 data-[claimed=true]:text-green-700
                                data-[claimed=false]:border-gray-200 data-[claimed=false]:hover:border-indigo-400 data-[claimed=false]:hover:bg-indigo-50"
                            data-claimed={claimed}
                        >
                            {busy === slot ? '…' : claimed ? `${SLOT_LABELS[slot]} ✓` : SLOT_LABELS[slot]}
                        </button>
                    )
                })}
            </div>
            {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
        </div>
    )
}
