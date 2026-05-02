import { useState } from 'react'
import { toast } from 'react-toastify'
import { ApiRequestError } from '../../../api/types'
import { anonymousShareService, type ReportCategory } from '../../../services/anonymousShareService'
import { getUi, REPORT_CATEGORY_OPTIONS } from './shared'
import { useThemeContext } from '../../../contexts/ThemeContext'

type ReportTarget = {
    id: string
}

export function ReportLetterModal({
    item,
    dark,
    onClose,
    onSuccess,
}: {
    item: ReportTarget
    dark?: boolean
    onClose: () => void
    onSuccess: () => void
}) {
    const { effectiveTheme } = useThemeContext()
    const isDark = typeof dark === 'boolean' ? dark : effectiveTheme === 'dark'
    const ui = getUi(isDark)
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
                                    borderColor: category === option.value ? (isDark ? 'rgba(95,208,190,0.7)' : 'rgba(79,157,203,0.7)') : isDark ? 'rgba(242,235,224,0.16)' : 'rgba(18,30,40,0.16)',
                                    backgroundColor: category === option.value ? (isDark ? 'rgba(95,208,190,0.08)' : 'rgba(79,157,203,0.08)') : 'transparent',
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
                                backgroundColor: isDark ? 'rgba(242,235,224,0.05)' : 'rgb(255,255,255)',
                                borderColor: isDark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)',
                                color: isDark ? 'rgb(255,255,255)' : 'rgb(15,23,42)',
                                border: `1px solid ${isDark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)'}`,
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
                            backgroundColor: isDark ? 'rgba(242,235,224,0.05)' : 'rgb(255,255,255)',
                            borderColor: isDark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)',
                            color: isDark ? 'rgb(255,255,255)' : 'rgb(15,23,42)',
                            border: `1px solid ${isDark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)'}`,
                        }}
                    />

                    <div className="flex items-center justify-between gap-3 pt-2">
                        <p className={`${ui.textSubtler} text-xs`}>{isOther ? 'Lý do khác cần ít nhất 10 ký tự.' : 'Bạn có thể thêm mô tả tùy chọn.'}</p>
                        <div className="flex gap-3">
                            <button
                                type="button"
                                onClick={onClose}
                                className="px-4 py-2 rounded-xl border text-sm font-semibold"
                                style={{ borderColor: isDark ? 'rgba(242,235,224,0.16)' : 'rgba(18,30,40,0.16)', color: isDark ? 'rgba(242,235,224,0.8)' : 'rgba(20,26,33,0.8)' }}
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
                                    border: `1px solid ${canSubmit ? 'rgba(111,190,214,0.68)' : isDark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)'}`,
                                    color: canSubmit ? '#ffffff' : isDark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.45)',
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
