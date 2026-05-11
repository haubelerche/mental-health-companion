import { useState } from 'react'
import { httpClient } from '../../../api/httpClient'
import { ApiRequestError } from '../../../api/types'
import Mascot from '../../pixel/Mascot'

type LetterStatus =
    | 'draft'
    | 'pending_review'
    | 'approved'
    | 'too_short'
    | 'rejected_harmful'
    | 'needs_review'

type LetterResponse = {
    letter_id: string
    status: LetterStatus
    reward?: { granted: boolean; amount: number } | null
}

const STATUS_UI: Record<LetterStatus, { label: string; color: string }> = {
    draft: { label: 'Bản nháp', color: 'text-gray-500' },
    pending_review: { label: 'Đang xét duyệt', color: 'text-yellow-600' },
    approved: { label: 'Đã duyệt', color: 'text-green-600' },
    too_short: { label: 'Quá ngắn (cần hơn 100 từ)', color: 'text-orange-500' },
    rejected_harmful: { label: 'Không được duyệt vì nội dung không phù hợp', color: 'text-red-500' },
    needs_review: { label: 'Cần xem xét thêm', color: 'text-purple-500' },
}

export default function LetterComposer() {
    const [content, setContent] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [result, setResult] = useState<LetterResponse | null>(null)
    const [error, setError] = useState<string | null>(null)

    const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault()
        if (!content.trim()) return
        setSubmitting(true)
        setError(null)
        try {
            const data = await httpClient.postWithCsrf<LetterResponse>('/letters', { content })
            setResult(data)
            setContent('')
        } catch (err) {
            if (err instanceof ApiRequestError) {
                setError(err.message)
            } else {
                setError('Không thể gửi thư. Vui lòng thử lại.')
            }
        } finally {
            setSubmitting(false)
        }
    }

    if (result) {
        const ui = STATUS_UI[result.status] ?? STATUS_UI.draft
        return (
            <div className="rounded-xl border border-gray-200 bg-white p-4">
                <div className="flex items-center gap-3">
                    <Mascot variant="idle" size="sm" decorative />
                    <p className={`text-sm font-medium ${ui.color}`}>{ui.label}</p>
                </div>
                {result.status === 'approved' && result.reward?.granted && (
                    <p className="text-xs text-green-600 mt-1">
                        +{result.reward.amount} Tim đã được cộng vào tài khoản của bạn.
                    </p>
                )}
                <button
                    type="button"
                    onClick={() => setResult(null)}
                    className="mt-3 text-xs text-indigo-600 hover:underline"
                >
                    Viết thư mới
                </button>
            </div>
        )
    }

    return (
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="flex items-center gap-3 rounded-xl border border-gray-100 bg-white/70 px-3 py-2">
                <Mascot variant="idle" size="sm" decorative />
                <p className="text-xs leading-relaxed text-gray-500">
                    Viết chậm cũng được. Serene chỉ gửi khi bạn chủ động bấm nút.
                </p>
            </div>
            <textarea
                className="rounded-xl border border-gray-200 p-3 text-sm resize-none focus:outline-none
                    focus:ring-2 focus:ring-indigo-400"
                rows={8}
                placeholder="Viết điều bạn muốn chia sẻ (hơn 100 từ để nhận Tim)…"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                disabled={submitting}
            />
            <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">{wordCount} từ</span>
                <button
                    type="submit"
                    disabled={submitting || !content.trim()}
                    className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white
                        hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {submitting ? 'Đang gửi…' : 'Gửi thư'}
                </button>
            </div>
            {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
        </form>
    )
}
