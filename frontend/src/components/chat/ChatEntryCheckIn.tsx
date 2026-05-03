import { useState } from 'react'
import { httpClient } from '../../api/httpClient'
import { ApiRequestError } from '../../api/types'

type CheckInResult = {
    reward?: { granted: boolean; amount: number; new_balance: number }
    streak?: { current: number; bonus_granted: boolean; bonus_amount: number }
}

type Props = {
    onComplete?: (result: CheckInResult) => void
}

export default function ChatEntryCheckIn({ onComplete }: Props) {
    const [submitting, setSubmitting] = useState(false)
    const [done, setDone] = useState(false)
    const [error, setError] = useState<string | null>(null)

    async function handleCheckIn() {
        setSubmitting(true)
        setError(null)
        try {
            const result = await httpClient.postWithCsrf<CheckInResult>('/mood/checkins', {})
            setDone(true)
            onComplete?.(result)
        } catch (err) {
            if (err instanceof ApiRequestError && err.code === 'already_claimed') {
                setDone(true)
            } else {
                setError('Không thể điểm danh lúc này. Vui lòng thử lại.')
            }
        } finally {
            setSubmitting(false)
        }
    }

    if (done) {
        return (
            <div className="rounded-xl bg-green-50 border border-green-200 p-3 text-sm text-green-700">
                Đã điểm danh hôm nay ✓
            </div>
        )
    }

    return (
        <div className="rounded-xl bg-indigo-50 border border-indigo-200 p-3 flex items-center justify-between">
            <p className="text-sm text-indigo-800">Hôm nay bạn thế nào? Điểm danh để nhận Tim nhé!</p>
            <button
                type="button"
                disabled={submitting}
                onClick={handleCheckIn}
                className="ml-3 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white
                    hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
                {submitting ? '…' : 'Điểm danh'}
            </button>
            {error && <p className="sr-only" role="alert">{error}</p>}
        </div>
    )
}
