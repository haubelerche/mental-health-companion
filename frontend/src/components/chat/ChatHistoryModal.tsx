import { useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import Modal from 'react-modal'
import { parseTime } from '@/utils/parseTime'

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
    useEffect(() => {
        if (typeof document !== 'undefined') {
            Modal.setAppElement('#root')
        }
    }, [])

    return (
        <Modal
            isOpen={open}
            onRequestClose={onClose}
            shouldCloseOnEsc
            shouldCloseOnOverlayClick
            contentLabel="Lịch sử chat"
            className="relative z-10 w-full max-w-2xl overflow-hidden rounded-[28px] border border-theme-border bg-theme-surface shadow-md outline-none"
            overlayClassName="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm"
        >
            <div>
                <div className="flex items-start justify-between border-b border-theme-border/20 px-5 py-4">
                    <div>
                        <p className="text-[10px] uppercase tracking-[0.24em] text-theme-text-secondary">Lịch sử chat</p>
                        <p className="mt-1 text-sm font-semibold text-theme-text-primary">Các phiên trò chuyện gần đây</p>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded-full p-2 text-theme-text-secondary transition hover:bg-theme-bg-secondary hover:text-theme-text-primary"
                        aria-label="Đóng lịch sử chat"
                    >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                            <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="max-h-[70vh] overflow-y-auto px-5 py-4">
                    {loading ? (
                        <div className="flex min-h-48 flex-col items-center justify-center gap-3 text-theme-text-secondary">
                            <Loader2 className="h-6 w-6 animate-spin text-theme-accent" />
                            <p className="text-sm">Đang tải lịch sử chat...</p>
                        </div>
                    ) : sessions.length === 0 ? (
                        <p className="py-8 text-center text-sm text-theme-text-secondary/70">Chưa có phiên nào.</p>
                    ) : (
                        <div className="space-y-2.5">
                            {sessions.map((sess) => (
                                <button
                                    key={sess.session_id}
                                    type="button"
                                    onClick={() => onSelectSession(sess.session_id)}
                                    className="w-full rounded-2xl border border-theme-border bg-theme-surface/50 px-4 py-3 text-left transition hover:bg-theme-accent/20 hover:border-theme-border/35"
                                >
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="min-w-0 flex-1">
                                            <p className="truncate text-sm font-semibold text-theme-text-primary">
                                                {sess.preview || 'Phiên trò chuyện'}
                                            </p>
                                            <p className="mt-1 text-[11px] leading-relaxed text-theme-text-secondary">
                                                {parseTime(sess.last_message_at)}
                                            </p>
                                        </div>
                                        <span className="mt-0.5 rounded-full bg-theme-accent/10 px-2 py-1 text-[10px] font-medium text-theme-accent">
                                            Mở
                                        </span>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </Modal>
    )
}