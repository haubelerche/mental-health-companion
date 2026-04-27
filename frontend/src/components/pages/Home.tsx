import {
    ArrowRight,
    BarChart2,
    BookOpen,
    CheckCircle2,
    Circle,
    Flame,
    Heart,
    MessageSquareText,
    Wind,
    Leaf,
    Headphones,
    ClipboardList,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { homeService } from '../../services/homeService'
import { httpClient } from '../../api/httpClient'
import { ROUTE_PATHS } from '../../routes/paths'
import { MoodWordChips } from '../common/MoodWordChips'
import { StreakBar } from '../common/StreakBar'
import { WellnessRadar, type WellnessScores } from '../wellness/WellnessRadar'
import { useAuth } from '../../hooks/useAuth'

type DailyItem = { id: string; label: string; icon: string; route: string }

type RecoCard = {
    icon: typeof Wind
    emoji: string
    label: string
    desc: string
    route: string
    accentClass: string
}

const RECO_CARDS: RecoCard[] = [
    {
        icon: Wind,
        emoji: '🌬️',
        label: 'Thở hộp 4-4-4',
        desc: '3 phút · Giảm lo âu',
        route: `${ROUTE_PATHS.exercises}?exercise=box_breath`,
        accentClass: 'bg-may/10 text-may',
    },
    {
        icon: Leaf,
        emoji: '🧘',
        label: 'Thiền buổi sáng',
        desc: '5 phút · Bắt đầu ngày mới',
        route: `${ROUTE_PATHS.exercises}?type=meditation&id=morning_5`,
        accentClass: 'bg-serene-primary/10 text-serene-primary',
    },
    {
        icon: Headphones,
        emoji: '🌊',
        label: 'Tiếng sóng biển',
        desc: 'Âm thanh · Thư giãn',
        route: `${ROUTE_PATHS.exercises}?type=sound&id=ocean`,
        accentClass: 'bg-la-ban/10 text-la-ban',
    },
    {
        icon: ClipboardList,
        emoji: '📓',
        label: 'Check-in buổi tối',
        desc: 'Nhìn lại ngày hôm nay',
        route: `${ROUTE_PATHS.checkin}?variant=evening`,
        accentClass: 'bg-lua/10 text-lua',
    },
]

type QuickAction = {
    icon: typeof Wind
    label: string
    desc: string
    route: string
    bgClass: string
    iconClass: string
}

const DAILY_PLAN: DailyItem[] = [
    { id: 'checkin', label: 'Check-in sáng', icon: '🌅', route: ROUTE_PATHS.checkin },
    { id: 'breathing', label: 'Thở 1 phút', icon: '🌬️', route: ROUTE_PATHS.exercises },
    { id: 'journal', label: 'Nhật ký tối', icon: '📓', route: ROUTE_PATHS.checkin },
]

const QUICK_ACTIONS: QuickAction[] = [
    {
        icon: MessageSquareText,
        label: 'Chat với Serene',
        desc: 'Luôn sẵn sàng',
        route: ROUTE_PATHS.chat,
        bgClass: 'bg-serene-primary/10',
        iconClass: 'text-serene-primary',
    },
    {
        icon: Wind,
        label: 'Bài thở',
        desc: '1–5 phút',
        route: ROUTE_PATHS.exercises,
        bgClass: 'bg-may-bg',
        iconClass: 'text-may',
    },
    {
        icon: BookOpen,
        label: 'Check-in',
        desc: 'Ghi nhận cảm xúc',
        route: ROUTE_PATHS.checkin,
        bgClass: 'bg-lua-bg',
        iconClass: 'text-lua',
    },
    {
        icon: BarChart2,
        label: 'Khám phá',
        desc: 'Bài tập & nguồn lực',
        route: ROUTE_PATHS.exercises,
        bgClass: 'bg-la-ban-bg',
        iconClass: 'text-la-ban',
    },
]

function getGreeting(): string {
    const hour = new Date().getHours()
    if (hour < 12) return 'Chào buổi sáng'
    if (hour < 18) return 'Chào buổi chiều'
    return 'Chào buổi tối'
}

export default function Home() {
    const navigate = useNavigate()
    const { user } = useAuth()
    const [quote, setQuote] = useState<{ text: string; author?: string | null } | null>(null)
    const [checkedPlan, setCheckedPlan] = useState<Set<string>>(new Set())
    const [selectedMoods, setSelectedMoods] = useState<string[]>([])
    const hearts = 0   // frontend-only placeholder; connect to API in Sprint 4
    const streak = 0   // frontend-only placeholder; connect to /reflect/summary in Sprint 4
    const [wellnessScores, setWellnessScores] = useState<WellnessScores | null>(null)

    useEffect(() => {
        let mounted = true
        homeService
            .feed()
            .then((data) => {
                if (!mounted) return
                setQuote(data.quote_of_day)
            })
            .catch(() => undefined)

        // Fetch wellness mini-preview in background (non-blocking)
        httpClient
            .get<{ wellness_score: number; coping_stats: { breathing_sessions?: number; effective_rate: number | null }; session_stats: { streak_days: number; days_active_last_30: number }; clinical_snapshot: { phq9_score: number | null } }>('/reflect/mental-health-summary')
            .then((data) => {
                if (!mounted) return
                const w = data.wellness_score ?? 50
                const phq9 = data.clinical_snapshot.phq9_score
                const breath = data.coping_stats.breathing_sessions ?? 0
                const active = data.session_stats.days_active_last_30 ?? 0
                const rate = data.coping_stats.effective_rate
                const streak30 = data.session_stats.streak_days ?? 0
                setWellnessScores({
                    emotional: Math.round(w),
                    sleep: phq9 !== null ? Math.max(5, Math.round(100 - phq9 * 3.7)) : Math.round(w * 0.85),
                    mindfulness: Math.round(Math.min(100, 30 + breath * 3.5)),
                    social: Math.round(Math.min(100, (active / 30) * 100)),
                    physical: rate !== null ? Math.round(rate * 100) : Math.round(w * 0.9),
                    growth: Math.round(Math.min(100, 20 + streak30 * 2.67)),
                })
            })
            .catch(() => undefined)

        return () => {
            mounted = false
        }
    }, [])

    const togglePlan = (id: string) => {
        setCheckedPlan((prev) => {
            const next = new Set(prev)
            if (next.has(id)) next.delete(id)
            else next.add(id)
            return next
        })
    }

    const displayName = user?.displayName || 'bạn'
    const completedCount = checkedPlan.size
    const totalCount = DAILY_PLAN.length

    return (
        <div className="space-y-6 pb-8 lg:space-y-8">

            {/* ── Greeting header ── */}
            <header className="flex items-start justify-between gap-4">
                <div>
                    <p className="text-sm font-medium uppercase tracking-wide text-white/70">
                        {getGreeting()}
                    </p>
                    <h1 className="mt-1 font-display text-4xl italic text-white sm:text-5xl">
                        {displayName}
                    </h1>
                </div>
                <div className="flex items-center gap-3 rounded-full border border-white/30 bg-white/20 px-4 py-2 backdrop-blur-sm">
                    <span className="flex items-center gap-1 text-sm font-semibold text-rose-300">
                        <Heart className="h-4 w-4 fill-current" />
                        {hearts}
                    </span>
                    <span className="h-4 w-px bg-white/30" />
                    <span className="flex items-center gap-1 text-sm font-semibold text-amber-300">
                        <Flame className="h-4 w-4 fill-current" />
                        {streak}
                    </span>
                </div>
            </header>

            {/* ── Today's plan + streak ── */}
            <section className="rounded-[28px] border border-white/35 bg-white/45 p-6 backdrop-blur-xl">
                <div className="mb-4 flex items-center justify-between">
                    <h2 className="font-display text-2xl text-serene-ink">Hôm nay của bạn</h2>
                    <span className="text-sm font-semibold text-serene-primary">
                        {completedCount}/{totalCount}
                    </span>
                </div>

                <div className="space-y-2.5">
                    {DAILY_PLAN.map((item) => {
                        const done = checkedPlan.has(item.id)
                        return (
                            <button
                                key={item.id}
                                type="button"
                                onClick={() => togglePlan(item.id)}
                                className="flex w-full items-center gap-3 rounded-2xl bg-white/60 px-4 py-3 text-left transition hover:bg-white/80 active:scale-[0.98]"
                            >
                                {done ? (
                                    <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-serene-primary" />
                                ) : (
                                    <Circle className="h-5 w-5 flex-shrink-0 text-serene-outline" />
                                )}
                                <span className={`text-sm ${done ? 'line-through text-serene-muted' : 'text-serene-ink'}`}>
                                    {item.icon} {item.label}
                                </span>
                                {done && (
                                    <motion.span
                                        initial={{ scale: 0, opacity: 0 }}
                                        animate={{ scale: 1, opacity: 1 }}
                                        className="ml-auto text-xs font-semibold text-serene-primary"
                                    >
                                        +5 ♥
                                    </motion.span>
                                )}
                            </button>
                        )
                    })}
                </div>

                <div className="mt-5 border-t border-serene-outline/20 pt-5">
                    <p className="mb-3 text-xs uppercase tracking-[0.22em] text-serene-muted">
                        Chuỗi tuần này
                    </p>
                    <StreakBar streak={streak} />
                </div>
            </section>

            {/* ── Mood word chips ── */}
            <section className="rounded-[28px] border border-white/35 bg-white/45 p-6 backdrop-blur-xl">
                <h2 className="mb-4 font-display text-2xl text-serene-ink">Tâm trạng hôm nay?</h2>
                <MoodWordChips selected={selectedMoods} onChange={setSelectedMoods} />
                <AnimatePresence>
                    {selectedMoods.length > 0 && (
                        <motion.button
                            type="button"
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 6 }}
                            onClick={() => navigate(ROUTE_PATHS.checkin)}
                            className="mt-4 text-sm font-medium text-serene-primary underline underline-offset-4 transition hover:opacity-70"
                        >
                            Ghi chép thêm →
                        </motion.button>
                    )}
                </AnimatePresence>
            </section>

            {/* ── Quick action grid 2×2 ── */}
            <section>
                <h2 className="mb-4 font-display text-2xl text-white">Bắt đầu từ đây</h2>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {QUICK_ACTIONS.map((action) => {
                        const Icon = action.icon
                        return (
                            <button
                                key={action.label}
                                type="button"
                                onClick={() => navigate(action.route)}
                                className="group flex flex-col gap-3 rounded-[22px] border border-white/35 bg-white/50 p-5 text-left backdrop-blur-xl transition hover:bg-white/70 active:scale-[0.97]"
                            >
                                <div
                                    className={`inline-flex h-10 w-10 items-center justify-center rounded-xl ${action.bgClass} ${action.iconClass}`}
                                >
                                    <Icon className="h-5 w-5" />
                                </div>
                                <div>
                                    <p className="text-sm font-semibold text-serene-ink">{action.label}</p>
                                    <p className="mt-0.5 text-xs text-serene-muted">{action.desc}</p>
                                </div>
                            </button>
                        )
                    })}
                </div>
            </section>

            {/* ── Wellness radar mini preview ── */}
            <button
                type="button"
                onClick={() => navigate(ROUTE_PATHS.reflect)}
                className="group w-full rounded-[28px] border border-white/25 bg-serene-primary/85 p-6 text-left backdrop-blur-xl transition hover:bg-serene-primary/95 active:scale-[0.99]"
            >
                <div className="flex items-center justify-between gap-4">
                    <div className="flex-1">
                        <p className="text-xs uppercase tracking-[0.22em] text-serene-accent/80">
                            Nhìn Lại · Tiến trình tuần này
                        </p>
                        <h3 className="mt-1.5 font-display text-2xl text-serene-on-primary">
                            6 chiều sức khoẻ
                        </h3>
                        <p className="mt-1 text-sm text-serene-on-primary/70">
                            Xem chi tiết biểu đồ →
                        </p>
                        <ArrowRight className="mt-3 h-5 w-5 text-serene-on-primary/50 transition group-hover:translate-x-1" />
                    </div>
                    <div className="flex-shrink-0">
                        {wellnessScores ? (
                            <WellnessRadar scores={wellnessScores} mini />
                        ) : (
                            <div className="flex h-[156px] w-32 items-center justify-center rounded-2xl bg-white/10">
                                <p className="text-center text-[10px] text-serene-on-primary/50 leading-relaxed px-2">
                                    Check-in thêm để thấy radar
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            </button>

            {/* ── Dành cho bạn ── */}
            <section>
                <div className="mb-4 flex items-center justify-between">
                    <h2 className="font-display text-2xl text-white">Dành cho bạn</h2>
                    <button
                        type="button"
                        onClick={() => navigate(ROUTE_PATHS.exercises)}
                        className="text-xs font-medium text-white/70 underline underline-offset-4 transition hover:text-white"
                    >
                        Xem tất cả
                    </button>
                </div>
                <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
                    {RECO_CARDS.map((card) => {
                        const Icon = card.icon
                        return (
                            <button
                                key={card.label}
                                type="button"
                                onClick={() => navigate(card.route)}
                                className="flex min-w-[148px] flex-shrink-0 flex-col gap-3 rounded-[22px] border border-white/35 bg-white/50 p-4 text-left backdrop-blur-xl transition hover:bg-white/70 active:scale-[0.97]"
                            >
                                <div className={`inline-flex h-10 w-10 items-center justify-center rounded-xl text-xl ${card.accentClass}`}>
                                    {card.emoji}
                                </div>
                                <div>
                                    <p className="text-sm font-semibold text-serene-ink leading-tight">{card.label}</p>
                                    <p className="mt-0.5 text-xs text-serene-muted">{card.desc}</p>
                                </div>
                            </button>
                        )
                    })}
                </div>
            </section>

            {/* ── Quote section ── */}
            <section className="rounded-4xl border border-white/30 bg-serene-primary/80 px-7 py-14 text-center backdrop-blur-xl sm:px-12 lg:px-20 lg:py-20">
                <blockquote className="mx-auto max-w-4xl font-display text-3xl italic leading-snug text-serene-on-primary sm:text-5xl">
                    {quote?.text
                        ? `"${quote.text}"`
                        : '"Giây phút hiện tại là nơi duy nhất sự sống thực sự tồn tại."'}
                </blockquote>
                <p className="mt-5 text-xs uppercase tracking-[0.25em] text-serene-on-primary/65">
                    {quote?.author || 'Thích Nhất Hạnh'}
                </p>
            </section>
        </div>
    )
}
