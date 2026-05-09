import { ArrowRight, ChevronRight, Flame, PenLine, Sparkles, Sprout, Star, Wind } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts'
import { httpClient } from '../../../api/httpClient'
import { useAuth } from '../../../hooks/useAuth'
import { WellnessRadar, type WellnessScores } from '../wellness/WellnessRadar'
import { MoodCalendar, type MoodPoint } from '../wellness/MoodCalendar'
import { useThemeContext } from '../../../contexts/ThemeContext'
import { DayDetailSheet, type DayDetail } from '../wellness/DayDetailSheet'
import { ProgressStats } from '../wellness/ProgressStats'
import { dashboardService, type DashboardReflectSummary } from '../../../services/dashboardService'
import { TinHieuCard } from '../../dashboard/TinHieuCard'
import { WellnessDimensionCards } from '../../dashboard/WellnessDimensionCards'
import { CheckinHistoryModal } from '../../dashboard/CheckinHistoryModal'
import { Skeleton } from './Skeleton'

type WeeklyNotePayload = {
    week_of: string
    content: string
    generated_at: string
    is_cached: boolean
}

type JournalsPayload = {
    journals: Array<{
        journal_id: string
        content_preview: string
        prompt_id: string | null
        created_at: string
    }>
    total: number
    has_more: boolean
}

function dimsToRadarScores(dimensions: DashboardReflectSummary['wellness_dimensions']): WellnessScores {
    const by = Object.fromEntries(dimensions.map((d) => [d.dimension, d.score])) as Record<
        string,
        number | null | undefined
    >
    const pick = (key: string, fallback: number) =>
        typeof by[key] === 'number' ? Math.round(by[key] as number) : fallback
    return {
        emotional: pick('emotion', 50),
        sleep: pick('sleep', 50),
        mindfulness: pick('mindfulness', 50),
        social: pick('connection', 50),
        physical: pick('body', 50),
        growth: pick('growth', 50),
    }
}


const WEEKDAY_LABELS = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7']

function toShortWeekday(isoDate: string): string {
    const parsed = new Date(isoDate)
    if (Number.isNaN(parsed.getTime())) return ''
    return WEEKDAY_LABELS[parsed.getDay()] || ''
}

function formatPercent(value: number | null | undefined): string {
    if (value == null || Number.isNaN(value)) return '--'
    return `${Math.round(value * 100)}%`
}

export default function Reflect() {
    const { user } = useAuth()
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'
    const navigate = useNavigate()

    const [reflectSummary, setReflectSummary] = useState<DashboardReflectSummary | null>(null)
    const [weeklyNote, setWeeklyNote] = useState<WeeklyNotePayload | null>(null)
    const [recentJournal, setRecentJournal] = useState<JournalsPayload['journals'][number] | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [prompts, setPrompts] = useState<Array<{ id: string; text: string }>>([])
    const [selectedDay, setSelectedDay] = useState<DayDetail | null>(null)
    const [historyOpen, setHistoryOpen] = useState(false)

    useEffect(() => {
        if (!user) {
            setLoading(false)
            return
        }

        let mounted = true
        const loadReflectData = async () => {
            setLoading(true)
            setError(null)
            try {
                const [dashSummary, weeklyNoteData, journalsData] = await Promise.all([
                    dashboardService.getReflectSummary(),
                    httpClient.get<WeeklyNotePayload>('/reflect/weekly-note'),
                    httpClient.get<JournalsPayload>('/reflect/journals?limit=1&offset=0'),
                ])
                if (!mounted) return
                setReflectSummary(dashSummary)
                setWeeklyNote(weeklyNoteData)
                setRecentJournal(journalsData.journals[0] || null)
                httpClient.get<{ prompts: Array<{ id: string; text: string }> }>('/reflect/journal-prompts')
                    .then(d => {
                        if (mounted) setPrompts(d.prompts)
                    })
                    .catch(() => {
                        if (import.meta.env.DEV) console.warn('[Reflect] journal prompts fetch failed')
                    })
            } catch {
                if (!mounted) return
                setError('Không tải được dữ liệu. Vui lòng thử lại sau.')
            } finally {
                if (mounted) setLoading(false)
            }
        }
        loadReflectData()
        return () => {
            mounted = false
        }
    }, [user])

    const moodCalendarPoints: MoodPoint[] = useMemo(() => {
        const series = reflectSummary?.mood_series || []
        return series.map((p) => ({
            date: typeof p.date === 'string' ? p.date : String(p.date),
            mood_score: typeof p.mood_score === 'number' ? p.mood_score : Number(p.mood_score),
            label: p.label,
            emoji: null,
        }))
    }, [reflectSummary])

    const chartData = useMemo(
        () =>
            (reflectSummary?.mood_series || []).map((p) => ({
                day: toShortWeekday(typeof p.date === 'string' ? p.date : String(p.date)),
                mood: p.mood_score_pct,
                note: p.label,
            })),
        [reflectSummary],
    )

    const distinctMoodDays = useMemo(() => new Set(moodCalendarPoints.map((p) => p.date.slice(0, 10))).size, [moodCalendarPoints])

    const showSparseMoodNote = distinctMoodDays > 0 && distinctMoodDays < 4

    const milestones = useMemo(() => {
        if (!reflectSummary) return []
        const chips: Array<{ Icon: LucideIcon; label: string }> = []
        const streak = reflectSummary.progress.streak_days ?? 0
        if (streak >= 3) chips.push({ Icon: Flame, label: `${streak} ngày liên tiếp` })
        const breathSessions = reflectSummary.progress.breathing_sessions ?? 0
        if (breathSessions > 0) chips.push({ Icon: Wind, label: `${breathSessions} lần thở` })
        if (reflectSummary.sufficiency.readiness_level === 'weekly_trend' || reflectSummary.sufficiency.readiness_level === 'stable_pattern') {
            chips.push({ Icon: Sprout, label: 'Có xu hướng nhẹ trong khung thời gian gần đây' })
        }
        if ((reflectSummary.progress.total_sessions ?? 0) >= 10) chips.push({ Icon: Star, label: '10 lần trò chuyện' })
        return chips
    }, [reflectSummary])

    const radarScores = useMemo<WellnessScores | null>(() => {
        if (!reflectSummary?.radar_available) return null
        return dimsToRadarScores(reflectSummary.wellness_dimensions)
    }, [reflectSummary])

    const completedDateSet = useMemo(() => {
        const s = new Set<string>()
        for (const d of reflectSummary?.checkin_history_preview || []) {
            if (d.completed) s.add(d.date.slice(0, 10))
        }
        return s
    }, [reflectSummary])

    const displayName = user?.displayName || 'bạn'

    return (
        <div className={`relative min-h-screen overflow-hidden ${isDark ? 'text-theme-text-primary' : 'text-serene-ink'}`}>

            {/* DayDetailSheet rendered outside stacking context */}
            <DayDetailSheet detail={selectedDay} onClose={() => setSelectedDay(null)} />
            <CheckinHistoryModal open={historyOpen} onClose={() => setHistoryOpen(false)} isDark={isDark} />

            <div className="flex-1">

                <div className="mx-auto flex w-full max-w-5xl flex-col items-center">
                    <section className={`w-full rounded-[2.5rem] border ${isDark ? 'border-theme-border/50 bg-theme-surface/40' : 'border-theme-border/10 bg-white/40 shadow-sm'} p-4 backdrop-blur-3xl md:p-7 lg:p-8`}>
                        <div className="text-center">
                            <p className={`mb-3 text-xs font-semibold uppercase tracking-[0.28em] ${isDark ? 'text-theme-text-secondary' : 'text-serene-primary/70'}`}>
                                Nhìn Lại
                            </p>
                            <h1 className={`font-display text-4xl font-light leading-tight ${isDark ? 'text-theme-text-primary' : 'text-[#2F342E]'} md:text-5xl lg:text-6xl`}>
                                Chào <span className={`italic font-medium text-theme-text-primary`}>{displayName}</span>
                            </h1>
                            <p className={`mx-auto mt-3 max-w-2xl text-xs italic leading-relaxed ${isDark ? 'text-theme-text-secondary' : 'text-serene-muted'} md:text-sm`}>
                                Dữ liệu cảm xúc của bạn đang được cập nhật liên tục từ những phiên trò chuyện cùng Serene.
                            </p>
                        </div>

                        {error && (
                            <div className={`mt-6 rounded-2xl border px-4 py-3 text-sm ${isDark ? 'border-red-900/50 bg-red-950/30 text-red-400' : 'border-red-200 bg-red-50 text-red-700'}`}>
                                {error}
                            </div>
                        )}

                        {loading && (
                            <Skeleton />
                        )}

                        {!loading && reflectSummary && (
                            <div className="mt-6">
                                <TinHieuCard sufficiency={reflectSummary.sufficiency} insights={reflectSummary.top_insights} isDark={isDark} />
                            </div>
                        )}

                        <div className={`mt-6 rounded-[1.75rem] border ${isDark ? 'border-theme-border/30 bg-theme-surface/60' : 'border-theme-border/20 bg-white/30'} p-4 backdrop-blur-md md:p-6 shadow-sm`}>
                                <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
                                    <div>
                                        <h2 className={`font-display text-xl ${isDark ? 'text-theme-text-primary' : 'text-serene-primary'} md:text-2xl`}>Biểu đồ cảm xúc</h2>
                                        <p className={`text-[10px] uppercase tracking-[0.28em] ${isDark ? 'text-theme-text-secondary' : 'text-serene-primary/60'}`}>
                                            14 ngày gần nhất (theo check-in)
                                        </p>
                                    </div>
                                    <div className="flex flex-col items-end gap-1 text-[10px] text-theme-text-secondary">
                                        {reflectSummary && (
                                            <span className="rounded-full bg-black/5 px-2 py-1 dark:bg-white/10">
                                                {reflectSummary.mood_series.length} ngày có điểm mood
                                            </span>
                                        )}
                                    </div>
                                </div>

                                {showSparseMoodNote && chartData.length > 0 && (
                                    <div className="mb-3 rounded-2xl border border-amber-200/60 bg-amber-50/80 px-3 py-2 text-xs text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-100">
                                        Dữ liệu hiện có ít ngày hoạt động — Serene chỉ xem đây là tín hiệu ban đầu, chưa phải xu hướng dài.
                                    </div>
                                )}

                                <div className="min-h-60 min-w-0 md:min-h-68">
                                    {chartData.length > 0 ? (
                                        <ResponsiveContainer width="100%" height={248} minWidth={1} minHeight={1}>
                                            <AreaChart data={chartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                                                <defs>
                                                    <linearGradient id="moodGradient" x1="0" x2="0" y1="0" y2="1">
                                                        <stop offset="5%" stopColor={isDark ? "var(--color-theme-accent)" : "#4d6359"} stopOpacity={0.38} />
                                                        <stop offset="95%" stopColor={isDark ? "var(--color-theme-accent)" : "#4d6359"} stopOpacity={0.04} />
                                                    </linearGradient>
                                                </defs>
                                                <CartesianGrid stroke={isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)"} strokeDasharray="4 10" vertical={false} />
                                                <XAxis
                                                    dataKey="day"
                                                    axisLine={false}
                                                    tickLine={false}
                                                    tick={{ fill: isDark ? 'var(--theme-text-tertiary)' : 'var(--theme-text-secondary)', fontSize: 11 }}
                                                />
                                                <YAxis hide domain={[0, 100]} />
                                                <Tooltip
                                                    cursor={{ stroke: isDark ? 'var(--color-theme-accent)' : '#4d6359', strokeOpacity: 0.12, strokeWidth: 1 }}
                                                    contentStyle={{
                                                        borderRadius: '1rem',
                                                        border: isDark ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(0,0,0,0.05)',
                                                        background: isDark ? 'rgba(22, 27, 34, 0.9)' : 'rgba(255,255,255,0.95)',
                                                        boxShadow: '0 18px 40px rgba(0,0,0,0.14)',
                                                        backdropFilter: 'blur(8px)',
                                                    }}
                                                    itemStyle={{ color: isDark ? 'var(--color-theme-accent)' : '#4d6359' }}
                                                    labelStyle={{ color: isDark ? 'var(--theme-text-primary)' : 'var(--theme-text-primary)', fontWeight: 700 }}
                                                    formatter={(value, name) => [
                                                        `${value ?? 0}%`,
                                                        name === 'mood' ? 'Cảm xúc' : String(name ?? ''),
                                                    ]}
                                                    labelFormatter={(label) => `Ngày ${label}`}
                                                />
                                                <Area
                                                    type="monotone"
                                                    dataKey="mood"
                                                    stroke={isDark ? "var(--color-theme-accent)" : "#4d6359"}
                                                    strokeWidth={3}
                                                    fill="url(#moodGradient)"
                                                    dot={{ r: 4, stroke: isDark ? 'var(--theme-bg-secondary)' : '#faf9f5', strokeWidth: 2, fill: isDark ? 'var(--color-theme-accent)' : '#4d6359' }}
                                                    activeDot={{ r: 6, stroke: isDark ? 'var(--theme-bg-secondary)' : '#faf9f5', strokeWidth: 2, fill: isDark ? 'var(--color-theme-accent)' : '#4d6359' }}
                                                />
                                            </AreaChart>
                                        </ResponsiveContainer>
                                    ) : (
                                        <div className={`flex min-h-72 flex-col items-center justify-center gap-2 rounded-3xl border px-6 text-center text-sm ${isDark ? 'border-theme-border/30 bg-theme-surface/40 text-theme-text-secondary' : 'border-theme-border/10 bg-theme-surface/50 text-serene-muted'} md:min-h-80`}>
                                            <p>Chưa đủ dữ liệu để vẽ xu hướng.</p>
                                            <p className="text-xs leading-relaxed opacity-70 md:text-sm">
                                                Cần ít nhất 3 ngày có check-in hoặc 5 check-in để Serene vẽ mood trend đáng tin hơn.
                                            </p>
                                        </div>
                                    )}
                                </div>

                                <div className="mt-3 flex justify-between px-1 text-[9px] uppercase tracking-wider text-theme-text-primary md:text-[10px]">
                                    <span>{reflectSummary?.sufficiency.evidence_window_start || ''}</span>
                                    <span className="font-bold text-theme-text-secondary">Xu hướng từ check-in</span>
                                    <span>{reflectSummary?.sufficiency.evidence_window_end || ''}</span>
                                </div>
                            </div>

                        {reflectSummary && (
                            <section className={`mt-6 rounded-[1.75rem] border ${isDark ? 'border-theme-border/30 bg-theme-surface/60' : 'border-theme-border/20 bg-white/30'} p-4 backdrop-blur-md md:p-6 shadow-sm`}>
                                <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
                                    <div>
                                        <p className={`text-[10px] uppercase tracking-[0.3em] ${isDark ? 'text-theme-text-secondary' : 'text-serene-primary/70'}`}>
                                            Tiến trình của bạn
                                        </p>
                                        <h2 className={`mt-1 font-display text-xl ${isDark ? 'text-theme-text-primary' : 'text-serene-ink'} md:text-2xl`}>
                                            Check-in 28 ngày qua
                                        </h2>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => setHistoryOpen(true)}
                                        className={`text-xs font-semibold underline underline-offset-4 ${isDark ? 'text-theme-accent' : 'text-primary'}`}
                                    >
                                        Xem lịch sử đầy đủ
                                    </button>
                                </div>
                                <p className={`mb-3 text-xs ${isDark ? 'text-theme-text-secondary/90' : 'text-serene-muted'}`}>
                                    Ô xanh là ngày đã có ít nhất một check-in. Chạm vào lịch để mở chi tiết các lần check-in.
                                </p>
                                <MoodCalendar
                                    mode="completion"
                                    completedDates={completedDateSet}
                                    onOpenHistory={() => setHistoryOpen(true)}
                                />
                                {moodCalendarPoints.length > 0 && (
                                    <div className="mt-8 border-t border-white/20 pt-6 dark:border-theme-border/30">
                                        <p className={`mb-3 text-[10px] uppercase tracking-[0.28em] ${isDark ? 'text-theme-text-secondary' : 'text-serene-muted'}`}>
                                            Chi tiết mood theo ngày (ước lượng)
                                        </p>
                                        <MoodCalendar
                                            points={moodCalendarPoints}
                                            mode="score"
                                            onDayClick={(date, score, label) => setSelectedDay({ date, score, label })}
                                        />
                                    </div>
                                )}
                            </section>
                        )}

                        {reflectSummary && (
                            <div className="mt-6">
                                <WellnessDimensionCards dimensions={reflectSummary.wellness_dimensions} isDark={isDark} />
                            </div>
                        )}

                        {reflectSummary && radarScores && (
                            <section className={`mt-6 rounded-[1.75rem] border ${isDark ? 'border-theme-border/30 bg-theme-surface/60' : 'border-theme-border/20 bg-white/30'} p-4 backdrop-blur-md md:p-6 shadow-sm`}>
                                <div className="mb-1 flex items-end justify-between gap-4">
                                    <div>
                                        <p className={`text-[10px] uppercase tracking-[0.3em] ${isDark ? 'text-theme-text-secondary' : 'text-serene-primary/70'}`}>
                                            Radar (phụ)
                                        </p>
                                        <h2 className={`mt-1 font-display text-xl ${isDark ? 'text-theme-text-primary' : 'text-serene-ink'} md:text-2xl`}>
                                            Tổng quan 6 chiều
                                        </h2>
                                    </div>
                                    <p className={`text-right text-[10px] ${isDark ? 'text-theme-text-secondary/60' : 'text-serene-muted/60'} max-w-[140px] leading-relaxed`}>
                                        Chỉ hiển thị khi dữ liệu đủ dày — không phải điểm chẩn đoán.
                                    </p>
                                </div>
                                <WellnessRadar scores={radarScores} className="mt-2" />
                            </section>
                        )}

                        {milestones.length > 0 && (
                            <div className="flex gap-2 overflow-x-auto pb-2 mt-4 scrollbar-hide">
                                {milestones.map((m) => {
                                    const Mi = m.Icon
                                    return (
                                    <div
                                        key={m.label}
                                        className={`flex-shrink-0 flex items-center gap-1.5 ${isDark ? 'bg-theme-surface-alt/60 border border-theme-border/20' : 'bg-serene-accent/30'} rounded-full px-3 py-1.5 text-xs font-medium ${isDark ? 'text-theme-text-primary' : 'text-serene-ink'}`}
                                    >
                                        <Mi className="h-3.5 w-3.5 shrink-0 opacity-90" aria-hidden />
                                        <span>{m.label}</span>
                                    </div>
                                )})}
                            </div>
                        )}

                        {/* ── Progress Stats ── */}
                        {reflectSummary && (
                            <section className={`mt-6 rounded-[1.75rem] border ${isDark ? 'border-theme-border/20 bg-theme-surface/60' : 'border-theme-border/20 bg-white/30'} p-4 backdrop-blur-md md:p-6 shadow-sm`}>
                                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                                    <div>
                                        <p className={`text-[10px] uppercase tracking-[0.3em] text-theme-text-secondary`}>Tiến trình</p>
                                        <h2 className={`mt-1 font-display text-xl ${isDark ? 'text-theme-text-primary' : 'text-serene-ink'} md:text-2xl`}>Thống kê của bạn</h2>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => setHistoryOpen(true)}
                                        className={`text-xs font-semibold underline underline-offset-4 ${isDark ? 'text-theme-accent' : 'text-primary'}`}
                                    >
                                        Lịch sử check-in
                                    </button>
                                </div>
                                <ProgressStats
                                    data={{
                                        streakDays: reflectSummary.progress.streak_days ?? 0,
                                        bestStreak: reflectSummary.progress.streak_days ?? 0,
                                        weeklyCheckins: reflectSummary.checkin_history_preview.filter((d) => d.completed).length,
                                        totalSessions: reflectSummary.progress.total_sessions ?? 0,
                                        breathingSessions: reflectSummary.progress.breathing_sessions ?? 0,
                                        daysActive30d: reflectSummary.progress.days_active_last_30 ?? 0,
                                    }}
                                />
                            </section>
                        )}

                        <section className={`my-6 rounded-3xl border-l-4 ${isDark ? 'border-theme-accent bg-theme-accent/10 shadow-sm' : 'border-serene-primary bg-serene-primary/5'} p-4 md:p-6`}>
                            <div className="mb-4 flex items-center gap-3">
                                <div className={`rounded-full ${isDark ? 'bg-theme-accent/20 text-theme-accent' : 'bg-theme-accent/10 p-2.5 text-theme-accent'} p-2.5`}>
                                    <Sparkles className="h-5 w-5" />
                                </div>
                                <h2 className={`font-display text-xl italic ${isDark ? 'text-theme-text-primary' : 'text-theme-text-primary'} md:text-2xl`}>
                                    Lời nhắn tuần từ Serene
                                </h2>
                            </div>
                            <p className={`text-sm leading-relaxed ${isDark ? 'text-theme-text-primary/90 font-medium' : 'text-theme-text-primary/80'} md:text-base`}>
                                {loading
                                    ? 'Serene đang phân tích dữ liệu tuần của bạn...'
                                    : `“${weeklyNote?.content || 'Bạn đang duy trì nỗ lực rất tốt. Hãy tiếp tục giữ nhịp nghỉ ngơi và chăm sóc bản thân.'}”`}
                            </p>
                        </section>
                    </section>
                </div>
            </div>

        </div>
    )
}
