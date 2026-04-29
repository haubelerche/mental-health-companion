import {
    ArrowRight,
    BarChart2,
    BookOpen,
    Flame,
    Heart,
    MessageSquareText,
    Wind,
    Leaf,
    Headphones,
    ClipboardList,
    Info,
    ChevronRight,
    X,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import Carousel from 'react-multi-carousel/lib/Carousel';
import 'react-multi-carousel/lib/styles.css';
import quotesJson from '../../../famous-quotes.json'
import { useNavigate } from 'react-router-dom'
import { homeService } from '../../services/homeService'
import { httpClient } from '../../api/httpClient'
import { ROUTE_PATHS } from '../../routes/paths'
import { MoodWordChips } from '../common/MoodWordChips'
import { StreakBar } from '../common/StreakBar'
import { WellnessRadar, type WellnessScores } from '../wellness/WellnessRadar'
import { useAuth } from '../../hooks/useAuth'
import { dashboardService, type NutritionDailyTip } from '../../services/dashboardService'
import {
    getRewardProgress,
    REWARD_UPDATED_EVENT,
    syncRewardStreak,
} from '../../utils/rewardProgress'

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
        iconClass: 'text-blue-500',
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
        label: 'Dinh dưỡng',
        desc: 'Ăn uống nâng mood',
        route: ROUTE_PATHS.nutrition,
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

type TimeSlot = 'morning' | 'day' | 'evening'

type ReminderItem = {
    id: string
    title: string
    summary: string
    detailTitle: string
    importance: string
    downside: string
    route?: string
}

const TIME_SLOT_META: Record<TimeSlot, { label: string; range: string; intro: string }> = {
    morning: {
        label: 'Buổi sáng',
        range: '05:00 - 10:00',
        intro: 'Khởi động nhẹ nhàng để cơ thể và tâm trí có năng lượng tích cực đầu ngày.',
    },
    day: {
        label: 'Buổi trưa / chiều',
        range: '10:00 - 18:00',
        intro: 'Giữ nhịp bền trong giờ học và làm việc, tránh tụt năng lượng vào cuối chiều.',
    },
    evening: {
        label: 'Buổi tối',
        range: '18:00 - 24:00',
        intro: 'Ưu tiên hồi phục để ngủ sâu hơn và dậy với tinh thần nhẹ hơn vào hôm sau.',
    },
}

const SLOT_REMINDERS: Record<TimeSlot, ReminderItem[]> = {
    morning: [
        {
            id: 'morning_checkin',
            title: 'Check-in mood buổi sáng',
            summary: 'Đặt tên cảm xúc đầu ngày để dễ quản trị tâm trạng.',
            detailTitle: 'Vì sao nên check-in mood buổi sáng?',
            importance: 'Bạn nhận diện cảm xúc sớm thì dễ chọn cách phản ứng phù hợp, giảm căng thẳng dây chuyền trong ngày.',
            downside: 'Bỏ qua bước này dễ khiến cảm xúc tiêu cực tích tụ và bùng lên khi gặp áp lực nhỏ.',
            route: ROUTE_PATHS.checkin,
        },
        {
            id: 'morning_water',
            title: 'Uống 250ml nước',
            summary: 'Bù nước sau giấc ngủ đêm để tỉnh táo hơn.',
            detailTitle: 'Tại sao cần uống nước ngay đầu ngày?',
            importance: 'Nước giúp tuần hoàn tốt, não tỉnh hơn và giảm cảm giác mệt mỏi, uể oải buổi sáng.',
            downside: 'Thiếu nước từ đầu ngày dễ gây đau đầu nhẹ, giảm tập trung và tụt mood nhanh hơn.',
        },
        {
            id: 'morning_exercise',
            title: 'Tập thể dục buổi sáng',
            summary: 'Chỉ 10-15 phút vận động nhẹ cũng đủ kích hoạt năng lượng.',
            detailTitle: 'Lợi ích của vận động buổi sáng',
            importance: 'Vận động giúp tăng endorphin, cải thiện sự tỉnh táo và giảm lo âu nền trong ngày.',
            downside: 'Ít vận động lâu ngày làm cơ thể ì ạch, tinh thần trì trệ và dễ cáu gắt khi áp lực tăng.',
            route: ROUTE_PATHS.exercises,
        },
        {
            id: 'morning_breakfast',
            title: 'Nhắc nhớ ăn sáng dinh dưỡng',
            summary: 'Ăn sáng đủ đạm - chất xơ để ổn định đường huyết và mood.',
            detailTitle: 'Tầm quan trọng của bữa sáng',
            importance: 'Bữa sáng là nguồn năng lượng nền cho não, giúp bạn tập trung và giữ cảm xúc ổn định hơn cả buổi.',
            downside: 'Bỏ bữa sáng dễ tụt đường huyết, cáu gắt, giảm hiệu suất học tập/làm việc và ăn bù quá mức về sau.',
            route: ROUTE_PATHS.nutrition,
        },
    ],
    day: [
        {
            id: 'day_checkin',
            title: 'Check-in mood buổi trưa',
            summary: 'Dừng 1 phút để tự hỏi “mình đang ổn không?”.',
            detailTitle: 'Vì sao nên check-in giữa ngày?',
            importance: 'Giúp phát hiện sớm dấu hiệu quá tải để điều chỉnh nhịp làm việc trước khi kiệt sức vào cuối ngày.',
            downside: 'Không dừng lại kiểm tra bản thân dễ khiến căng thẳng dồn nén và bùng phát vào chiều tối.',
            route: ROUTE_PATHS.checkin,
        },
        {
            id: 'day_lunch',
            title: 'Nhắc nhở ăn trưa đầy đủ',
            summary: 'Ăn đủ chất để não có nhiên liệu cho nửa ngày còn lại.',
            detailTitle: 'Tầm quan trọng của bữa trưa',
            importance: 'Bữa trưa cân bằng giúp giữ năng lượng ổn định, duy trì sự tập trung và hiệu suất làm việc buổi chiều.',
            downside: 'Bỏ bữa hoặc ăn quá ít dễ gây mệt lả, khó tập trung, tăng nguy cơ đau đầu và stress.',
        },
        {
            id: 'day_nap',
            title: 'Nghỉ trưa ngắn để thư giãn',
            summary: 'Nghỉ 15-20 phút để đầu óc reset và có thêm năng lượng.',
            detailTitle: 'Tại sao nên nghỉ trưa ngắn?',
            importance: 'Một khoảng nghỉ ngắn giúp phục hồi sự chú ý, giảm quá tải nhận thức và làm việc hiệu quả hơn.',
            downside: 'Cố gồng liên tục khiến bạn đuối nhanh vào cuối chiều, dễ mất bình tĩnh và giảm chất lượng quyết định.',
        },
        {
            id: 'day_hydration_move',
            title: 'Uống đủ nước và đứng dậy vận động',
            summary: 'Nhắc bản thân rời ghế vài phút sau mỗi 45-60 phút.',
            detailTitle: 'Tác hại của việc ngồi quá lâu',
            importance: 'Đứng dậy vận động giúp máu lưu thông tốt hơn, giảm mỏi cơ và giữ tinh thần tỉnh táo.',
            downside: 'Ngồi nhiều liên tục làm đau lưng/cổ vai, giảm trao đổi chất, dễ mệt não và tụt năng lượng cuối ngày.',
        },
    ],
    evening: [
        {
            id: 'evening_dinner',
            title: 'Ăn tối nhẹ nhàng',
            summary: 'Ưu tiên bữa tối vừa đủ, dễ tiêu, không quá muộn.',
            detailTitle: 'Vì sao nên ăn tối nhẹ?',
            importance: 'Ăn tối vừa phải giúp hệ tiêu hóa nghỉ ngơi đúng nhịp và cải thiện chất lượng giấc ngủ đêm.',
            downside: 'Ăn tối quá nhiều dễ đầy bụng, khó ngủ sâu và sáng hôm sau uể oải, tâm trạng nặng nề hơn.',
        },
        {
            id: 'evening_relax',
            title: 'Thư giãn và ngồi thiền',
            summary: 'Dành 5-10 phút hạ nhịp căng thẳng trước giờ ngủ.',
            detailTitle: 'Lợi ích của thư giãn buổi tối',
            importance: 'Thiền/thở chậm giúp hệ thần kinh hạ kích hoạt, giảm lo âu và đưa cơ thể vào trạng thái nghỉ.',
            downside: 'Nếu không hạ nhịp trước ngủ, não vẫn căng và bạn dễ trằn trọc hoặc thức giấc giữa đêm.',
            route: `${ROUTE_PATHS.exercises}?type=meditation&id=evening_winddown`,
        },
        {
            id: 'evening_sleep',
            title: 'Ngủ sớm trước 11PM',
            summary: 'Giấc ngủ đúng giờ giúp phục hồi cảm xúc bền vững.',
            detailTitle: 'Tầm quan trọng của việc ngủ sớm',
            importance: 'Ngủ trước 23h hỗ trợ điều hòa hormone stress, cải thiện trí nhớ và độ ổn định cảm xúc hôm sau.',
            downside: 'Ngủ muộn kéo dài làm tăng mệt mỏi, giảm tập trung và dễ cáu gắt trong ngày kế tiếp.',
        },
        {
            id: 'evening_snack',
            title: 'Hạn chế ăn vặt buổi tối',
            summary: 'Tránh đồ ngọt/mặn muộn để cơ thể nghỉ ngơi tốt hơn.',
            detailTitle: 'Tại sao nên tránh ăn vặt buổi tối?',
            importance: 'Giảm ăn vặt tối giúp ngủ ngon hơn và giữ nhịp năng lượng ổn định vào sáng hôm sau.',
            downside: 'Ăn vặt đêm dễ gây rối loạn tiêu hóa, tăng đường huyết dao động và khiến tâm trạng sáng sau kém ổn định.',
        },
    ],
}

function getCurrentTimeSlot(hour: number): TimeSlot {
    if (hour >= 5 && hour < 10) return 'morning'
    if (hour >= 10 && hour < 18) return 'day'
    return 'evening'
}

export default function Home() {
    const navigate = useNavigate()
    const { user } = useAuth()
    const [quote, setQuote] = useState<{ text: string; author?: string | null } | null>(null)
    const [rewardProgress, setRewardProgress] = useState(() => getRewardProgress())
    const hearts = rewardProgress.hearts
    const streak = rewardProgress.streakDays
    const [wellnessScores, setWellnessScores] = useState<WellnessScores | null>(null)
    const [nutritionTip, setNutritionTip] = useState<NutritionDailyTip | null>(null)
    const [homeMoodWords, setHomeMoodWords] = useState<string[]>([])
    const currentHour = new Date().getHours()
    const currentSlot = useMemo<TimeSlot>(() => getCurrentTimeSlot(currentHour), [currentHour])
    const currentReminders = useMemo(() => SLOT_REMINDERS[currentSlot], [currentSlot])
    const [selectedReminderId, setSelectedReminderId] = useState<string>(currentReminders[0]?.id ?? '')
    const [detailReminderId, setDetailReminderId] = useState<string | null>(null)
    const detailReminder = useMemo(
        () => currentReminders.find((item) => item.id === detailReminderId) ?? null,
        [currentReminders, detailReminderId],
    )
    const responsive = {
        superLargeDesktop: {
            // the naming can be any, depends on you.
            breakpoint: { max: 4000, min: 3000 },
            items: 5
        },
        desktop: {
            breakpoint: { max: 3000, min: 1024 },
            items: 3
        },
        tablet: {
            breakpoint: { max: 1024, min: 464 },
            items: 2
        },
        mobile: {
            breakpoint: { max: 464, min: 0 },
            items: 1
        }
    };

    const quotes = ((quotesJson as unknown) as { quotes?: Array<{ id: string; content_vi?: string; content_en?: string; author?: string }> }).quotes ?? []

    useEffect(() => {
        if (!user) {
            return
        }

        let mounted = true
        homeService
            .feed()
            .then((data) => {
                if (!mounted) return
                setQuote(data.quote_of_day)
            })
            .catch(() => undefined)
        dashboardService
            .getNutritionDailyTip()
            .then((data) => {
                if (!mounted) return
                setNutritionTip(data)
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
                setRewardProgress(syncRewardStreak(streak30))
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
    }, [user])

    useEffect(() => {
        const onRewardUpdated = (event: Event) => {
            const custom = event as CustomEvent<{ hearts: number; streakDays: number }>
            if (custom.detail) {
                setRewardProgress(custom.detail)
            }
        }
        const onStorage = (event: StorageEvent) => {
            if (event.key) {
                setRewardProgress(getRewardProgress())
            }
        }

        window.addEventListener(REWARD_UPDATED_EVENT, onRewardUpdated as EventListener)
        window.addEventListener('storage', onStorage)
        return () => {
            window.removeEventListener(REWARD_UPDATED_EVENT, onRewardUpdated as EventListener)
            window.removeEventListener('storage', onStorage)
        }
    }, [])
    useEffect(() => {
        if (currentReminders.some((item) => item.id === selectedReminderId)) return
        const newId = currentReminders[0]?.id ?? ''
        if (newId !== selectedReminderId) {
            setSelectedReminderId(newId)
        }
    }, [currentReminders, selectedReminderId])

    const displayName = user?.displayName || 'bạn'

    return (
        <div className="space-y-6 pb-8 lg:space-y-8">

            {/* ── Greeting header ── */}
            <header className="flex items-start justify-between gap-4">
                <div>
                    <p className="text-sm font-medium uppercase tracking-wide text-white">
                        {getGreeting()}
                    </p>
                    <h1 className="mt-1 font-display text-3xl italic text-white sm:text-4xl">
                        {displayName}
                    </h1>
                </div>
                <div className="flex items-center gap-3 rounded-full border border-white/30 bg-white/20 px-4 py-2 backdrop-blur-sm">
                    <span className="flex items-center gap-1 text-sm font-semibold text-rose-500">
                        <Heart className="h-4 w-4 fill-current" />
                        {hearts}
                    </span>
                    <span className="h-4 w-px bg-white/30" />
                    <span className="flex items-center gap-1 text-sm font-semibold text-amber-400">
                        <Flame className="h-4 w-4 fill-current" />
                        {streak}
                    </span>
                </div>
            </header>

            {/* ── Today's plan + streak ── */}
            <section className="rounded-[28px] border border-white/35 bg-white/55 p-6 backdrop-blur-xl">
                <div className="mb-4 flex items-center justify-between">
                    <h2 className="font-display text-[1.6rem] text-serene-ink">Hôm nay của bạn</h2>
                    <span className="rounded-full bg-serene-primary/10 px-3 py-1 text-xs font-semibold text-serene-primary">
                        {TIME_SLOT_META[currentSlot].label} · {TIME_SLOT_META[currentSlot].range}
                    </span>
                </div>
                <p className="mb-4 text-sm text-serene-muted">{TIME_SLOT_META[currentSlot].intro}</p>

                <div className="space-y-3">
                    {currentReminders.map((item) => {
                        const active = selectedReminderId === item.id
                        return (
                            <button
                                key={item.id}
                                type="button"
                                onClick={() => {
                                    setSelectedReminderId(item.id)
                                    setDetailReminderId(item.id)
                                }}
                                className={[
                                    'flex w-full items-center gap-3 rounded-2xl p-4 text-left transition active:scale-[0.98]',
                                    active
                                        ? 'border border-serene-primary/30 bg-serene-primary/10'
                                        : 'border border-transparent bg-white/60 hover:bg-white/80',
                                ].join(' ')}
                            >
                                <Info className={`h-5 w-5 shrink-0 ${active ? 'text-serene-primary' : 'text-serene-outline'}`} />
                                <div className="min-w-0 flex-1">
                                    <p className="text-sm font-semibold text-serene-ink">{item.title}</p>
                                    <p className="mt-0.5 text-xs text-serene-muted">{item.summary}</p>
                                </div>
                                <ChevronRight className={`h-4 w-4 ${active ? 'text-serene-primary' : 'text-serene-muted'}`} />
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

            <section className="rounded-[28px] border border-white/35 bg-white/55 p-6 backdrop-blur-xl">
                <h2 className="mb-4 font-display text-2xl text-serene-ink">Tâm trạng hôm nay?</h2>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                        <MoodWordChips selected={homeMoodWords} onChange={setHomeMoodWords} />
                        {homeMoodWords.length > 0 && (
                            <button
                                type="button"
                                onClick={() =>
                                    navigate(ROUTE_PATHS.checkin, { state: { moodWords: homeMoodWords } })
                                }
                                className="mt-4 text-sm font-medium text-serene-primary underline underline-offset-4 transition hover:opacity-70"
                            >
                                Ghi chép thêm →
                            </button>
                        )}
                    </div>

                    <div className="flex items-center justify-center">
                        <div className="w-full">
                            <Carousel.default
                                responsive={responsive}
                                infinite
                                autoPlay
                                autoPlaySpeed={4500}
                                showDots
                                arrows={false}
                            >
                                {quotes.slice(0, 8).map((q) => (
                                    <div key={q.id} className="px-3">
                                        <div className="rounded-2xl border border-white/20 bg-white/10 p-6 text-left">
                                            <blockquote className="font-display text-lg italic text-serene-on-primary">
                                                {q.content_vi || q.content_en}
                                            </blockquote>
                                            <p className="mt-3 text-xs uppercase tracking-[0.18em] text-serene-on-primary/70">
                                                {q.author || 'Không rõ'}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </Carousel.default>
                        </div>
                    </div>
                </div>
            </section>

            <button
                type="button"
                onClick={() => navigate(ROUTE_PATHS.nutrition)}
                className="w-full rounded-[28px] border border-white/35 bg-white/55 p-6 text-left backdrop-blur-xl transition hover:bg-white/70 active:scale-[0.99]"
            >
                <p className="text-xs uppercase tracking-[0.22em] text-serene-muted">Hôm nay ăn gì</p>
                <h2 className="mt-2 font-display text-2xl text-serene-ink">
                    {nutritionTip?.dish || 'Yến mạch + trái cây + hạt'}
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-serene-muted">
                    {nutritionTip?.benefit || 'Bữa ăn đủ đạm và chất xơ giúp ổn định mood, giảm cảm giác tụt năng lượng.'}
                </p>
            </button>

            {/* ── Quick action grid 2×2 ── */}
            <section>
                <h2 className="mb-4 font-display text-3xl text-white">Bắt đầu từ đây</h2>
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
                className="group w-full rounded-3xl border border-white/25 bg-serene-primary/85 p-6 text-left backdrop-blur-xl transition hover:bg-serene-primary/95 active:scale-[0.99]"
            >
                <div className="flex items-center justify-between gap-4">
                    <div className="flex-1">
                        <p className="text-xs uppercase tracking-[0.22em] text-serene-accent/80">
                            Nhìn Lại · Tiến trình tuần này
                        </p>
                        <h3 className="mt-1.5 font-display text-2xl text-serene-on-primary">
                            6 chiều sức khoẻ
                        </h3>

                        <ArrowRight className="mt-3 h-5 w-5 text-serene-on-primary/50 transition group-hover:translate-x-1" />
                    </div>
                    <div className="shrink-0">
                        {wellnessScores ? (
                            <WellnessRadar scores={wellnessScores} mini />
                        ) : (
                            <div className="flex h-39 w-32 items-center justify-center rounded-2xl bg-white/10">
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
                    <h2 className="font-display text-3xl text-white">Dành cho bạn</h2>
                    <button
                        type="button"
                        onClick={() => navigate(ROUTE_PATHS.exercises)}
                        className="font-medium text-white underline underline-offset-4 transition hover:text-white/50"
                    >
                        Xem tất cả
                    </button>
                </div>
                <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
                    {RECO_CARDS.map((card) => {
                        return (
                            <button
                                key={card.label}
                                type="button"
                                onClick={() => navigate(card.route)}
                                className="flex min-w-37 shrink-0 flex-col gap-3 rounded-[22px] border border-white/35 bg-white/50 p-4 text-left backdrop-blur-xl transition hover:bg-white/70 active:scale-[0.97]"
                            >
                                <div className={`inline-flex h-12 w-12 items-center justify-center rounded-xl text-xl ${card.accentClass}`}>
                                    {card.emoji}
                                </div>
                                <div>
                                    <p className="text-sm font-semibold text-serene-ink leading-tight">{card.label}</p>
                                    <p className="mt-1 text-xs text-serene-muted">{card.desc}</p>
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

            {detailReminder && (
                <div className="fixed inset-0 z-70 flex items-center justify-center bg-black/35 px-4">
                    <article className="w-full max-w-lg rounded-3xl border border-white/40 bg-white p-5 shadow-2xl">
                        <div className="flex items-start justify-between gap-4">
                            <p className="text-base font-semibold text-serene-ink">{detailReminder.detailTitle}</p>
                            <button
                                type="button"
                                aria-label="Đóng thông tin"
                                onClick={() => setDetailReminderId(null)}
                                className="rounded-full border border-serene-outline/25 p-1.5 text-serene-muted transition hover:bg-serene-ink/5 hover:text-serene-ink"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>
                        <p className="mt-3 text-sm leading-relaxed text-serene-muted">
                            <span className="font-semibold text-serene-ink">Tầm quan trọng:</span>{' '}
                            {detailReminder.importance}
                        </p>
                        <p className="mt-2 text-sm leading-relaxed text-serene-muted">
                            <span className="font-semibold text-serene-ink">Nếu bỏ qua:</span>{' '}
                            {detailReminder.downside}
                        </p>
                        {detailReminder.route ? (
                            <button
                                type="button"
                                onClick={() => {
                                    navigate(detailReminder.route as string)
                                    setDetailReminderId(null)
                                }}
                                className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-serene-primary hover:underline"
                            >
                                Mở nội dung liên quan <ArrowRight className="h-3.5 w-3.5" />
                            </button>
                        ) : null}
                    </article>
                </div>
            )}
        </div>
    )
}
