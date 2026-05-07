import { useState } from 'react'
import { checkinService } from '../../services/checkinService'
import { ApiRequestError } from '../../api/types'

type Props = {
    onComplete?: (result: unknown) => void
}

/** Check-in cảm xúc nhanh nhận Tim — không chọn persona ở đây (persona nằm trong menu Tùy chọn). */
export default function ChatEntryCheckIn({ onComplete }: Props) {
    const [submitting, setSubmitting] = useState(false)
    const [done, setDone] = useState(false)
    const [error, setError] = useState<string | null>(null)

    async function handleCheckIn() {
        setSubmitting(true)
        setError(null)
        try {
            const result = await checkinService.quickCheckin({ mood: 'fine' })
            setDone(true)
            onComplete?.(result)
        } catch (err) {
            if (err instanceof ApiRequestError) setError(err.message)
            else setError('Không thể check-in cảm xúc lúc này. Vui lòng thử lại.')
        } finally {
            setSubmitting(false)
        }
    }

    if (done) {
        return (
            <div className="rounded-xl border border-green-200 bg-green-50 p-3 text-sm text-green-700">
                Đã check-in cảm xúc hôm nay ✓
            </div>
        )
    }

    return (
        <div className="flex flex-col gap-2 rounded-xl border border-indigo-200 bg-indigo-50 p-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-indigo-800">Hôm nay bạn thế nào? Check-in cảm xúc để nhận Tim nhé.</p>
            <button
                type="button"
                disabled={submitting}
                onClick={() => void handleCheckIn()}
                className="shrink-0 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
                {submitting ? '…' : 'Check-in'}
            </button>
            {error && <p className="sr-only" role="alert">{error}</p>}
        </div>
    )
}
