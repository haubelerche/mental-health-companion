import { useEffect, useState } from 'react'
import type { MemoryCard } from '../../services/memoryCardsService'
import { memoryCardsService } from '../../services/memoryCardsService'
import { ApiRequestError } from '../../api/types'
import Loading from '../ui/Loading'

const STATUS_LABELS: Record<string, string> = {
    active: 'Đang dùng',
    pending_user_review: 'Chờ xác nhận',
    edited_by_user: 'Đã chỉnh sửa',
    rejected_by_guardrail: 'Không lưu',
    deleted_by_user: 'Đã xoá',
}

function MemoryCardItem({ card, onAction }: {
    card: MemoryCard
    onAction: (id: string, action: 'keep' | 'edit' | 'delete', opts?: { new_content?: string }) => Promise<void>
}) {
    const [editing, setEditing] = useState(false)
    const [editContent, setEditContent] = useState(card.content)
    const [busy, setBusy] = useState(false)

    async function act(action: 'keep' | 'edit' | 'delete', opts?: { new_content?: string }) {
        setBusy(true)
        await onAction(card.card_id, action, opts)
        setBusy(false)
        setEditing(false)
    }

    if (card.status === 'deleted_by_user') return null

    return (
        <div className="rounded-lg border border-gray-200 bg-theme-surface/60 p-3 text-sm">
            <div className="flex items-start justify-between gap-2">
                <div>
                    <p className="font-medium text-theme-text-primary">{card.title}</p>
                    {editing ? (
                        <textarea
                            className="mt-1 w-full rounded border border-gray-300 p-1.5 text-xs"
                            rows={3}
                            value={editContent}
                            onChange={(e) => setEditContent(e.target.value)}
                        />
                    ) : (
                        <p className="text-theme-text-secondary mt-0.5">{card.content}</p>
                    )}
                    <p className="text-xs text-theme-text-secondary mt-1">
                        {STATUS_LABELS[card.status] ?? card.status}
                    </p>
                </div>
                {!editing && card.status === 'pending_user_review' && (
                    <div className="flex gap-1.5 shrink-0">
                        <button
                            type="button"
                            disabled={busy}
                            onClick={() => act('keep')}
                            className="text-xs text-theme-accent hover:underline disabled:opacity-50"
                        >
                            Lưu
                        </button>
                        <button
                            type="button"
                            disabled={busy}
                            onClick={() => act('delete')}
                            className="text-xs text-red-500 hover:underline disabled:opacity-50"
                        >
                            Xoá
                        </button>
                    </div>
                )}
                {!editing && card.status === 'active' && (
                    <div className="flex gap-1.5 shrink-0">
                        <button
                            type="button"
                            disabled={busy}
                            onClick={() => setEditing(true)}
                            className="text-xs text-indigo-600 hover:underline disabled:opacity-50"
                        >
                            Sửa
                        </button>
                        <button
                            type="button"
                            disabled={busy}
                            onClick={() => act('delete')}
                            className="text-xs text-red-500 hover:underline disabled:opacity-50"
                        >
                            Xoá
                        </button>
                    </div>
                )}
            </div>
            {editing && (
                <div className="flex gap-2 mt-2">
                    <button
                        type="button"
                        disabled={busy}
                        onClick={() => act('edit', { new_content: editContent })}
                        className="text-xs rounded bg-indigo-600 text-white px-2 py-1 hover:bg-indigo-700 disabled:opacity-50"
                    >
                        Lưu
                    </button>
                    <button
                        type="button"
                        onClick={() => { setEditing(false); setEditContent(card.content) }}
                        className="text-xs text-gray-500 hover:underline"
                    >
                        Huỷ
                    </button>
                </div>
            )}
        </div>
    )
}

export default function MemoryCardsTab() {
    const [cards, setCards] = useState<MemoryCard[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        let cancelled = false
        memoryCardsService.list()
            .then((data) => { if (!cancelled) setCards(data.cards) })
            .catch(() => { if (!cancelled) setError('Không tải được ký ức. Vui lòng thử lại.') })
            .finally(() => { if (!cancelled) setLoading(false) })
        return () => { cancelled = true }
    }, [])

    async function handleAction(
        cardId: string,
        action: 'keep' | 'edit' | 'delete',
        opts?: { new_content?: string },
    ) {
        try {
            const data = await memoryCardsService.applyAction(cardId, action, opts)
            setCards((prev) => prev.map((c) => c.card_id === cardId ? data.card : c))
        } catch (err) {
            if (err instanceof ApiRequestError) {
                setError(err.message)
            }
        }
    }

    if (loading) return <Loading/>
    if (error) return <p className="text-sm text-red-500 p-4">{error}</p>

    const visible = cards.filter((c) => c.status !== 'deleted_by_user')
    if (visible.length === 0) {
        return (
            <p className="text-sm text-theme-text-secondary p-4">
                Chưa có ký ức nào. Serene sẽ ghi nhớ những điều quan trọng từ các cuộc trò chuyện của bạn.
            </p>
        )
    }

    return (
        <div className="flex flex-col gap-2 p-4">
            {cards.map((card) => (
                <MemoryCardItem key={card.card_id} card={card} onAction={handleAction} />
            ))}
        </div>
    )
}
