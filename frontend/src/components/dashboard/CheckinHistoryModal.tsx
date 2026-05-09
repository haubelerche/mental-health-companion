import { useEffect, useMemo, useState } from 'react'
import { X } from 'lucide-react'
import Modal from 'react-modal'
import type { CheckinHistoryDay, CheckinHistoryItem } from '../../services/dashboardService'
import { dashboardService } from '../../services/dashboardService'
import Loading from '../ui/Loading'

type Props = {
    open: boolean
    onClose: () => void
    isDark?: boolean
}

const BUCKET_VI: Record<CheckinHistoryItem['time_bucket'], string> = {
    morning: 'Sáng',
    afternoon: 'Chiều',
    evening: 'Tối',
    other: 'Khác',
}

export function CheckinHistoryModal({ open, onClose, isDark = false }: Props) {
    const [loading, setLoading] = useState(false)
    const [history, setHistory] = useState<CheckinHistoryDay[]>([])
    const [err, setErr] = useState<string | null>(null)
    const [loaded, setLoaded] = useState(false)

    useEffect(() => {
        if (typeof document !== 'undefined') {
            Modal.setAppElement('#root')
        }
    }, [])

    useEffect(() => {
        if (!open || loaded) return
        let cancelled = false
        ;(async () => {
            setLoading(true)
            setErr(null)
            try {
                const data = await dashboardService.getCheckinHistory('90d')
                if (!cancelled) {
                    setHistory(data.history || [])
                    setLoaded(true)
                }
            } catch {
                if (!cancelled) setErr('Không tải được lịch sử check-in.')
            } finally {
                if (!cancelled) setLoading(false)
            }
        })()
        return () => {
            cancelled = true
        }
    }, [loaded, open])

    const completedSet = useMemo(() => {
        const s = new Set<string>()
        for (const d of history) {
            if (d.completed) s.add(d.date.slice(0, 10))
        }
        return s
    }, [history])

    return (
        <Modal
            isOpen={open}
            onRequestClose={onClose}
            shouldCloseOnEsc
            shouldCloseOnOverlayClick
            contentLabel="Lịch sử check-in"
            className="relative z-[81] mb-5 flex max-h-[80dvh] w-full max-w-lg flex-col overflow-hidden rounded-3xl border shadow-2xl border-theme-border bg-theme-surface outline-none"
            overlayClassName="fixed inset-0 z-[80] flex items-end justify-center sm:items-center bg-black/45 backdrop-blur-[2px]"
        >
            <div className="flex items-center justify-between border-b px-5 py-4 border-theme-secondary/40">
                <div>
                    <p className="mb-3 text-sm font-semibold uppercase tracking-[0.22em] text-theme-text-secondary">
                        Lịch sử check-in
                    </p>
                    <h2 className={`font-display text-sm ${isDark ? 'text-theme-text-primary' : 'text-serene-ink'}`}>90 ngày gần đây</h2>
                </div>
                <button
                    type="button"
                    onClick={onClose}
                    className="cursor-pointer rounded-full p-2 hover:text-red-400"
                >
                    <X className="h-5 w-5" />
                </button>
            </div>

            <div className="overflow-y-auto px-5 pb-8 pt-4">
                {loading && <Loading />}
                {err && <p className="text-sm text-red-600">{err}</p>}

                {!loading && !err && (
                    <>
                        <MiniCompletionCalendar completedDates={completedSet} />

                        <div className="mt-6 space-y-6">
                            {history.length === 0 && (
                                <p className={`text-sm ${isDark ? 'text-theme-text-secondary' : 'text-serene-muted'}`}>
                                    Chưa có check-in trong khung thời gian này.
                                </p>
                            )}
                            {history.map((day) => (
                                <div key={day.date}>
                                    <div className="mb-2 flex items-center justify-between gap-2">
                                        <p className={`font-semibold ${isDark ? 'text-theme-text-primary' : 'text-serene-ink'}`}>
                                            {new Date(day.date).toLocaleDateString('vi-VN')}
                                        </p>
                                        {day.completed && (
                                            <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-semibold text-primary dark:bg-theme-accent/15 dark:text-theme-accent">
                                                Đã check-in
                                            </span>
                                        )}
                                    </div>
                                    <div className="space-y-3">
                                        {day.checkins.map((c) => (
                                            <CheckinCard key={c.checkin_id} c={c} isDark={isDark} />
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </>
                )}
            </div>
        </Modal>
    )
}

function CheckinCard({ c, isDark }: { c: CheckinHistoryItem; isDark: boolean }) {
    const time = (() => {
        try {
            const d = new Date(c.logged_at)
            return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
        } catch {
            return ''
        }
    })()

    return (
        <div className="rounded-2xl border border-theme-primary/30 bg-theme-surface p-3 text-sm">
            <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="rounded-full bg-primary/15 px-2 py-0.5 font-semibold text-primary dark:bg-theme-accent/15 dark:text-theme-accent">
                    {BUCKET_VI[c.time_bucket]}
                </span>
                {time && <span className="text-theme-text-secondary">{time}</span>}
                {c.mood_label && (
                    <span className="font-semibold text-theme-text-primary">
                        {c.mood_label}
                        {c.mood_score != null ? ` (${c.mood_score}/5)` : ''}
                    </span>
                )}
            </div>
            {c.emotions.length > 0 && (
                <p className={`mt-2 text-xs ${isDark ? 'text-theme-text-secondary' : 'text-serene-muted'}`}>
                    Cảm xúc: {c.emotions.join(', ')}
                </p>
            )}
            {c.triggers.length > 0 && (
                <p className={`mt-1 text-xs ${isDark ? 'text-theme-text-secondary' : 'text-serene-muted'}`}>
                    Yếu tố: {c.triggers.join(', ')}
                </p>
            )}
            {c.note && (
                <p className={`mt-2 text-xs leading-relaxed ${isDark ? 'text-theme-text-primary/90' : 'text-serene-ink/90'}`}>{c.note}</p>
            )}
            {c.reward_granted != null && (
                <p className="mt-2 text-[10px] uppercase tracking-wide text-theme-text-secondary">
                    Tim thưởng: {c.reward_granted ? 'đã nhận (theo ngày)' : 'không áp dụng'}
                </p>
            )}
        </div>
    )
}

const DAY_LABELS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']

function MiniCompletionCalendar({
    completedDates,
}: {
    completedDates: Set<string>
}) {
    const today = new Date()
    const dayOfWeek = today.getDay()
    const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1
    const startDate = new Date(today)
    startDate.setDate(today.getDate() - daysToMonday - 21)

    const weeks: string[][] = []
    for (let week = 0; week < 4; week++) {
        const row: string[] = []
        for (let day = 0; day < 7; day++) {
            const d = new Date(startDate)
            d.setDate(startDate.getDate() + week * 7 + day)
            row.push(d.toISOString().slice(0, 10))
        }
        weeks.push(row)
    }

    return (
        <div>
            <p className="mb-2 text-[11px] font-medium text-theme-primary">
                Các ngày có check-in (màu thương hiệu)
            </p>
            <div className="mb-1 grid grid-cols-7 gap-1">
                {DAY_LABELS.map((d) => (
                    <div key={d} className="text-center text-[9px] font-semibold uppercase text-theme-secondary">
                        {d}
                    </div>
                ))}
            </div>
            <div className="space-y-1">
                {weeks.map((week, wi) => (
                    <div key={wi} className="grid grid-cols-7 gap-1">
                        {week.map((iso) => {
                            const done = completedDates.has(iso)
                            const isFuture = iso > today.toISOString().slice(0, 10)
                            return (
                                <div
                                    key={iso}
                                    className={[
                                        'flex aspect-square items-center justify-center rounded-lg border text-[9px]',
                                        done
                                            ? 'border-primary bg-primary text-white dark:border-theme-accent dark:bg-theme-accent'
                                            : isFuture
                                              ? 'border-transparent bg-transparent'
                                              : 'border-theme-primary/30 bg-theme-surface',
                                    ].join(' ')}
                                    title={iso}
                                >
                                    {done ? '✓' : ''}
                                </div>
                            )
                        })}
                    </div>
                ))}
            </div>
        </div>
    )
}
