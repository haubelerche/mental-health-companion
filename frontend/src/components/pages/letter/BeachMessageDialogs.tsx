import { useEffect, useRef, useState } from 'react'
import type { MouseEvent as ReactMouseEvent } from 'react'
import { toast } from 'react-toastify'
import { ApiRequestError } from '../../../api/types'
import { anonymousShareService, type ReportCategory, type SentLetterItem } from '../../../services/anonymousShareService'
import { formatRelativeTime, getUi, REPORT_CATEGORY_OPTIONS, type Letter } from './shared'

export function LetterOverlay({
    letter,
    onClose,
    dark,
    onReply,
    onPass,
}: {
    letter: Letter
    onClose: () => void
    dark: boolean
    onReply: (content: string) => Promise<void>
    onPass: () => Promise<void>
}) {
    const ui = getUi(dark)
    const [replyOpen, setReplyOpen] = useState(false)
    const [reply, setReply] = useState('')
    const [sent, setSent] = useState(false)
    const [busy, setBusy] = useState(false)
    const [busyAction, setBusyAction] = useState<'pass' | 'reply' | null>(null)
    const [actionError, setActionError] = useState<string | null>(null)
    const areaRef = useRef<HTMLTextAreaElement | null>(null)

    useEffect(() => {
        if (replyOpen) areaRef.current?.focus()
    }, [replyOpen])

    return (
        <div
            onClick={(e: ReactMouseEvent<HTMLDivElement>) => e.target === e.currentTarget && onClose()}
            className={`fixed inset-0 z-50 flex items-center justify-center p-4 ${ui.overlay} backdrop-blur-2xl`}
            style={{ animation: 'fadeIn 0.45s ease' }}
        >
            <div className={`${ui.glassLight} border w-full max-w-xl rounded-2xl backdrop-blur-2xl`} style={{ animation: 'letterOpen 0.65s cubic-bezier(0.22,1,0.36,1) both' }}>
                <div className={`border-b ${ui.glassBorder} px-8 py-7 flex justify-between items-start`}>
                    <div>
                        <p className={`${ui.textSubtler} font-display text-xs font-bold uppercase tracking-wide mb-2`}>Lá thư từ biển khơi</p>
                        <p className={`${ui.textPrimary} font-display text-lg font-semibold`}>{letter.from}</p>
                    </div>
                    <div className="flex items-center gap-4">
                        <span className={`${ui.textSubtler} italic text-xs`}>{letter.time}</span>
                        <button type="button" onClick={onClose} className={`${ui.textSubtle} bg-none border-none cursor-pointer p-1 flex hover:opacity-70 transition-opacity`}>
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <path d="M18 6L6 18M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>

                <div className="px-8 py-7">
                    <p className={`${ui.textPrimary} font-display text-lg italic leading-relaxed tracking-[.5px]`}>{letter.body}</p>
                </div>

                <div className={`px-8 py-7 border-t ${ui.glassBorder}`}>
                    {!sent ? (
                        !replyOpen ? (
                            <div className="mt-5 flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setActionError(null)
                                        setReplyOpen(true)
                                    }}
                                    disabled={busy}
                                    className="flex-1 bg-none border rounded-xl py-2.5 px-0 font-display tracking-wide cursor-pointer transition-all"
                                    style={{
                                        borderColor: dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)',
                                        color: dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.7)',
                                    }}
                                >
                                    Trả lời thư
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
                                    className="flex-1 bg-none border rounded-xl py-2.5 px-0 font-display font-semibold tracking-wide cursor-pointer transition-all"
                                    style={{
                                        borderColor: dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)',
                                        color: dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.7)',
                                    }}
                                >
                                    {busy && busyAction === 'pass' ? 'Đang đẩy...' : 'Đẩy thuyền trôi đi'}
                                </button>
                            </div>
                        ) : (
                            <div className="mt-5" style={{ animation: 'fadeUpCard 0.35s ease' }}>
                                <textarea
                                    ref={areaRef}
                                    value={reply}
                                    onChange={(e) => setReply(e.target.value)}
                                    placeholder="Viết hồi âm của bạn..."
                                    rows={3}
                                    className="w-full rounded-xl p-4 font-display text-lg italic font-light leading-relaxed resize-none outline-none transition-colors"
                                    style={{
                                        backgroundColor: dark ? 'rgba(242,235,224,0.05)' : 'rgb(255,255,255)',
                                        borderColor: dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)',
                                        color: dark ? 'rgb(255,255,255)' : 'rgb(15,23,42)',
                                        border: `1px solid ${dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)'}`,
                                    }}
                                />
                                <div className="flex justify-between items-center mt-2.5">
                                    <button type="button" onClick={() => setReplyOpen(false)} disabled={busy} className="text-xs cursor-pointer tracking-wide" style={{ background: 'none', border: 'none', color: dark ? 'rgba(242,235,224,0.55)' : 'rgba(20,26,33,0.56)' }}>
                                        Huỷ
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
                                        className="px-6 py-2 rounded-lg font-display text-sm italic transition-all"
                                        style={{
                                            background: reply.trim() ? 'linear-gradient(135deg,#5fd0be 0%,#4f9dcb 100%)' : 'none',
                                            border: `1px solid ${reply.trim() ? 'rgba(111,190,214,0.68)' : dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)'}`,
                                            color: reply.trim() ? '#ffffff' : dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.45)',
                                        }}
                                    >
                                        {busy && busyAction === 'reply' ? 'Đang gửi...' : 'Thả về biển'}
                                    </button>
                                </div>
                                {actionError && <p className="mt-2 text-xs text-rose-400">{actionError}</p>}
                            </div>
                        )
                    ) : (
                        <div className="mt-5 text-center py-3" style={{ animation: 'fadeUpCard 0.5s ease' }}>
                            <p className={`${ui.textSubtle} font-display text-base italic font-light`}>Hồi âm đã trôi ra biển khơi...</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export function WriteOverlay({ onClose, dark }: { onClose: () => void; dark: boolean }) {
    const ui = getUi(dark)
    const [text, setText] = useState('')
    const [sent, setSent] = useState(false)
    const [busy, setBusy] = useState(false)
    const [submitError, setSubmitError] = useState<string | null>(null)

    return (
        <div
            onClick={(e: ReactMouseEvent<HTMLDivElement>) => e.target === e.currentTarget && onClose()}
            className={`fixed inset-0 z-50 flex items-center justify-center p-4 ${ui.overlay} backdrop-blur-2xl`}
            style={{ animation: 'fadeIn 0.45s ease' }}
        >
            <div className={`${ui.glassLight} border w-full max-w-xl rounded-2xl backdrop-blur-2xl`} style={{ animation: 'letterOpen 0.65s cubic-bezier(0.22,1,0.36,1) both' }}>
                <div className={`border-b ${ui.glassBorder} px-8 py-7 flex justify-between items-start`}>
                    <div>
                        <p className={`${ui.textSubtler} text-lg font-light uppercase tracking-wider mb-2`}>Viết lá thư của bạn</p>
                        <p className={`${ui.textSubtle} font-display text-base italic font-light`}>Lá thư sẽ trôi đến tay một người xa lạ</p>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.45)' }}
                        className="p-1 flex hover:opacity-70 transition-opacity"
                    >
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                            <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="px-8 py-7">
                    {!sent ? (
                        <>
                            <textarea
                                value={text}
                                onChange={(e) => setText(e.target.value)}
                                placeholder="Hôm nay bạn muốn chia sẻ điều gì..."
                                rows={6}
                                autoFocus
                                className="w-full rounded-3xl p-4 font-display text-lg italic font-light leading-relaxed resize-none outline-none transition-colors"
                                style={{
                                    backgroundColor: dark ? 'rgba(242,235,224,0.05)' : 'rgb(255,255,255)',
                                    borderColor: dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)',
                                    color: dark ? 'rgb(255,255,255)' : 'rgb(15,23,42)',
                                    border: `1px solid ${dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)'}`,
                                }}
                            />
                            <div className="flex justify-end mt-3.5">
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
                                    className="px-8 py-2.5 rounded-3xl font-display text-base italic transition-all"
                                    style={{
                                        background: text.trim() ? 'linear-gradient(135deg,#5fd0be 0%,#4f9dcb 100%)' : 'none',
                                        border: `1px solid ${text.trim() ? 'rgba(111,190,214,0.68)' : dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)'}`,
                                        color: text.trim() ? '#ffffff' : dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.45)',
                                    }}
                                >
                                    {busy ? 'Đang thả...' : 'Thả ra biển'}
                                </button>
                            </div>
                            {submitError && <p className="mt-2 text-xs text-rose-400">{submitError}</p>}
                        </>
                    ) : (
                        <div className="text-center py-6" style={{ animation: 'fadeUpCard 0.6s ease' }}>
                            <p className={`${ui.textSubtle} font-display text-lg italic font-light leading-relaxed`}>Lá thư đã trôi ra biển khơi...</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export function ReportLetterModal({
    item,
    dark,
    onClose,
    onSuccess,
}: {
    item: SentLetterItem
    dark: boolean
    onClose: () => void
    onSuccess: () => void
}) {
    const ui = getUi(dark)
    const [category, setCategory] = useState<ReportCategory>('spam')
    const [reason, setReason] = useState('')
    const [description, setDescription] = useState('')
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const isOther = category === 'other'
    const canSubmit = !busy && (!isOther || reason.trim().length >= 10)

    return (
        <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 ${ui.overlay} backdrop-blur-2xl`}>
            <div className={`${ui.glassLight} border w-full max-w-xl rounded-2xl backdrop-blur-2xl`} style={{ animation: 'letterOpen 0.45s cubic-bezier(0.22,1,0.36,1) both' }}>
                <div className={`border-b ${ui.glassBorder} px-8 py-6 flex items-center justify-between gap-3`}>
                    <div>
                        <p className={`${ui.textSubtler} text-xs uppercase tracking-[0.24em] mb-2`}>Báo cáo thư</p>
                        <p className={`${ui.textSubtle} font-display text-lg font-semibold`}>Chọn lý do báo cáo</p>
                    </div>
                    <button type="button" onClick={onClose} className="p-1 flex hover:opacity-70 transition-opacity" aria-label="Đóng báo cáo">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                            <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="px-8 py-6 space-y-4">
                    <p className={`${ui.textSubtler} text-sm leading-relaxed`}>Việc báo cáo giúp chúng tôi xem xét nội dung này. Chọn đúng lý do để hỗ trợ xử lý nhanh hơn.</p>

                    <div className="grid gap-2">
                        {REPORT_CATEGORY_OPTIONS.map((option) => (
                            <button
                                key={option.value}
                                type="button"
                                onClick={() => {
                                    setCategory(option.value)
                                    setError(null)
                                }}
                                className="text-left rounded-2xl border px-4 py-3 transition-all"
                                style={{
                                    borderColor: category === option.value ? (dark ? 'rgba(95,208,190,0.7)' : 'rgba(79,157,203,0.7)') : dark ? 'rgba(242,235,224,0.16)' : 'rgba(18,30,40,0.16)',
                                    backgroundColor: category === option.value ? (dark ? 'rgba(95,208,190,0.08)' : 'rgba(79,157,203,0.08)') : 'transparent',
                                }}
                            >
                                <p className={`${ui.textSubtle} font-display text-sm font-semibold`}>{option.label}</p>
                                <p className={`${ui.textSubtler} text-xs mt-1`}>{option.description}</p>
                            </button>
                        ))}
                    </div>

                    {isOther && (
                        <textarea
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="Hãy mô tả ngắn gọn lý do báo cáo..."
                            rows={4}
                            className="w-full rounded-2xl p-4 font-display text-base italic leading-relaxed resize-none outline-none transition-colors"
                            style={{
                                backgroundColor: dark ? 'rgba(242,235,224,0.05)' : 'rgb(255,255,255)',
                                borderColor: dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)',
                                color: dark ? 'rgb(255,255,255)' : 'rgb(15,23,42)',
                                border: `1px solid ${dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)'}`,
                            }}
                        />
                    )}

                    <textarea
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Ghi chú thêm nếu bạn muốn..."
                        rows={3}
                        className="w-full rounded-2xl p-4 font-display text-sm italic leading-relaxed resize-none outline-none transition-colors"
                        style={{
                            backgroundColor: dark ? 'rgba(242,235,224,0.05)' : 'rgb(255,255,255)',
                            borderColor: dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)',
                            color: dark ? 'rgb(255,255,255)' : 'rgb(15,23,42)',
                            border: `1px solid ${dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)'}`,
                        }}
                    />

                    <div className="flex items-center justify-between gap-3 pt-2">
                        <p className={`${ui.textSubtler} text-xs`}>{isOther ? 'Lý do khác cần ít nhất 10 ký tự.' : 'Bạn có thể thêm mô tả tùy chọn.'}</p>
                        <div className="flex gap-3">
                            <button
                                type="button"
                                onClick={onClose}
                                className="px-4 py-2 rounded-xl border text-sm font-semibold"
                                style={{ borderColor: dark ? 'rgba(242,235,224,0.16)' : 'rgba(18,30,40,0.16)', color: dark ? 'rgba(242,235,224,0.8)' : 'rgba(20,26,33,0.8)' }}
                            >
                                Hủy
                            </button>
                            <button
                                type="button"
                                disabled={!canSubmit}
                                onClick={async () => {
                                    if (!canSubmit) return
                                    setBusy(true)
                                    setError(null)
                                    try {
                                        await anonymousShareService.reportLetter(
                                            item.id,
                                            category,
                                            isOther ? reason.trim() : undefined,
                                            description.trim() || undefined,
                                        )
                                        toast.success('Báo cáo đã được gửi.')
                                        onSuccess()
                                        onClose()
                                    } catch (reportError) {
                                        if (reportError instanceof ApiRequestError) setError(reportError.message)
                                        else setError('Không thể gửi báo cáo lúc này. Vui lòng thử lại.')
                                    } finally {
                                        setBusy(false)
                                    }
                                }}
                                className="px-5 py-2 rounded-xl font-semibold text-sm transition-all"
                                style={{
                                    background: canSubmit ? 'linear-gradient(135deg,#5fd0be 0%,#4f9dcb 100%)' : 'none',
                                    border: `1px solid ${canSubmit ? 'rgba(111,190,214,0.68)' : dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)'}`,
                                    color: canSubmit ? '#ffffff' : dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.45)',
                                }}
                            >
                                {busy ? 'Đang gửi...' : 'Gửi báo cáo'}
                            </button>
                        </div>
                    </div>

                    {error && <p className="text-xs text-rose-400">{error}</p>}
                </div>
            </div>
        </div>
    )
}

export function SentLetterDialog({
    item,
    dark,
    onClose,
    onReact,
    onReportSuccess,
}: {
    item: SentLetterItem
    dark: boolean
    onClose: () => void
    onReact: () => Promise<void>
    onReportSuccess: () => void
}) {
    const ui = getUi(dark)
    const [busyReact, setBusyReact] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [reacted, setReacted] = useState(Boolean(item.reply?.reaction_type))
    const [showReport, setShowReport] = useState(false)

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/55 backdrop-blur-sm">
            <div className={`${ui.glassLight} border rounded-3xl shadow-2xl w-full max-w-3xl max-h-[86vh] overflow-hidden flex flex-col`} style={{ animation: 'letterOpen 0.35s cubic-bezier(0.22,1,0.36,1) both' }}>
                <div className={`border-b ${ui.glassBorder} px-5 py-4 flex items-center justify-between gap-3`}>
                    <button
                        type="button"
                        onClick={onClose}
                        className="inline-flex items-center justify-center h-10 w-10 rounded-xl border"
                        style={{
                            borderColor: dark ? 'rgba(242,235,224,0.12)' : 'rgba(18,30,40,0.12)',
                            color: dark ? 'rgba(242,235,224,0.92)' : 'rgba(20,26,33,0.92)',
                        }}
                        aria-label="Quay lại"
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                            <path d="M15 18l-6-6 6-6" />
                        </svg>
                    </button>

                    <div className="min-w-0 flex-1 text-center px-2">
                        <div className="flex items-center justify-center gap-2">
                            <p className={`${ui.textSubtle} font-display text-lg font-semibold truncate`}>Chi tiết thư</p>
                            {item.is_reported && (
                                <span className="text-xs font-semibold px-2 py-1 rounded-full" style={{ backgroundColor: 'rgba(255, 120, 120, 0.15)', color: 'rgba(255, 150, 150, 0.95)' }}>
                                    Đã báo cáo
                                </span>
                            )}
                        </div>
                    </div>

                    <button
                        type="button"
                        onClick={() => setShowReport(true)}
                        className="inline-flex items-center justify-center h-10 px-3 rounded-xl border text-xs font-semibold"
                        style={{
                            borderColor: dark ? 'rgba(255,120,120,0.35)' : 'rgba(190,40,40,0.35)',
                            color: dark ? 'rgba(255,190,190,0.95)' : 'rgba(145,20,20,0.95)',
                        }}
                    >
                        Report
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-5 space-y-4">
                    <div className={`rounded-2xl border p-4 ${ui.glassLight}`}>
                        <p className={`${ui.textSubtler} text-xs uppercase tracking-wider mb-2`}>Thư bạn gửi</p>
                        <p className={`${ui.textSubtle} font-display text-base leading-relaxed whitespace-pre-wrap`}>{item.content}</p>
                        <p className={`${ui.textSubtler} text-[11px] mt-2`}>{formatRelativeTime(item.sent_at)}</p>
                    </div>

                    <div className={`rounded-2xl border p-4 ${ui.glassLight}`}>
                        <p className={`${ui.textSubtler} text-xs uppercase tracking-wider mb-2`}>Thư bạn nhận được</p>
                        {item.reply ? (
                            <>
                                <p className={`${ui.textSubtler} text-xs mb-2`}>
                                    {item.reply.anonymous_name ? `Ẩn danh: ${item.reply.anonymous_name}` : 'Người phản hồi ẩn danh'}
                                    {item.reply.has_reaction ? ` · Đã được thả ${item.reply.reaction_type ?? 'cảm xúc'}` : ' · Chưa được phản hồi cảm xúc'}
                                </p>
                                <p className={`${ui.textSubtle} font-display text-base leading-relaxed whitespace-pre-wrap`}>{item.reply.content}</p>
                                <p className={`${ui.textSubtler} text-[11px] mt-2`}>{formatRelativeTime(item.reply.received_at)}</p>
                                <div className="mt-3 flex items-center justify-end">
                                    <button
                                        type="button"
                                        disabled={reacted || busyReact}
                                        onClick={async () => {
                                            if (!item.reply || reacted || busyReact) return
                                            setBusyReact(true)
                                            setError(null)
                                            try {
                                                await onReact()
                                                setReacted(true)
                                            } catch (e) {
                                                if (e instanceof ApiRequestError) setError(e.message)
                                                else setError('Không thể thả tim lúc này.')
                                            } finally {
                                                setBusyReact(false)
                                            }
                                        }}
                                        className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border"
                                        style={{
                                            borderColor: reacted ? 'rgba(245,128,160,0.7)' : dark ? 'rgba(242,235,224,0.2)' : 'rgba(18,30,40,0.18)',
                                            color: reacted ? '#f06292' : dark ? 'rgba(242,235,224,0.85)' : 'rgba(20,26,33,0.8)',
                                        }}
                                    >
                                        <span aria-hidden="true">❤</span>
                                        <span className="text-sm">{reacted ? 'Đã thả tim' : busyReact ? 'Đang thả...' : 'Thả tim'}</span>
                                    </button>
                                </div>
                            </>
                        ) : (
                            <p className={`${ui.textSubtler} text-sm`}>Chưa có hồi âm cho thư này.</p>
                        )}
                    </div>

                    {error && <p className="text-sm text-rose-400">{error}</p>}
                </div>
            </div>

            {showReport && <ReportLetterModal item={item} dark={dark} onClose={() => setShowReport(false)} onSuccess={onReportSuccess} />}
        </div>
    )
}
