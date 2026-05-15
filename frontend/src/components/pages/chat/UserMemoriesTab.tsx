import { MoreHorizontal, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { UserMemory } from '../../../services/memoryService'
import { memoryService } from '../../../services/memoryService'
import { ApiRequestError } from '../../../api/types'
import Loading from '../../ui/Loading'
import PixelEmptyState from '../../pixel/PixelEmptyState'

const ALL_CATEGORIES = 'Tất cả'

function memoryId(memory: UserMemory): string {
    return memory.id || memory.memory_id || memory.card_id || ''
}

function memoryText(memory: UserMemory): string {
    return memory.display_text || memory.body || memory.content || ''
}

function category(memory: UserMemory): string {
    return memory.display_category || memory.badge_label || memory.title || 'Ký ức'
}

function mentionChip(memory: UserMemory): string | null {
    const count = Number(memory.mention_count || 1)
    if (count <= 1) return null
    return `Nhắc lại ${count} lần`
}

function isPending(memory: UserMemory): boolean {
    return memory.status === 'pending_user_review'
}

function NewMemoryModal({
    memories,
    onClose,
    onKeepSelected,
}: {
    memories: UserMemory[]
    onClose: () => void
    onKeepSelected: (ids: string[]) => Promise<void>
}) {
    const [selected, setSelected] = useState(() => new Set(memories.map(memoryId)))
    const [busy, setBusy] = useState(false)

    async function keepSelected() {
        setBusy(true)
        try {
            await onKeepSelected(Array.from(selected))
            onClose()
        } finally {
            setBusy(false)
        }
    }

    return (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/55 px-4">
            <section className="w-full max-w-2xl border border-theme-primary/35 bg-theme-surface p-4 shadow-2xl">
                <div className="mb-3 flex items-start justify-between gap-3">
                    <div>
                        <h2 className="text-lg font-semibold text-theme-text-primary">Ký ức mới</h2>
                        <p className="mt-1 text-sm text-theme-text-secondary">
                            Serene vừa nhận ra vài điều có thể giúp lần trò chuyện sau dễ hơn. Bạn chọn điều muốn giữ lại.
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="border border-theme-primary/30 p-1.5 text-theme-text-secondary hover:bg-theme-primary/10"
                        aria-label="Đóng"
                    >
                        <X size={16} />
                    </button>
                </div>

                <div className="max-h-[52vh] space-y-2 overflow-y-auto pr-1">
                    {memories.map((memory) => {
                        const id = memoryId(memory)
                        const checked = selected.has(id)
                        return (
                            <button
                                key={id}
                                type="button"
                                onClick={() => {
                                    setSelected((prev) => {
                                        const next = new Set(prev)
                                        if (next.has(id)) next.delete(id)
                                        else next.add(id)
                                        return next
                                    })
                                }}
                                className="flex w-full items-center gap-3 border border-theme-primary/25 bg-theme-bg/70 px-3 py-2 text-left hover:bg-theme-primary/10"
                            >
                                <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-xs ${checked ? 'border-theme-accent bg-theme-accent text-theme-bg' : 'border-theme-primary/40 text-transparent'}`}>
                                    ✓
                                </span>
                                <span className="min-w-0 flex-1 text-sm text-theme-text-primary">{memoryText(memory)}</span>
                                {mentionChip(memory) && (
                                    <span className="shrink-0 border border-theme-primary/25 px-2 py-0.5 text-[11px] text-theme-text-secondary">
                                        {mentionChip(memory)}
                                    </span>
                                )}
                            </button>
                        )
                    })}
                </div>

                <div className="mt-4 flex justify-end gap-2">
                    <button
                        type="button"
                        disabled={busy}
                        onClick={onClose}
                        className="border border-theme-primary/25 px-3 py-2 text-xs font-semibold text-theme-text-secondary hover:bg-theme-primary/10 disabled:opacity-50"
                    >
                        Bỏ qua
                    </button>
                    {memories.length <= 8 && (
                        <button
                            type="button"
                            disabled={busy}
                            onClick={() => {
                                setSelected(new Set(memories.map(memoryId)))
                                void keepSelected()
                            }}
                            className="border border-theme-primary/35 px-3 py-2 text-xs font-semibold text-theme-text-primary hover:bg-theme-primary/10 disabled:opacity-50"
                        >
                            Giữ tất cả
                        </button>
                    )}
                    <button
                        type="button"
                        disabled={busy || selected.size === 0}
                        onClick={() => void keepSelected()}
                        className="border border-theme-primary/40 bg-theme-primary/10 px-3 py-2 text-xs font-semibold text-theme-accent hover:bg-theme-primary/20 disabled:opacity-50"
                    >
                        Giữ đã chọn
                    </button>
                </div>
            </section>
        </div>
    )
}

function MemoryRow({
    memory,
    onChanged,
    onDelete,
}: {
    memory: UserMemory
    onChanged: (memory: UserMemory) => void
    onDelete: (id: string) => Promise<void>
}) {
    const [open, setOpen] = useState(false)
    const [editing, setEditing] = useState(false)
    const [draft, setDraft] = useState(memoryText(memory))
    const [busy, setBusy] = useState(false)
    const id = memoryId(memory)

    async function run(action: 'keep' | 'edit' | 'delete' | 'disable_personalization') {
        if (!id) return
        setBusy(true)
        try {
            if (action === 'delete') {
                await onDelete(id)
                return
            }
            if (action === 'edit') {
                const trimmed = draft.trim()
                if (!trimmed || trimmed === memoryText(memory)) {
                    setEditing(false)
                    return
                }
                const res = await memoryService.edit(id, trimmed)
                onChanged(res.memory_card)
                setEditing(false)
                setOpen(false)
                return
            }
            const res = action === 'keep'
                ? await memoryService.keep(id)
                : await memoryService.disablePersonalization(id)
            onChanged(res.memory_card)
            setOpen(false)
        } finally {
            setBusy(false)
        }
    }

    return (
        <div className="border border-theme-primary/20 bg-theme-surface/85 px-3 py-2 rounded-lg">
            <div className="flex items-center gap-3">
                <div className="min-w-0 flex-1">
                    {editing ? (
                        <input
                            value={draft}
                            onChange={(event) => setDraft(event.target.value)}
                            maxLength={180}
                            className="w-full border border-theme-primary/30 bg-theme-bg px-2 py-1.5 text-sm text-theme-text-primary outline-none focus:border-theme-accent"
                        />
                    ) : (
                        <p className="truncate text-sm text-theme-text-primary">{memoryText(memory)}</p>
                    )}
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-theme-text-secondary/75">
                        {mentionChip(memory) && <span>{mentionChip(memory)}</span>}
                        {isPending(memory) && <span>Chờ bạn xác nhận</span>}
                        {memory.personalization_disabled && <span>Không dùng để cá nhân hóa</span>}
                    </div>
                </div>
                {editing ? (
                    <div className="flex shrink-0 gap-1">
                        <button disabled={busy} onClick={() => void run('edit')} className="border border-theme-primary/35 px-2 py-1 text-xs text-theme-accent disabled:opacity-50">Lưu</button>
                        <button disabled={busy} onClick={() => setEditing(false)} className="border border-theme-primary/20 px-2 py-1 text-xs text-theme-text-secondary disabled:opacity-50">Hủy</button>
                    </div>
                ) : (
                    <div className="relative shrink-0">
                        <button
                            type="button"
                            disabled={busy}
                            onClick={() => setOpen((value) => !value)}
                            className="border border-theme-primary/20 p-1.5 text-theme-text-secondary hover:bg-theme-primary/10 disabled:opacity-50"
                            aria-label="Tùy chọn ký ức"
                        >
                            <MoreHorizontal size={15} />
                        </button>
                        {open && (
                            <div className="absolute right-0 top-8 z-20 w-48 border border-theme-primary/30 bg-theme-surface p-1 shadow-xl">
                                {isPending(memory) && (
                                    <button onClick={() => void run('keep')} className="block w-full px-3 py-2 text-left text-xs text-theme-text-primary hover:bg-theme-primary/10">Giữ lại</button>
                                )}
                                <button onClick={() => { setDraft(memoryText(memory)); setEditing(true); setOpen(false) }} className="block w-full px-3 py-2 text-left text-xs text-theme-text-primary hover:bg-theme-primary/10">Sửa</button>
                                {!memory.personalization_disabled && (
                                    <button onClick={() => void run('disable_personalization')} className="block w-full px-3 py-2 text-left text-xs text-theme-text-secondary hover:bg-theme-primary/10">Không dùng để cá nhân hóa</button>
                                )}
                                <button onClick={() => void run('delete')} className="block w-full px-3 py-2 text-left text-xs text-red-500 hover:bg-red-500/10">Xóa</button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}

type UserMemoriesTabProps = {
    refreshKey?: number
}

export default function UserMemoriesTab({ refreshKey = 0 }: UserMemoriesTabProps) {
    const [memories, setMemories] = useState<UserMemory[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [retryKey, setRetryKey] = useState(0)
    const [activeCategory, setActiveCategory] = useState(ALL_CATEGORIES)
    const [showNewModal, setShowNewModal] = useState(false)

    useEffect(() => {
        let cancelled = false
        setLoading(true)
        setError(null)
        memoryService.list()
            .then((data) => {
                if (cancelled) return
                const next = Array.isArray(data.memories) ? data.memories : []
                setMemories(next)
                setShowNewModal(next.some(isPending))
            })
            .catch((err) => {
                if (cancelled) return
                if (err instanceof ApiRequestError && (err.code === 'DATABASE_UNAVAILABLE' || err.status === 503)) {
                    setError('Ký ức đang tạm thời chưa tải được. Thử lại sau một chút.')
                    return
                }
                setError(err instanceof ApiRequestError ? err.message : 'Không tải được ký ức. Vui lòng thử lại.')
            })
            .finally(() => {
                if (!cancelled) setLoading(false)
            })
        return () => { cancelled = true }
    }, [refreshKey, retryKey])

    const categories = useMemo(() => {
        const values = Array.from(new Set(memories.map(category).filter(Boolean)))
        return [ALL_CATEGORIES, ...values]
    }, [memories])

    const visibleMemories = useMemo(() => {
        return memories.filter((memory) => activeCategory === ALL_CATEGORIES || category(memory) === activeCategory)
    }, [activeCategory, memories])

    const grouped = useMemo(() => {
        const map = new Map<string, UserMemory[]>()
        for (const memory of visibleMemories) {
            const key = category(memory)
            map.set(key, [...(map.get(key) || []), memory])
        }
        return Array.from(map.entries())
    }, [visibleMemories])

    function updateMemory(next: UserMemory) {
        setMemories((prev) => prev.map((memory) => memoryId(memory) === memoryId(next) ? next : memory))
    }

    async function handleDelete(id: string) {
        try {
            await memoryService.delete(id)
            setMemories((prev) => prev.filter((memory) => memoryId(memory) !== id))
        } catch (err) {
            setError(err instanceof ApiRequestError ? err.message : 'Không xóa được ký ức. Vui lòng thử lại.')
        }
    }

    async function keepSelected(ids: string[]) {
        for (const id of ids) {
            const res = await memoryService.keep(id)
            updateMemory(res.memory_card)
        }
    }

    if (loading) return <Loading />
    if (error) {
        return (
            <div className="p-4 text-sm text-red-500">
                <p>{error}</p>
                <button
                    type="button"
                    onClick={() => setRetryKey((value) => value + 1)}
                    className="mt-3 border border-red-500/40 px-3 py-2 text-xs font-semibold uppercase tracking-wide hover:bg-red-500/10"
                >
                    Thử lại
                </button>
            </div>
        )
    }

    if (memories.length === 0) {
        return (
            <div className="p-4">
                <PixelEmptyState
                    mascot="main"
                    title="Chưa có ký ức nào."
                    description="Serene sẽ chỉ giữ những câu ngắn giúp lần trò chuyện sau dễ chịu hơn."
                />
            </div>
        )
    }

    const pendingMemories = memories.filter(isPending)

    return (
        <div className="p-4">
            {showNewModal && pendingMemories.length > 0 && (
                <NewMemoryModal
                    memories={pendingMemories}
                    onClose={() => setShowNewModal(false)}
                    onKeepSelected={keepSelected}
                />
            )}

            <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
                {categories.map((item) => (
                    <button
                        key={item}
                        type="button"
                        onClick={() => setActiveCategory(item)}
                        className={`shrink-0 border rounded-lg px-3 py-1.5 text-xs font-semibold ${activeCategory === item ? 'border-theme-accent text-theme-accent' : 'border-theme-primary/25 text-theme-text-secondary hover:bg-theme-primary/10'}`}
                    >
                        {item}
                    </button>
                ))}
            </div>

            <div className="space-y-4">
                {grouped.map(([group, items]) => (
                    <section key={group}>
                        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-theme-accent">{group}</h3>
                        <div className="space-y-2">
                            {items.map((memory) => (
                                <MemoryRow
                                    key={memoryId(memory)}
                                    memory={memory}
                                    onChanged={updateMemory}
                                    onDelete={handleDelete}
                                />
                            ))}
                        </div>
                    </section>
                ))}
            </div>
        </div>
    )
}
