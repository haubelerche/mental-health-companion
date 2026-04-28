import { Loader2 } from 'lucide-react'

export type ChatSession = {
    session_id: string
    preview: string | null
    last_message_at: string
}

type ChatHistoryModalProps = {
    open: boolean
    loading: boolean
    sessions: ChatSession[]
    onClose: () => void
    onSelectSession: (sessionId: string) => void
}

export function ChatHistoryModal({ open, loading, sessions, onClose, onSelectSession }: ChatHistoryModalProps) {
    if (!open) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 py-6 backdrop-blur-md">
            <div className="absolute inset-0" onClick={onClose} aria-hidden="true" />
            <div className="relative z-10 w-full max-w-2xl overflow-hidden rounded-[28px] border border-white/35 bg-white/96 shadow-[0_30px_80px_rgba(15,23,42,0.22)]">
                <div className="flex items-start justify-between border-b border-serene-outline/20 px-5 py-4">
                    <div>
                        <p className="text-[10px] uppercase tracking-[0.24em] text-serene-muted">Lịch sử chat</p>
                        <p className="mt-1 text-sm font-semibold text-serene-ink">Các phiên trò chuyện gần đây</p>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded-full p-2 text-serene-muted transition hover:bg-serene-surface hover:text-serene-ink"
                        aria-label="Đóng lịch sử chat"
                    >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                            <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="max-h-[70vh] overflow-y-auto px-5 py-4">
                    {loading ? (
                        <div className="flex min-h-48 flex-col items-center justify-center gap-3 text-serene-muted">
                            <Loader2 className="h-6 w-6 animate-spin text-serene-primary" />
                            <p className="text-sm">Đang tải lịch sử chat...</p>
                        </div>
                    ) : sessions.length === 0 ? (
                        <p className="py-8 text-center text-sm text-serene-muted/70">Chưa có phiên nào.</p>
                    ) : (
                        <div className="space-y-2.5">
                            {sessions.map((sess) => (
                                <button
                                    key={sess.session_id}
                                    type="button"
                                    onClick={() => onSelectSession(sess.session_id)}
                                    className="w-full rounded-2xl border border-serene-outline/20 bg-white/70 px-4 py-3 text-left transition hover:bg-serene-accent/30 hover:border-serene-outline/35"
                                >
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="min-w-0 flex-1">
                                            <p className="truncate text-sm font-semibold text-serene-ink">
                                                {sess.preview || 'Phiên trò chuyện'}
                                            </p>
                                            <p className="mt-1 text-[11px] leading-relaxed text-serene-muted">
                                                {new Date(sess.last_message_at).toLocaleString('vi-VN')}
                                            </p>
                                        </div>
                                        <span className="mt-0.5 rounded-full bg-serene-primary/10 px-2 py-1 text-[10px] font-medium text-serene-primary">
                                            Mở
                                        </span>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}