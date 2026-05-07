import { useEffect, useRef, useState } from 'react'
import type { MouseEvent as ReactMouseEvent } from 'react'
import { ApiRequestError } from '../../../api/types'
import { anonymousShareService, type ReplyArchiveItem, type SentLetterItem } from '../../../services/anonymousShareService'
import { formatRelativeTime, getUi, type Letter } from './shared'
import { ReportLetterModal } from './ReportLetterModal.tsx'
import { AlertTriangle, CornerDownRight, Heart, RotateCcw, Send, Shell, Sparkles, X } from 'lucide-react'

export function LetterOverlay({
    letter,
    onClose,
    dark,
    onReply,
    onPass,
    onReportSuccess,
}: {
    letter: Letter
    onClose: () => void
    dark?: boolean
    onReply: (content: string) => Promise<void>
    onPass: () => Promise<void>
    onReportSuccess: () => void
}) {
    const isDark = Boolean(dark)
    const ui = getUi(isDark)
    const [replyOpen, setReplyOpen] = useState(false)
    const [reply, setReply] = useState('')
    const [sent, setSent] = useState(false)
    const [busy, setBusy] = useState(false)
    const [busyAction, setBusyAction] = useState<'pass' | 'reply' | null>(null)
    const [actionError, setActionError] = useState<string | null>(null)
    const [showReport, setShowReport] = useState(false)
    const areaRef = useRef<HTMLTextAreaElement | null>(null)
    const canReport = letter.direction === 'received'

    useEffect(() => {
        if (replyOpen) areaRef.current?.focus()
    }, [replyOpen])

    return (
        <div
            onClick={(e: ReactMouseEvent<HTMLDivElement>) => e.target === e.currentTarget && onClose()}
            className={`fixed inset-0 z-50 flex items-center justify-center p-6 ${ui.overlay} backdrop-blur-md`}
            style={{ animation: 'fadeIn 0.45s ease' }}
        >
            <div className={`${ui.glassLight} w-full max-w-xl rounded-[32px] overflow-hidden shadow-2xl`} style={{ animation: 'letterOpen 0.65s cubic-bezier(0.22,1,0.36,1) both' }}>
                <div className={`border-b ${ui.glassBorder} px-8 py-8 flex justify-between items-start bg-theme-surface/30`}>
                    <div>
                        <p className={`${ui.textSubtler} font-bold text-[10px] uppercase tracking-[0.3em] mb-2`}>Lá thư từ biển khơi</p>
                        <p className={`${ui.textPrimary} font-display text-2xl font-bold italic`}>{letter.from}</p>
                    </div>
                    <div className="flex items-center gap-5">
                        <span className={`${ui.textSubtler} italic text-xs font-medium`}>{letter.time}</span>
                        <button type="button" onClick={onClose} className="text-theme-text-secondary hover:text-theme-text-primary transition-colors">
                            <X size={24} />
                        </button>
                    </div>
                </div>

                <div className="px-10 py-12 bg-theme-surface/5">
                    <p className={`${ui.textPrimary} font-display text-2xl italic font-medium leading-relaxed tracking-[.5px] whitespace-pre-wrap`}>
                        "{letter.body}"
                    </p>
                </div>

                <div className={`px-8 py-8 border-t ${ui.glassBorder} bg-theme-surface/30`}>
                    {!sent ? (
                        !replyOpen ? (
                            <div className="flex flex-wrap gap-3">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setActionError(null)
                                        setReplyOpen(true)
                                    }}
                                    disabled={busy}
                                    className="flex-1 min-w-[140px] flex items-center justify-center gap-2 bg-theme-accent text-white rounded-2xl py-3.5 px-4 font-bold text-sm tracking-widest uppercase transition-all hover:brightness-105 active:scale-95 shadow-lg shadow-theme-accent/20"
                                >
                                    <CornerDownRight size={16} />
                                    Hồi âm
                                </button>
                                <button
                                    type="button"
                                    onClick={async () => {
                                        if (busy) return
                                        setBusy(true)
                                        setBusyAction('pass')
                                        setActionError(null)
                                        try {
                                            await onPass()
                                            onClose()
                                        } catch (error) {
                                            if (error instanceof ApiRequestError) setActionError(error.message)
                                            else setActionError('Không thể đẩy thư lúc này. Vui lòng thử lại.')
                                        } finally {
                                            setBusy(false)
                                            setBusyAction(null)
                                        }
                                    }}
                                    disabled={busy}
                                    className="flex-1 min-w-[140px] flex items-center justify-center gap-2 text-theme-text-secondary rounded-2xl py-3.5 px-4 font-bold text-sm tracking-widest uppercase transition-all hover:bg-theme-surface active:scale-95 bg-theme-surface/50"
                                >
                                    <RotateCcw size={16} className={busyAction === 'pass' ? 'animate-spin' : ''} />
                                    {busy && busyAction === 'pass' ? 'Đang đẩy...' : 'Để thư trôi'}
                                </button>
                                {canReport && (
                                    <button
                                        type="button"
                                        onClick={() => setShowReport(true)}
                                        disabled={busy}
                                        className="flex items-center justify-center gap-2 text-red-500/80 rounded-2xl py-3.5 px-6 font-bold text-sm tracking-widest uppercase transition-all hover:bg-red-500/5 active:scale-95 bg-red-500/10"
                                    >
                                        <AlertTriangle size={16} />
                                    </button>
                                )}
                            </div>
                        ) : (
                            <div className="space-y-4" style={{ animation: 'fadeUpCard 0.35s ease' }}>
                                <textarea
                                    ref={areaRef}
                                    value={reply}
                                    onChange={(e) => setReply(e.target.value)}
                                    placeholder="Viết hồi âm chân thành của bạn..."
                                    rows={4}
                                    className="w-full rounded-2xl p-5 font-display text-xl italic font-medium leading-relaxed resize-none outline-none transition-all bg-theme-surface/50 text-theme-text-primary focus:ring-1 focus:ring-theme-accent/30"
                                />
                                <div className="flex justify-between items-center px-2">
                                    <button
                                        type="button"
                                        onClick={() => setReplyOpen(false)}
                                        disabled={busy}
                                        className="text-[10px] font-bold uppercase tracking-widest text-theme-text-secondary/50 hover:text-theme-text-primary transition-colors"
                                    >
                                        Huỷ bỏ
                                    </button>
                                    <button
                                        type="button"
                                        onClick={async () => {
                                            if (!reply.trim() || busy) return
                                            setBusy(true)
                                            setBusyAction('reply')
                                            setActionError(null)
                                            try {
                                                await onReply(reply.trim())
                                                setSent(true)
                                                setTimeout(onClose, 1200)
                                            } catch (error) {
                                                if (error instanceof ApiRequestError) setActionError(error.message)
                                                else setActionError('Không thể gửi hồi âm lúc này. Vui lòng thử lại.')
                                            } finally {
                                                setBusy(false)
                                                setBusyAction(null)
                                            }
                                        }}
                                        disabled={!reply.trim() || busy}
                                        className={`flex items-center gap-2 px-8 py-3 rounded-2xl font-bold text-sm uppercase tracking-widest transition-all shadow-lg ${reply.trim() ? 'bg-theme-accent text-white shadow-theme-accent/25 hover:brightness-105' : 'bg-theme-border/20 text-theme-text-secondary/30 cursor-not-allowed'}`}
                                    >
                                        <Send size={16} />
                                        {busy && busyAction === 'reply' ? 'Đang thả...' : 'Thả về biển'}
                                    </button>
                                </div>
                                {actionError && <p className="mt-2 text-xs font-bold text-rose-500 text-center uppercase tracking-wider">{actionError}</p>}
                            </div>
                        )
                    ) : (
                        <div className="text-center py-6" style={{ animation: 'fadeUpCard 0.5s ease' }}>
                            <p className={`${ui.textSubtle} font-display text-xl italic font-bold`}>Hồi âm đã hòa cùng tiếng sóng khơi xa...</p>
                        </div>
                    )}
                </div>
            </div>
            {showReport && canReport && (
                <ReportLetterModal
                    item={{ id: letter.id }}
                    dark={isDark}
                    onClose={() => setShowReport(false)}
                    onSuccess={onReportSuccess}
                />
            )}
        </div>
    )
}

export function WriteOverlay({ onClose, dark }: { onClose: () => void; dark?: boolean }) {
    const isDark = Boolean(dark)
    const ui = getUi(isDark)
    const [text, setText] = useState('')
    const [sent, setSent] = useState(false)
    const [busy, setBusy] = useState(false)
    const [submitError, setSubmitError] = useState<string | null>(null)

    return (
        <div
            onClick={(e: ReactMouseEvent<HTMLDivElement>) => e.target === e.currentTarget && onClose()}
            className={`fixed inset-0 z-50 flex items-center justify-center p-6 ${ui.overlay} backdrop-blur-md`}
            style={{ animation: 'fadeIn 0.45s ease' }}
        >
            <div className={`${ui.glassLight} w-full max-w-xl rounded-[32px] overflow-hidden shadow-2xl bg-theme-surface`} style={{ animation: 'letterOpen 0.65s cubic-bezier(0.22,1,0.36,1) both' }}>
                <div className={`border-b ${ui.glassBorder} px-8 py-8 flex justify-between items-start bg-theme-surface/30`}>
                    <div>
                        <p className={`${ui.textSubtler} text-[10px] font-bold uppercase tracking-[0.3em] mb-2`}>Viết tâm tư gửi biển</p>
                        <p className={`${ui.textPrimary} font-display text-xl italic font-bold`}>Lá thư sẽ tìm đến một tâm hồn đồng điệu</p>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="text-theme-text-secondary hover:text-theme-text-primary transition-colors p-1"
                    >
                        <X size={24} />
                    </button>
                </div>

                <div className="px-8 py-10 ">
                    {!sent ? (
                        <div className="space-y-6">
                            <textarea
                                value={text}
                                onChange={(e) => setText(e.target.value)}
                                placeholder="Hãy trút bỏ nỗi lòng hoặc sẻ chia niềm hạnh phúc của bạn hôm nay..."
                                rows={6}
                                autoFocus
                                className="w-full rounded-[24px] p-6 font-display text-xl italic font-medium leading-relaxed resize-none outline-none transition-all bg-theme-border/5 text-theme-text-primary focus:ring-1 focus:ring-theme-accent/30"
                            />
                            <div className="flex justify-end">
                                <button
                                    type="button"
                                    onClick={async () => {
                                        if (!text.trim() || busy) return
                                        setBusy(true)
                                        setSubmitError(null)
                                        try {
                                            await anonymousShareService.send({ content: text.trim() })
                                            setSent(true)
                                            setTimeout(onClose, 1800)
                                        } catch (error) {
                                            if (error instanceof ApiRequestError) setSubmitError(error.message)
                                            else setSubmitError('Không thể gửi thư lúc này. Vui lòng thử lại.')
                                        } finally {
                                            setBusy(false)
                                        }
                                    }}
                                    disabled={!text.trim() || busy}
                                    className={`flex items-center gap-3 px-10 py-4 rounded-2xl font-bold text-sm uppercase tracking-widest transition-all shadow-xl ${text.trim() ? 'bg-theme-accent text-white shadow-theme-accent/25 hover:brightness-105 active:scale-95' : 'bg-theme-border/20 text-theme-text-secondary/30'}`}
                                >
                                    <Send size={18} />
                                    {busy ? 'Đang thả...' : 'Gửi ra khơi'}
                                </button>
                            </div>
                            {submitError && <p className="mt-2 text-xs font-bold text-rose-500 text-center uppercase tracking-wider">{submitError}</p>}
                        </div>
                    ) : (
                        <div className="text-center py-12" style={{ animation: 'fadeUpCard 0.6s ease' }}>
                            <div className="mb-4 flex justify-center text-theme-accent">
                                <Sparkles className="h-12 w-12" aria-hidden />
                            </div>
                            <p className={`${ui.textPrimary} font-display text-2xl italic font-bold leading-relaxed`}>Lá thư đã trôi theo con sóng...</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export function SentLetterDialog({
    item,
    dark,
    onClose,
    onReact: parentOnReact,
}: {
    item: SentLetterItem
    dark?: boolean
    onClose: () => void
    onReact: () => Promise<void>
}) {
    const isDark = Boolean(dark)
    const ui = getUi(isDark)
    const [busyReact, setBusyReact] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [reacted, setReacted] = useState(Boolean(item.reply?.reaction_type))

    const handleReact = async () => {
        if (!item.reply || reacted || busyReact) return
        setBusyReact(true)
        setError(null)
        try {
            await parentOnReact()
            setReacted(true)
        } catch (e) {
            if (e instanceof ApiRequestError) setError(e.message)
            else setError('Không thể gửi cảm ơn lúc này.')
        } finally {
            setBusyReact(false)
        }
    }

    return (
        <div
            onClick={(e) => e.target === e.currentTarget && onClose()}
            className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-theme-surface/40 backdrop-blur-md transition-all"
        >
            <div className={`${ui.glassLight} bg-theme-surface rounded-[32px] shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col`} style={{ animation: 'letterOpen 0.35s cubic-bezier(0.22,1,0.36,1) both' }}>
                <div className={`border-b ${ui.glassBorder} px-8 py-5 flex items-center justify-between`}>
                    <div className="flex flex-col">
                        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-theme-text-secondary/60">Hành trình lá thư</p>
                        <h2 className="text-xl font-bold text-theme-text-primary">Chi tiết tâm tình</h2>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="h-10 w-10 rounded-full flex items-center justify-center text-theme-text-secondary hover:bg-theme-surface/50 hover:text-theme-text-primary transition-all"
                    >
                        <X size={20} />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-8 space-y-6 custom-scrollbar">
                    <div className="space-y-3">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-theme-accent/70 px-2">Nội dung bạn gửi</p>
                        <div className={`rounded-3xl p-6 ${isDark ? 'bg-white/10' : 'bg-black/10'}`}>
                            <p className="text-theme-text-primary font-display text-xl italic leading-relaxed whitespace-pre-wrap">"{item.content}"</p>
                            <p className="text-theme-text-secondary/40 text-[10px] font-bold mt-4 uppercase tracking-tighter">{formatRelativeTime(item.sent_at)}</p>
                        </div>
                    </div>

                    <div className="space-y-3">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-500/70 px-2">Phản hồi từ phương xa</p>
                        <div className={`rounded-3xl p-6 ${isDark ? 'bg-white/10' : 'bg-black/10'}`}>
                            {item.reply ? (
                                <>
                                    <div className="flex items-center gap-2 mb-4 border-b border-theme-border/5 pb-3">
                                        <Shell className="h-5 w-5 shrink-0 text-emerald-600/80" aria-hidden />
                                        <p className="text-theme-text-primary text-[11px] font-bold uppercase tracking-widest">
                                            {item.reply.anonymous_name ? item.reply.anonymous_name : 'Người lạ ẩn danh'}
                                        </p>
                                    </div>
                                    <p className="text-theme-text-primary font-display text-xl italic leading-relaxed whitespace-pre-wrap">"{item.reply.content}"</p>
                                    <p className="text-theme-text-secondary/40 text-[10px] font-bold mt-4 uppercase tracking-tighter">{formatRelativeTime(item.reply.received_at)}</p>
                                    <div className="mt-6 flex justify-end">
                                        <button
                                            type="button"
                                            disabled={reacted || busyReact}
                                            onClick={handleReact}
                                            className={`flex items-center gap-2 px-6 py-2.5 rounded-2xl font-bold text-xs uppercase tracking-widest transition-all ${reacted ? 'bg-rose-400 text-white shadow-lg shadow-rose-400/20' : 'bg-theme-surface/50 text-theme-text-secondary hover:bg-theme-surface active:scale-95'}`}
                                        >
                                            <Heart size={14} fill={reacted ? "white" : "none"} className={reacted ? "text-white" : ""} />
                                            {reacted ? 'Đã cảm ơn' : busyReact ? 'Đang gửi...' : 'Gửi lời cảm ơn'}
                                        </button>
                                    </div>
                                </>
                            ) : (
                                <div className="py-10 text-center">
                                    <p className="text-theme-text-secondary/40 text-sm italic font-medium">Lá thư vẫn đang trôi dạt, chưa có ai nhặt được...</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {error && <p className="text-xs font-bold text-rose-500 uppercase text-center">{error}</p>}
                </div>
            </div>
        </div>
    )
}

export function ReceivedLetterDialog({
    item,
    dark,
    onClose,
}: {
    item: ReplyArchiveItem
    dark?: boolean
    onClose: () => void
}) {
    const isDark = Boolean(dark)
    const ui = getUi(isDark)

    return (
        <div
            className={`fixed inset-0 z-50 flex items-center justify-center p-6 ${ui.overlay} backdrop-blur-md`}
            style={{ animation: 'fadeIn 0.45s ease' }}
            onClick={(e: ReactMouseEvent<HTMLDivElement>) => e.target === e.currentTarget && onClose()}
        >
            <div className={`${ui.glassLight} rounded-[32px] shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col`} style={{ animation: 'letterOpen 0.35s cubic-bezier(0.22,1,0.36,1) both' }}>
                <div className={`border-b ${ui.glassBorder} px-8 py-5 flex items-center justify-between bg-theme-surface/30`}>
                    <div className="flex flex-col">
                        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-theme-text-secondary/60">Lưu trữ phản hồi</p>
                        <h2 className="text-xl font-bold text-theme-text-primary">Chi tiết hồi đáp</h2>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="h-10 w-10 rounded-full flex items-center justify-center text-theme-text-secondary hover:bg-theme-surface/50 hover:text-theme-text-primary transition-all"
                    >
                        <X size={20} />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-8 space-y-6 bg-theme-surface/5 custom-scrollbar">
                    <div className="space-y-3">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-theme-accent/70 px-2">Phản hồi của bạn</p>
                        <div className="rounded-3xl p-6 bg-theme-surface/50">
                            <div className="flex items-center gap-2 mb-4 border-b border-theme-border/5 pb-3">
                                <p className="text-theme-text-primary text-[10px] font-bold uppercase tracking-widest">
                                    Dưới danh nghĩa: {item.anonymous_name ? item.anonymous_name : 'Ẩn danh'}
                                </p>
                            </div>
                            <p className="text-theme-text-primary font-display text-xl italic leading-relaxed whitespace-pre-wrap">"{item.content}"</p>
                            <div className="mt-4 flex items-center justify-between">
                                <p className="text-theme-text-secondary/40 text-[10px] font-bold uppercase tracking-tighter">{formatRelativeTime(item.sent_at)}</p>
                                {item.has_reaction && (
                                    <div className="flex items-center gap-1.5 bg-rose-500/10 px-3 py-1 rounded-full border border-rose-500/20">
                                        <Heart size={10} fill="#f43f5e" className="text-rose-500" />
                                        <span className="text-[10px] font-bold text-rose-500 uppercase tracking-tighter">Đã nhận</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="space-y-3">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-theme-text-secondary/50 px-2">Thư gốc từ người lạ</p>
                        <div className="rounded-3xl p-6 bg-theme-surface/20">
                            {item.original_content ? (
                                <p className="text-theme-text-secondary/70 font-display text-lg italic leading-relaxed whitespace-pre-wrap">"{item.original_content}"</p>
                            ) : (
                                <p className="text-theme-text-secondary/30 text-sm italic">Nội dung thư gốc đã bị con sóng cuốn trôi...</p>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}