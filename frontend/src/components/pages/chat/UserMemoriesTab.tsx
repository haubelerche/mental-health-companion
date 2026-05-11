import { useEffect, useState } from 'react'
import type { UserMemory } from '../../../services/memoryService'
import { memoryService } from '../../../services/memoryService'
import { ApiRequestError } from '../../../api/types'
import Loading from '../../ui/Loading'
import PixelEmptyState from '../../pixel/PixelEmptyState'

function formatMemoryDate(value?: string | null): string {
    if (!value) return 'mem0_memories'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return 'mem0_memories'
    return date.toLocaleDateString('vi-VN')
}

function MemoryItem({ memory, onDelete }: {
    memory: UserMemory
    onDelete: (id: string) => Promise<void>
}) {
    const [busy, setBusy] = useState(false)

    async function handleDelete() {
        setBusy(true)
        try {
            await onDelete(memory.memory_id)
        } finally {
            setBusy(false)
        }
    }

    return (
        <div className="border border-theme-primary/30 bg-theme-surface px-5 py-4 text-sm">
            <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                    <p className="text-theme-text-secondary">{memory.content}</p>
                    <p className="mt-2 text-xs text-theme-accent">
                        {memory.source || 'session_summary'} · {formatMemoryDate(memory.created_at)}
                    </p>
                </div>
                <button
                    type="button"
                    disabled={busy}
                    onClick={() => void handleDelete()}
                    className="shrink-0 text-sm text-red-500 hover:underline disabled:opacity-50"
                >
                    Xoá
                </button>
            </div>
        </div>
    )
}

export default function UserMemoriesTab() {
    const [memories, setMemories] = useState<UserMemory[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        let cancelled = false
        memoryService.list()
            .then((data) => {
                if (!cancelled) setMemories(data.memories)
            })
            .catch(() => {
                if (!cancelled) setError('Không tải được ký ức. Vui lòng thử lại.')
            })
            .finally(() => {
                if (!cancelled) setLoading(false)
            })
        return () => { cancelled = true }
    }, [])

    async function handleDelete(memoryId: string) {
        try {
            await memoryService.delete(memoryId)
            setMemories((prev) => prev.filter((memory) => memory.memory_id !== memoryId))
        } catch (err) {
            if (err instanceof ApiRequestError) {
                setError(err.message)
            } else {
                setError('Không xoá được ký ức. Vui lòng thử lại.')
            }
        }
    }

    if (loading) return <Loading />
    if (error) return <p className="p-4 text-sm text-red-500">{error}</p>

    if (memories.length === 0) {
        return (
            <div className="p-4">
                <PixelEmptyState
                    mascot="main"
                    title="Chưa có ký ức nào"
                    description="Serene sẽ lưu những điều quan trọng từ các cuộc trò chuyện khi có đủ ngữ cảnh phù hợp."
                />
            </div>
        )
    }

    return (
        <div className="flex flex-col gap-2 p-4">
            {memories.map((memory) => (
                <MemoryItem key={memory.memory_id} memory={memory} onDelete={handleDelete} />
            ))}
        </div>
    )
}
