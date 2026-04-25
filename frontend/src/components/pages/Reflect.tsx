import { ArrowRight, ChevronRight, Leaf, Sparkles, Wind } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts'
import { httpClient } from '../../api/httpClient'
import { useAuth } from '../../hooks/useAuth'

type MoodPoint = {
    date: string
    mood_score: number
    label: string
    emoji: string | null
}

type MoodTrendPayload = {
    period: { from: string; to: string }
    points: MoodPoint[]
    days_missing: string[]
    summary: string
}

type TopCoping = {
    action: string
    tried_count: number
}

type MentalHealthSummary = {
    wellness_score: number
    wellness_label: string
    mood_trend: MoodTrendPayload
    dominant_emotions: Array<{ emotion: string; count: number }>
    top_triggers: Array<{ tag: string; count: number; last_seen: string | null }>
    coping_stats: { total_attempts: number; effective_rate: number | null; top_coping: TopCoping[] }
    session_stats: { total_sessions: number; streak_days: number; days_active_last_30: number }
    clinical_snapshot: { phq9_score: number | null; gad7_score: number | null; crisis_level: number; last_scored_at: string | null }
    goals: Array<{ goal_id: string; text: string; status: string }>
    has_enough_data: boolean
}

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

const quickExercises = [
    {
        title: 'Thở 4-7-8',
        duration: '2 phút • Thư giãn',
        icon: Wind,
        tone: 'bg-primary/10 text-primary',
    },
    {
        title: 'Quét cơ thể',
        duration: '5 phút • Nhận thức',
        icon: Leaf,
        tone: 'bg-secondary-container/50 text-secondary',
    },
]

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

function normalizeTag(tag: string): string {
    return tag.replaceAll('_', ' ')
}

export default function Reflect() {
    const { user } = useAuth()
    const [summary, setSummary] = useState<MentalHealthSummary | null>(null)
    const [weeklyNote, setWeeklyNote] = useState<WeeklyNotePayload | null>(null)
    const [moodTrend, setMoodTrend] = useState<MoodTrendPayload | null>(null)
    const [recentJournal, setRecentJournal] = useState<JournalsPayload['journals'][number] | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [prompts, setPrompts] = useState<Array<{ id: string; text: string }>>([])

    useEffect(() => {
        let mounted = true
        const loadReflectData = async () => {
            setLoading(true)
            setError(null)
            try {
                const [summaryData, weeklyNoteData, moodTrendData, journalsData] = await Promise.all([
                    httpClient.get<MentalHealthSummary>('/reflect/mental-health-summary'),
                    httpClient.get<WeeklyNotePayload>('/reflect/weekly-note'),
                    httpClient.get<MoodTrendPayload>('/reflect/mood-trend?days=7'),
                    httpClient.get<JournalsPayload>('/reflect/journals?limit=1&offset=0'),
                ])
                if (!mounted) return
                setSummary(summaryData)
                setWeeklyNote(weeklyNoteData)
                setMoodTrend(moodTrendData)
                setRecentJournal(journalsData.journals[0] || null)
                httpClient.get<{ prompts: Array<{ id: string; text: string }> }>('/reflect/journal-prompts')
                    .then(d => setPrompts(d.prompts))
                    .catch(() => {
                        if (import.meta.env.DEV) console.warn('[Reflect] journal prompts fetch failed')
                    })
            } catch {
                if (!mounted) return
                setError('Không tải được dữ liệu Nhìn lại. Vui lòng thử lại sau.')
            } finally {
                if (!mounted) return
                setLoading(false)
            }
        }
        loadReflectData()
        return () => {
            mounted = false
        }
    }, [])

    const peaceScore = summary?.wellness_score ?? 0
    const chartData = useMemo(
        () =>
            (moodTrend?.points || []).map((point) => ({
                day: toShortWeekday(point.date),
                mood: Math.round((point.mood_score / 5) * 100),
                note: point.label,
            })),
        [moodTrend],
    )
    const milestones = useMemo(() => {
        if (!summary) return []
        const chips: Array<{ emoji: string; label: string }> = []
        const streak = summary.session_stats?.streak_days ?? 0
        if (streak >= 3) chips.push({ emoji: '🔥', label: `${streak} ngày liên tiếp` })
        const breathSessions = (summary.coping_stats as any)?.breathing_sessions ?? 0
        if (breathSessions > 0) chips.push({ emoji: '🌬️', label: `${breathSessions} lần thở` })
        if ((summary.wellness_score ?? 0) > 60) chips.push({ emoji: '🌱', label: 'Ổn hơn tuần trước' })
        if ((summary.session_stats?.total_sessions ?? 0) >= 10) chips.push({ emoji: '⭐', label: '10 lần trò chuyện' })
        return chips
    }, [summary])

    const ringCircumference = 2 * Math.PI * 82
    const ringOffset = ringCircumference - (Math.max(0, Math.min(100, peaceScore)) / 100) * ringCircumference
    const displayName = user?.displayName || 'bạn'

    return (
        <div className="relative min-h-screen overflow-hidden text-serene-ink ">

            <div className="flex-1">

                <div className="mx-auto flex w-full max-w-5xl flex-col items-center">
                    <section className="border border-white/35 bg-white/40 backdrop-blur-xl w-full rounded-4xl  p-5 shadow-md md:p-10 lg:p-12">
                        <div className="text-center">
                            <h1 className="font-display text-5xl font-light leading-tight text-[#2F342E] md:text-6xl lg:text-7xl">
                                Chào <span className="italic text-primary font-medium">{displayName}</span>
                            </h1>
                            <p className="mx-auto mt-5 max-w-2xl text-sm italic leading-relaxed text-serene-primary/80 md:text-lg">
                                Dữ liệu cảm xúc của bạn đang được cập nhật liên tục từ những phiên trò chuyện cùng Serene.
                            </p>
                        </div>

                        {error && (
                            <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                {error}
                            </div>
                        )}

                        {loading && (
                            <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
                                <div className="h-20 animate-pulse rounded-2xl bg-white/50 lg:col-span-2" />
                                <div className="h-20 animate-pulse rounded-2xl bg-white/50" />
                            </div>
                        )}

                        {!loading && summary && !summary.has_enough_data && (
                            <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                                Chưa đủ dữ liệu để đánh giá sâu. Hãy tiếp tục trò chuyện thêm để nhận insight cá nhân hóa.
                            </div>
                        )}

                        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2 lg:gap-8">
                            <div className="rounded-[1.75rem] border border-white/25 bg-white/30 p-6 text-center backdrop-blur-md md:p-8">
                                <p className="mb-6 text-[10px] uppercase tracking-[0.3em] text-primary">Peace Score</p>
                                <div className="relative mx-auto flex h-48 w-48 items-center justify-center md:h-56 md:w-56">
                                    <svg className="h-full w-full -rotate-90 transform">
                                        <circle cx="112" cy="112" r="82" fill="transparent" className="text-white/40" stroke="currentColor" strokeWidth="12" />
                                        <circle
                                            cx="112"
                                            cy="112"
                                            r="82"
                                            fill="transparent"
                                            stroke="url(#peaceGradient)"
                                            strokeDasharray={ringCircumference}
                                            strokeDashoffset={ringOffset}
                                            strokeLinecap="round"
                                            strokeWidth="12"
                                        />
                                        <defs>
                                            <linearGradient id="peaceGradient" x1="0%" x2="100%" y1="0%" y2="100%">
                                                <stop offset="0%" style={{ stopColor: '#4d6359', stopOpacity: 1 }} />
                                                <stop offset="100%" style={{ stopColor: '#c2dacd', stopOpacity: 1 }} />
                                            </linearGradient>
                                        </defs>
                                    </svg>

                                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                                        <span className="font-display text-5xl font-light text-serene-pborder-serene-primary md:text-6xl">
                                            {loading ? '--' : peaceScore}
                                            <span className="text-xl opacity-40 md:text-2xl">%</span>
                                        </span>
                                        <span className="mt-2 text-[10px] uppercase tracking-[0.3em] text-serene-primary-dim">
                                            {loading ? 'Đang cập nhật' : summary?.wellness_label || 'Đang cập nhật'}
                                        </span>
                                    </div>
                                </div>
                                <p className="mx-auto mt-6 max-w-sm text-sm leading-relaxed">
                                    {loading
                                        ? 'Đang tổng hợp dữ liệu từ mood check-in và các phiên trò chuyện...'
                                        : `Bạn đã có ${summary?.session_stats.total_sessions || 0} phiên, chuỗi duy trì hiện tại là ${summary?.session_stats.streak_days || 0} ngày.`}
                                </p>
                            </div>

                            <div className="rounded-[1.75rem] border border-white/25 bg-white/30 p-6 backdrop-blur-md md:p-8">
                                <div className="mb-6 flex items-end justify-between gap-4">
                                    <div>
                                        <h2 className="font-display text-2xl text-serene-pborder-serene-primary md:text-[2rem]">Biểu đồ cảm xúc</h2>
                                        <p className="text-[10px] uppercase tracking-[0.28em] text-serene-primary/60">
                                            7 ngày qua
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="h-2.5 w-2.5 rounded-full bg-primary" />
                                        <span className="h-2.5 w-2.5 rounded-full bg-white/50" />
                                    </div>
                                </div>

                                <div className="h-72 w-full md:h-80">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <AreaChart data={chartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                                            <defs>
                                                <linearGradient id="moodGradient" x1="0" x2="0" y1="0" y2="1">
                                                    <stop offset="5%" stopColor="#4d6359" stopOpacity={0.38} />
                                                    <stop offset="95%" stopColor="#4d6359" stopOpacity={0.04} />
                                                </linearGradient>
                                            </defs>
                                            <CartesianGrid stroke="rgba(47, 52, 46, 0.08)" strokeDasharray="4 10" vertical={false} />
                                            <XAxis
                                                dataKey="day"
                                                axisLine={false}
                                                tickLine={false}
                                                tick={{ fill: '#5c605a', fontSize: 11 }}
                                            />
                                            <YAxis hide domain={[0, 100]} />
                                            <Tooltip
                                                cursor={{ stroke: '#4d6359', strokeOpacity: 0.12, strokeWidth: 1 }}
                                                contentStyle={{
                                                    borderRadius: '1rem',
                                                    border: '1px solid rgba(255,255,255,0.5)',
                                                    background: 'rgba(255,255,255,0.85)',
                                                    boxShadow: '0 18px 40px rgba(47,52,46,0.14)',
                                                }}
                                                labelStyle={{ color: '#2f342e', fontWeight: 700 }}
                                                formatter={(value, name) => [
                                                    `${value ?? 0}%`,
                                                    name === 'mood' ? 'Mức ổn định cảm xúc' : String(name ?? ''),
                                                ]}
                                                labelFormatter={(label) => `Ngày ${label}`}
                                            />
                                            <Area
                                                type="monotone"
                                                dataKey="mood"
                                                stroke="#4d6359"
                                                strokeWidth={3}
                                                fill="url(#moodGradient)"
                                                dot={{ r: 4, stroke: '#faf9f5', strokeWidth: 2, fill: '#4d6359' }}
                                                activeDot={{ r: 6, stroke: '#faf9f5', strokeWidth: 2, fill: '#4d6359' }}
                                            />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                </div>

                                <div className="mt-5 flex justify-between px-1 text-[10px] uppercase tracking-widest text-serene-primary/70">
                                    <span>{moodTrend?.period.from || ''}</span>
                                    <span className="font-bold text-primary">{moodTrend?.summary || ''}</span>
                                    <span>{moodTrend?.period.to || ''}</span>
                                </div>
                            </div>
                        </div>

                        {milestones.length > 0 && (
                            <div className="flex gap-2 overflow-x-auto pb-2 mt-4 scrollbar-hide">
                                {milestones.map((m) => (
                                    <div
                                        key={m.label}
                                        className="flex-shrink-0 flex items-center gap-1.5 bg-[var(--color-guong-bg)] rounded-full px-3 py-1.5 text-xs font-medium text-[var(--color-serene-ink)]"
                                    >
                                        <span aria-hidden="true">{m.emoji}</span>
                                        <span>{m.label}</span>
                                    </div>
                                ))}
                            </div>
                        )}

                        <section className="mt-8 rounded-3xl border-l-4 border-serene-primary bg-serene-primary/5 p-6 md:p-8">
                            <div className="mb-5 flex items-center gap-4">
                                <div className="rounded-full bg-primary/10 p-3 text-primary">
                                    <Sparkles className="h-6 w-6" />
                                </div>
                                <h2 className="font-display text-2xl italic text-emerald-900 md:text-3xl">
                                    Lời nhắn tuần từ Serene
                                </h2>
                            </div>
                            <p className="text-base leading-relaxed text-serene-ink/90 md:text-lg">
                                {loading
                                    ? 'Serene đang phân tích dữ liệu tuần của bạn...'
                                    : `“${weeklyNote?.content || 'Bạn đang duy trì nỗ lực rất tốt. Hãy tiếp tục giữ nhịp nghỉ ngơi và chăm sóc bản thân.'}”`}
                            </p>
                        </section>

                        <section className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3 lg:gap-8">
                            <div className="rounded-3xl border border-white/25 bg-white/10 p-6 backdrop-blur-md lg:col-span-2 md:p-8">
                                <div className="mb-7 flex items-center justify-between gap-4">
                                    <div className="flex items-center gap-3">
                                        <Leaf className="h-5 w-5 text-primary" />
                                        <h3 className="font-display text-2xl text-serene-pborder-serene-primary">Nhật ký gần đây</h3>
                                    </div>
                                    <span className="text-[10px] uppercase tracking-widest text-serene-primary/50">
                                        {recentJournal?.created_at
                                            ? new Date(recentJournal.created_at).toLocaleDateString('vi-VN')
                                            : 'Chưa có'}
                                    </span>
                                </div>

                                <blockquote className="mb-6 font-display text-xl italic leading-relaxed text-serene-primary-dim md:text-3xl">
                                    {recentJournal
                                        ? `“${recentJournal.content_preview}”`
                                        : '“Hãy viết vài dòng cảm nhận để hệ thống hiểu bạn sâu hơn.”'}
                                </blockquote>

                                <button
                                    type="button"
                                    className="inline-flex items-center gap-2 text-xs uppercase tracking-widest text-serene-primary transition-transform hover:translate-x-0.5"
                                >
                                    Đọc toàn bộ
                                    <ArrowRight className="h-4 w-4" />
                                </button>
                            </div>

                            <aside className="rounded-3xl border border-white/25 bg-white/10 p-6 backdrop-blur-md md:p-8">
                                <h3 className="mb-6 font-display text-2xl text-serene-pborder-serene-primary">Bài tập nhanh</h3>
                                <div className="space-y-4">
                                    {quickExercises.map((exercise) => {
                                        const Icon = exercise.icon

                                        return (
                                            <button
                                                key={exercise.title}
                                                type="button"
                                                className="group flex w-full items-center gap-4 rounded-full bg-white p-4 text-left transition-all hover:bg-white/60"
                                            >
                                                <div className={`flex h-10 w-10 items-center justify-center rounded-full ${exercise.tone} bg-serene-on-primary `}>
                                                    <Icon className="h-5 w-5" />
                                                </div>
                                                <div>
                                                    <p className="text-sm font-bold text-serene-pborder-serene-primary">{exercise.title}</p>
                                                    <p className="text-[10px] text-serene-primary">{exercise.duration}</p>
                                                </div>
                                                <ChevronRight className="ml-auto h-4 w-4 text-serene-primary/30 transition-transform group-hover:translate-x-1" />
                                            </button>
                                        )
                                    })}
                                </div>
                                <div className="mt-6 rounded-2xl bg-white/60 p-4 text-xs text-serene-primary">
                                    <p>Tỷ lệ coping hiệu quả: {formatPercent(summary?.coping_stats.effective_rate)}</p>
                                    <p className="mt-2">
                                        Trigger gần đây:{' '}
                                        {summary?.top_triggers?.length
                                            ? summary.top_triggers.slice(0, 2).map((item) => normalizeTag(item.tag)).join(', ')
                                            : 'chưa có'}
                                    </p>
                                </div>
                            </aside>
                        </section>

                        {prompts.length > 0 && (
                            <section className="mt-6">
                                <h3 className="font-semibold text-[var(--color-serene-ink)] mb-3 text-sm">
                                    <span aria-hidden="true">✍️</span> Gợi ý ghi chép hôm nay
                                </h3>
                                <div className="flex flex-col gap-2">
                                    {prompts.slice(0, 3).map(p => (
                                        <div
                                            key={p.id}
                                            className="bg-[var(--color-guong-bg)] rounded-2xl p-4 text-sm text-[var(--color-serene-muted)] leading-relaxed"
                                        >
                                            {p.text}
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )}

                        <div className="mt-8 border-t border-serene-primary/5 pt-10 text-center">
                            <p className="font-display text-lg italic text-serene-primary border-serene-primary/50 md:text-xl">
                                “Học cách chữa lành là hành trình đẹp đẽ nhất của mỗi con người.”
                            </p>
                        </div>
                    </section>
                </div>
            </div>

        </div>
    )
}
