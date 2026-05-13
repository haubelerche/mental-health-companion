import {
    ArrowRight,
    ChevronLeft,
    Flame,
    Heart,
    Wind,
    Leaf,
    Info,
    ChevronRight,
    X,
    CalendarCheck,
    Moon,
    Activity,
    Gift,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import quotesJson from '../../../famous-quotes.json'
import beachMessageBg from '../../assets/motion/landing-rain.gif'
import exerciseImg from '../../assets/motion/fishing.gif'
import morningRhythmImg from '../../assets/motion/serene-landing-day-welcome.gif'
import dayRhythmImg from '../../assets/motion/afternoon-serene-bamboo-page.gif'
import eveningRhythmImg from '../../assets/motion/serene-landing-night-welcome.gif'
import healingImg from '../../assets/motion/calmness.gif'
import { Link, useNavigate } from 'react-router-dom'
import { homeService } from '../../services/homeService'
import { rewardsService } from '../../services/rewardsService'
import { ROUTE_PATHS } from '../../routes/paths'
import { CheckinHistoryModal } from '../dashboard/CheckinHistoryModal'
import { MoodWordChips } from '../common/MoodWordChips'
import { StreakBar } from '../common/StreakBar'
import { useAuth } from '../../hooks/useAuth'
import { dashboardService, type NutritionDailyTip } from '../../services/dashboardService'
import { useThemeContext } from '../../contexts/ThemeContext'
import { REWARD_UPDATED_EVENT } from '../../utils/rewardProgress'
import Mascot from '../pixel/Mascot'

type RecoCard = {
    icon: typeof Wind
    label: string
    desc: string
    route: string
    accentClass: string
    cardClass: string
}

const getRecoCards = (hour: number, isDark: boolean): RecoCard[] => {
    const isMorning = hour >= 5 && hour < 16

    return [
    {
        icon: Wind,
        label: 'Bài hít thở 4-4-4',
        desc: '3 phút · Giảm lo âu',
        route: `${ROUTE_PATHS.exercises}?exercise=box_breath`,
        accentClass: isDark
            ? 'bg-emerald-500/12 text-emerald-200 border border-emerald-200'
            : 'bg-emerald-100 text-emerald-800 border border-emerald-500',
        cardClass: isDark
            ? 'bg-emerald-950/18 border border-emerald-800/20'
            : 'bg-emerald-50/90 border border-emerald-500/60',
    },
    {
        icon: isMorning ? Leaf : Moon,
        label: isMorning ? 'Thiền buổi sáng' : 'Thiền trước ngủ',
        desc: isMorning
            ? '5 phút · Bắt đầu ngày mới'
            : '10 phút · Dễ đi vào giấc ngủ',
        route: isMorning
            ? `${ROUTE_PATHS.exercises}?type=meditation&id=morning_5`
            : `${ROUTE_PATHS.exercises}?type=meditation&id=sleep_deep`,
        accentClass: isDark
            ? 'bg-violet-500/12 text-violet-200 border border-violet-200'
            : 'bg-violet-100 text-violet-800 border border-violet-500',
        cardClass: isDark
            ? 'bg-violet-950/18 border border-violet-800/20'
            : 'bg-violet-50/90 border border-violet-500/60',
    },
    {
        icon: CalendarCheck,
        label: isMorning ? 'Check-in buổi sáng' : 'Check-in buổi tối',
        desc: isMorning
            ? 'Khởi đầu ngày tỉnh thức'
            : 'Nhìn lại ngày hôm nay',
        route: `${ROUTE_PATHS.checkin}?variant=${isMorning ? 'morning' : 'evening'}`,
        accentClass: isDark
            ? 'bg-amber-500/12 text-amber-100 border border-amber-200'
            : 'bg-amber-100 text-amber-900 border border-amber-500',
        cardClass: isDark
            ? 'bg-amber-950/18 border border-amber-800/20'
            : 'bg-amber-50/90 border border-amber-500/60',
    },
      {
        icon: Gift,
        label: "Cửa hàng vật phẩm",
        desc: 'Đổi quà bằng điểm nỗ lực',
        route: `${ROUTE_PATHS.rewards}`,
        accentClass: isDark
            ? 'bg-pink-500/12 text-pink-100 border border-pink-200'
            : 'bg-pink-100 text-pink-900 border border-pink-500',
        cardClass: isDark
            ? 'bg-pink-950/18 border border-pink-800/20'
            : 'bg-pink-50/90 border border-pink-500/60',
    },
]

}

const SEVERITY_LABELS: Record<string, string> = {
  minimal: 'Rất nhẹ',
  mild: 'Nhẹ',
  moderate: 'Trung bình',
  moderately_severe: 'Khá cao',
  severe: 'Cao',
}

const SEVERITY_COLORS: Record<string, string> = {
  minimal: '#4caf50',
  mild: '#8bc34a',
  moderate: '#ff9800',
  moderately_severe: '#e57373',
  severe: '#c62828',
}

const getCombinedInsight = (phq9?: string, gad7?: string) => {
  if (phq9 === 'minimal' && gad7 === 'minimal') {
    return 'Tâm trạng và mức độ lo âu của bạn đang ở trạng thái rất tốt. Hãy tiếp tục duy trì lối sống lành mạnh!'
  }
  if ((phq9 === 'moderate' || phq9 === 'severe') && (gad7 === 'moderate' || gad7 === 'severe')) {
    return 'Bạn đang có dấu hiệu căng thẳng và mệt mỏi khá cao. Hãy cân nhắc trò chuyện với Serene hoặc tìm kiếm sự hỗ trợ từ chuyên gia.'
  }
  return 'Có một vài biến động nhỏ trong tâm trạng hoặc lo âu. Hãy chú ý lắng nghe cơ thể và dành thời gian thư giãn nhiều hơn.'
}

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

const TIME_SLOT_BG: Record<TimeSlot, string> = {
    morning: morningRhythmImg,
    day: dayRhythmImg,
    evening: eveningRhythmImg,
}

export default function Home() {
    const navigate = useNavigate()
    const { user } = useAuth()
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const [quote, setQuote] = useState<{ text: string; author?: string | null } | null>(null)
    const [hearts, setHearts] = useState<number | null>(null)
    const [backendStreakDays, setBackendStreakDays] = useState<number | null>(null)
    const [isTodayCompleted, setIsTodayCompleted] = useState<boolean>(false)
    const [completedDays, setCompletedDays] = useState<number[]>([])
    const [checkinHistoryOpen, setCheckinHistoryOpen] = useState(false)
    const streak = backendStreakDays ?? 0
    const [nutritionTip, setNutritionTip] = useState<NutritionDailyTip | null>(null)
    const [homeMoodWords, setHomeMoodWords] = useState<string[]>([])
    const [quoteIndex, setQuoteIndex] = useState(0)
    
    const [phq9Result, setPhq9Result] = useState<{ raw_score: number, severity_label: string } | null>(null)
    const [gad7Result, setGad7Result] = useState<{ raw_score: number, severity_label: string } | null>(null)

    useEffect(() => {
        const phq9 = localStorage.getItem('serene_screening_phq9')
        const gad7 = localStorage.getItem('serene_screening_gad7')
        if (phq9) setPhq9Result(JSON.parse(phq9))
        if (gad7) setGad7Result(JSON.parse(gad7))
    }, [])
    const [currentHour, setCurrentHour] = useState(() => new Date().getHours())
    const recoCards = useMemo(() => getRecoCards(currentHour, isDark), [currentHour, isDark])
    const currentSlot = useMemo<TimeSlot>(() => getCurrentTimeSlot(currentHour), [currentHour])

    const currentReminders = useMemo(() => SLOT_REMINDERS[currentSlot], [currentSlot])
    const [selectedReminderId, setSelectedReminderId] = useState<string>(currentReminders[0]?.id ?? '')
    const [detailReminderId, setDetailReminderId] = useState<string | null>(null)
    const detailReminder = useMemo(
        () => currentReminders.find((item) => item.id === detailReminderId) ?? null,
        [currentReminders, detailReminderId],
    )
    const quotes = ((quotesJson as unknown) as { quotes?: Array<{ id: string; content_vi?: string; content_en?: string; author?: string }> }).quotes ?? []
    const activeQuote = quotes.length > 0 ? quotes[quoteIndex % quotes.length] : null
    const quoteContent = activeQuote?.content_vi || activeQuote?.content_en || quote?.text || 'Giây phút hiện tại là nơi duy nhất sự sống thực sự tồn tại.'
    const quoteAuthor = activeQuote?.author || quote?.author || 'Thích Nhất Hạnh'

    useEffect(() => {
        const tick = () => setCurrentHour(new Date().getHours())
        const id = window.setInterval(tick, 60_000)
        const onVisible = () => {
            if (document.visibilityState === 'visible') tick()
        }
        document.addEventListener('visibilitychange', onVisible)
        return () => {
            window.clearInterval(id)
            document.removeEventListener('visibilitychange', onVisible)
        }
    }, [])

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
        rewardsService
            .getBalance()
            .then((data) => {
                if (!mounted) return
                setHearts(data.balance)
            })
            .catch(() => undefined)

        dashboardService
            .getReflectSummary()
            .then((data) => {
                if (!mounted) return
                setBackendStreakDays(data.progress.streak_days ?? 0)
                setIsTodayCompleted(data.progress.is_today_completed ?? false)
                setCompletedDays(data.progress.completed_days ?? [])

            })
            .catch(() => undefined)

        return () => {
            mounted = false
        }
    }, [user])

    useEffect(() => {
        const onRewardUpdated = (event: Event) => {
            const custom = event as CustomEvent<{ balance: number }>
            if (custom.detail?.balance !== undefined) {
                setHearts(custom.detail.balance)
            }
        }

        window.addEventListener(REWARD_UPDATED_EVENT, onRewardUpdated as EventListener)
        return () => {
            window.removeEventListener(REWARD_UPDATED_EVENT, onRewardUpdated as EventListener)
        }
    }, [])

    useEffect(() => {
        if (quotes.length <= 1) return

        const timer = window.setInterval(() => {
            setQuoteIndex((current) => (current + 1) % quotes.length)
        }, 5000)

        return () => window.clearInterval(timer)
    }, [quotes.length])

    const displayName = user?.displayName || 'bạn'
    const effectiveSelectedReminderId = currentReminders.some((item) => item.id === selectedReminderId)
        ? selectedReminderId
        : currentReminders[0]?.id ?? ''

    return (
        <div className="relative min-h-screen overflow-hidden ">
            <CheckinHistoryModal open={checkinHistoryOpen} onClose={() => setCheckinHistoryOpen(false)} isDark={isDark} />
            <div className="space-y-6 pb-8 lg:space-y-8">
                {/* ── Greeting header ── */}
                <header className="flex items-start justify-between gap-4">
                    <div className="flex min-w-0 items-center gap-3">
                        <Mascot
                            variant="main"
                            size="lg"
                            decorative
                            className="hidden sm:block"
                        />
                        <h1 className={`mt-1 font-display text-2xl italic ${isDark ? 'text-theme-text-primary' : 'text-white'} sm:text-4xl`}>
                            {getGreeting()}! {displayName}
                        </h1>
                    </div>
                    <div data-tour-id="heart-balance" className="flex items-center gap-3 rounded-full bg-theme-surface/80 px-4 py-2 backdrop-blur-sm border border-theme-border/50 shadow-sm">
                        <span className="flex items-center gap-1 text-sm font-bold text-rose-500 dark:text-rose-400">
                            <Heart className="h-4 w-4 fill-current" />
                            {hearts === null ? (
                                <span className="h-3 w-6 bg-theme-accent/50 animate-pulse rounded-full" />
                            ) : (
                                hearts
                            )}
                        </span>
                        <span className="h-4 w-px bg-theme-secondary" />
                        <span className="flex items-center gap-1 text-sm font-bold text-amber-600 dark:text-amber-400">
                            <Flame className="h-4 w-4 fill-current" />
                            {backendStreakDays === null ? (
                                <span className="h-3 w-6 bg-theme-accent/50 animate-pulse rounded-full" />
                            ) : (
                                streak
                            )}
                        </span>
                    </div>
                </header>

                {/* ── Today's plan + streak ── */}
                <section data-tour-id="home-today-card" className="rounded-[2.5rem] bg-theme-surface/60 p-6 backdrop-blur-3xl border border-theme-border/50 shadow-sm">
                    <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-stretch">
                        <div>
                            <div className="mb-5 flex items-center justify-between gap-4">
                                <h2 className="font-display text-3xl text-theme-text-primary">Nhịp sống hôm nay</h2>
                                <span className="rounded-full bg-theme-accent px-3 py-1 text-sm font-semibold text-white/90">
                                    {TIME_SLOT_META[currentSlot].label} · {TIME_SLOT_META[currentSlot].range}
                                </span>
                            </div>


                            <div className="space-y-3">
                                {currentReminders.map((item) => {
                                    const active = effectiveSelectedReminderId === item.id
                                    return (
                                        <button
                                            key={item.id}
                                            type="button"
                                            onClick={() => {
                                                setSelectedReminderId(item.id)
                                                setDetailReminderId(item.id)
                                            }}
                                            className={[
                                                'flex w-full items-center gap-3 rounded-2xl p-4 text-left transition active:scale-[0.98] cursor-pointer border',
                                                active
                                                    ? 'bg-theme-accent/20 border-theme-accent/30'
                                                    : 'bg-theme-surface/60 hover:bg-theme-accent/10 border-theme-border/30',
                                            ].join(' ')}
                                        >
                                            <Info className={`h-5 w-5 shrink-0 ${active ? 'text-theme-accent' : 'text-theme-text-secondary'}`} />
                                            <div className="min-w-0 flex-1">
                                                <p className="text-lg font-semibold text-theme-text-primary">{item.title}</p>
                                                <p className="mt-0.5 text-sm text-theme-text-secondary">{item.summary}</p>
                                            </div>
                                            <ChevronRight className={`h-4 w-4 ${active ? 'text-theme-accent' : 'text-theme-text-secondary/60'}`} />
                                        </button>
                                    )
                                })}
                            </div>

                            <div className="mt-5 border-t border-theme-border/50 pt-5">
                                <button
                                    type="button"
                                    onClick={() => setCheckinHistoryOpen(true)}
                                    className="mb-3 cursor-pointer inline-flex items-center gap-2 text-left text-sm font-semibold uppercase tracking-[0.22em] text-theme-text-secondary underline-offset-4 hover:underline"
                                >
                                    Chuỗi tuần này <ChevronRight className="h-5 w-5 text-theme-text-secondary/60" />
                                </button>
                                {backendStreakDays === null ? (
                                    <div className="flex items-center justify-between">
                                        {/* skeleton */}
                                        {Array.from({ length: 7 }).map((_, index) => (
                                            <div
                                                key={index}
                                                className="flex h-10 w-10 animate-pulse rounded-full bg-theme-accent/50"
                                            />
                                        ))}
                                    </div>
                                ) : (
                                    <StreakBar streak={streak} isTodayCompleted={isTodayCompleted} completedDays={completedDays} />
                                )}
                            </div>
                        </div>

                        <div className="relative overflow-hidden rounded-[26px] min-h-[280px] shadow-xl">
                            <img
                                src={TIME_SLOT_BG[currentSlot]}
                                alt="Khung cảnh thiên nhiên dịu nhẹ cho phần nhịp hôm nay"
                                className="absolute inset-0 h-full w-full object-cover "
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-black/20 to-transparent" />
                            <div className="absolute inset-x-0 bottom-0 p-4 text-white">
                                <p className="text-lg uppercase tracking-[0.22em] text-white">Khoảnh khắc hiện tại</p>
                                <p className="mt-2 text-lg font-semibold">{TIME_SLOT_META[currentSlot].label}</p>
                                <p className="mt-1 text-sm leading-relaxed text-white/90">{TIME_SLOT_META[currentSlot].intro}</p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* ── Monitor Bài Test ── */}
                <section className="bg-theme-surface/60 p-6 rounded-4xl backdrop-blur-xl border border-theme-border/50 shadow-sm">
                    <div className="flex items-center justify-between gap-4 mb-5">
                        <div>
                            <h2 className="font-display text-3xl text-theme-primary">Giám sát sức khỏe</h2>
                            <p className="mt-1 text-theme-secondary">
                                Kết quả đánh giá gần nhất của bạn
                            </p>
                        </div>
                        <Activity className="h-6 w-6 text-theme-accent" />
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2">
                        {/* PHQ-9 */}
                        <div className="bg-theme-surface/40 p-5 rounded-xl border-2  border-theme-secondary  flex flex-col justify-between min-h-[160px] relative">
                            <div>
                                <div className="flex justify-between items-center mb-2">
                                    <h3 className="text-sm uppercase tracking-wider text-theme-text-primary flex items-center gap-2 font-bold">
                                        MÔ-ĐUN: PHQ-9
                                    </h3>
                                    <span className="text-xs text-theme-text-secondary">TÂM TRẠNG</span>
                                </div>
                                {phq9Result ? (
                                    <div className="mt-2">
                                        <div className="flex items-baseline gap-1">
                                            <span className="text-4xl font-bold text-theme-accent">
                                                {phq9Result.raw_score.toString().padStart(2, '0')}
                                            </span>
                                            <span className="text-lg text-theme-text-secondary">/27</span>
                                        </div>
                                        <p className="text-xs uppercase mt-2 font-semibold" style={{ color: SEVERITY_COLORS[phq9Result.severity_label] }}>
                                            TRẠNG THÁI: {SEVERITY_LABELS[phq9Result.severity_label]?.toUpperCase() || phq9Result.severity_label.toUpperCase()}
                                        </p>
                                        <div className="w-full bg-theme-border/20 h-1.5 mt-2 rounded-full overflow-hidden">
                                            <div 
                                                className="h-full" 
                                                style={{ 
                                                    width: `${(phq9Result.raw_score / 27) * 100}%`,
                                                    backgroundColor: SEVERITY_COLORS[phq9Result.severity_label]
                                                }}
                                            />
                                        </div>
                                    </div>
                                ) : (
                                    <div className="mt-4 text-sm text-theme-text-secondary">
                                        &gt; KHÔNG CÓ DỮ LIỆU
                                        <br />
                                        &gt; HỆ THỐNG YÊU CẦU KIỂM TRA
                                    </div>
                                )}
                            </div>
                            {!phq9Result && (
                                <Link to={ROUTE_PATHS.screening} className="text-xs text-theme-accent hover:underline mt-2 inline-block">
                                    &gt; BẮT ĐẦU ĐÁNH GIÁ
                                </Link>
                            )}
                            {phq9Result && (
                                <Link to={ROUTE_PATHS.screening} className="text-sm text-theme-accent hover:underline mt-2 inline-block absolute bottom-2 right-2">
                                    Thử làm lại
                                </Link>
                            )}
                        </div>

                        {/* GAD-7 */}
                        <div className="bg-theme-surface/40 p-5 rounded-xl border-2  border-theme-secondary  flex flex-col justify-between min-h-[160px] relative">
                            <div>
                                <div className="flex justify-between items-center mb-2">
                                    <h3 className="text-sm uppercase tracking-wider text-theme-text-primary flex items-center gap-2 font-bold">
                                        MÔ-ĐUN: GAD-7
                                    </h3>
                                    <span className="text-xs text-theme-text-secondary">LO ÂU</span>
                                </div>
                                {gad7Result ? (
                                    <div className="mt-2">
                                        <div className="flex items-baseline gap-1">
                                            <span className="text-4xl font-bold text-theme-accent">
                                                {gad7Result.raw_score.toString().padStart(2, '0')}
                                            </span>
                                            <span className="text-lg text-theme-text-secondary">/21</span>
                                        </div>
                                        <p className="text-xs uppercase mt-2 font-semibold" style={{ color: SEVERITY_COLORS[gad7Result.severity_label] }}>
                                            TRẠNG THÁI: {SEVERITY_LABELS[gad7Result.severity_label]?.toUpperCase() || gad7Result.severity_label.toUpperCase()}
                                        </p>
                                        <div className="w-full bg-theme-border/20 h-1.5 mt-2 rounded-full overflow-hidden">
                                            <div 
                                                className="h-full" 
                                                style={{ 
                                                    width: `${(gad7Result.raw_score / 21) * 100}%`,
                                                    backgroundColor: SEVERITY_COLORS[gad7Result.severity_label]
                                                }}
                                            />
                                        </div>
                                    </div>
                                ) : (
                                    <div className="mt-4 text-sm text-theme-text-secondary">
                                        &gt; KHÔNG CÓ DỮ LIỆU
                                        <br />
                                        &gt; HỆ THỐNG YÊU CẦU KIỂM TRA
                                    </div>
                                )}
                            </div>
                            {!gad7Result && (
                                <Link to={ROUTE_PATHS.screening} className="text-sm text-theme-accent hover:underline mt-2 inline-block">
                                    Làm test ngay
                                </Link>
                            )}
                            {gad7Result && (
                                <Link to={ROUTE_PATHS.screening} className="text-sm text-theme-accent hover:underline mt-2 inline-block absolute bottom-2 right-2">
                                    Thử làm lại
                                </Link>
                            )}
                        </div>
                    </div>

                    {(phq9Result || gad7Result) && (
                        <div className="mt-4 p-4 bg-theme-surface/30 rounded-xl border border-theme-border/20 text-sm text-theme-text-secondary">
                            <span className="font-bold text-theme-accent">Insight:</span>{' '}
                            {getCombinedInsight(phq9Result?.severity_label, gad7Result?.severity_label)}
                        </div>
                    )}
                </section>

                {/* ── Gợi ý nhẹ nhàng ── */}
                <section className="bg-theme-surface/60 p-6 rounded-4xl backdrop-blur-xl border border-theme-border/50 shadow-sm">

                    <div className="flex items-center justify-between gap-4">
                        <div>
                            <h2 className="font-display text-3xl text-theme-text-primary">Gợi ý nhẹ nhàng</h2>
                            <p className="mt-2 text-xs lg:text-base  text-theme-text-secondary">
                                Chọn một lối vào ngắn, nhẹ và đúng nhu cầu hiện tại để bạn bắt đầu nhanh hơn.
                            </p>
                        </div>
                    </div>

                    <Link
                        to={ROUTE_PATHS.screening}
                        className="relative block overflow-hidden rounded-[24px] min-h-[300px] shadow-lg mt-5 transition-transform hover:scale-[1.01]"
                    >
                        <img
                            src={exerciseImg}
                            alt="Một hình minh họa cho các gợi ý bắt đầu nhanh"
                            className={`absolute inset-0 h-full w-full object-cover ${isDark ? 'brightness-75' : ''}`}
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-black/30 to-transparent" />
                        <div className="absolute inset-x-0 bottom-0 p-5 text-white">
                            <p className="text-sm font-bold uppercase tracking-[0.2em] text-theme-text-secondary">Làm bài test sức khỏe tinh thần</p>
                            <p className="mt-1 text-sm ">Một chạm là có thể bắt đầu ngay</p>
                        </div>
                    </Link>

                    <div className="flex gap-4 mt-5 flex-wrap">
                        {recoCards.map((card) => {
                            const RecoIcon = card.icon
                            return (
                                <button
                                    key={card.label}
                                    type="button"
                                    onClick={() => navigate(card.route)}
                                    className={`cursor-pointer flex min-w-[148px] shrink-0 flex-col gap-3 rounded-[22px] p-4 text-left border backdrop-blur-xl transition-all hover:scale-105 active:scale-[0.97] ${card.cardClass}`}
                                >
                                    <div className={`inline-flex h-12 w-12 items-center justify-center rounded-xl ${card.accentClass}`}>
                                        <RecoIcon className="h-6 w-6" aria-hidden />
                                    </div>
                                    <div>
                                        <p className=" font-semibold text-theme-text-primary leading-tight">{card.label}</p>
                                        <p className="mt-1 text-sm text-theme-text-secondary">{card.desc}</p>
                                    </div>
                                </button>
                            )
                        })}
                    </div>
                </section>

                <section data-tour-id="mood-checkin-card" className="rounded-4xl bg-theme-surface/60 p-6 backdrop-blur-xl border border-theme-border/50 shadow-sm">
                    <div className="grid gap-6 lg:grid-cols-2 lg:items-stretch">
                        <div>
                            <p className="font-semibold uppercase tracking-[0.2em] text-theme-text-primary">Bạn đang cảm thấy thế nào?</p>
                            <p className="mt-2 max-w-xl text-sm leading-relaxed text-theme-text-secondary">
                                Chọn 1-3 từ mô tả điều đang diễn ra bên trong bạn. Những từ nhỏ cũng đủ giúp bạn nhìn rõ mình hơn.
                            </p>

                            <div className="mt-4">
                                <div className="relative h-full overflow-hidden rounded-[22px] min-h-[200px]">
                                    <img
                                        src={healingImg}
                                        alt="Không gian chữa lành dịu nhẹ cho phần chọn từ mô tả tâm trạng"
                                        className={`absolute inset-0 h-full w-full object-cover ${isDark ? 'brightness-75' : ''}`}
                                    />
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-black/10 to-transparent" />
                                    <div className="absolute inset-x-0 bottom-0 p-5 text-white">
                                        <p className="text-xs uppercase tracking-[0.22em] text-theme-text-secondary">Lắng dịu</p>
                                        <p className="mt-1 text-sm font-semibold">Nhìn vào ảnh, rồi gọi tên cảm xúc của mình</p>
                                    </div>
                                </div>

                            </div>
                        </div>

                        <div className=" sm:p-6">
                            <div className="mb-4 flex items-center justify-between gap-4">
                                <div>
                                    <h3 className=" uppercase tracking-[0.2em] font-display text-theme-text-primary">Lời nhắn cho bạn</h3>
                                </div>
                                <div className="mt-4 flex items-center gap-2">
                                    <button
                                        type="button"
                                        aria-label="Câu trước"
                                        onClick={() => setQuoteIndex((current) => (current - 1 + Math.max(quotes.length, 1)) % Math.max(quotes.length, 1))}
                                        className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-theme-surface/80 text-theme-text-primary border border-theme-border/30 shadow-sm transition duration-200 ease-in-out hover:bg-theme-accent/10 cursor-pointer"
                                    >
                                        <ChevronLeft className="h-4 w-4" />
                                    </button>
                                    <button
                                        type="button"
                                        aria-label="Câu sau"
                                        onClick={() => setQuoteIndex((current) => (current + 1) % Math.max(quotes.length, 1))}
                                        className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-theme-surface/80 text-theme-text-primary border border-theme-border/30 shadow-sm transition duration-200 ease-in-out hover:bg-theme-accent/10 cursor-pointer"
                                    >
                                        <ChevronRight className="h-4 w-4" />
                                    </button>
                                </div>
                            </div>

                            <div className="relative min-h-[212px] overflow-hidden rounded-3xl  p-5 sm:p-6 shadow-sm border border-theme-border/30">
                                <img
                                    src={beachMessageBg}
                                    alt="Nền sóng biển dịu để làm nổi bật câu nhắc"
                                    className="absolute inset-0 h-full w-full object-cover "
                                />
                                <div className="absolute inset-0 bg-gradient-to-b from-theme-surface/80 via-theme-surface/80 to-transparent" />

                                <AnimatePresence mode="wait">
                                    <motion.div
                                        key={activeQuote?.id || 'default-quote'}
                                        initial={{ opacity: 0, x: 20, filter: 'blur(6px)' }}
                                        animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
                                        exit={{ opacity: 0, x: -20, filter: 'blur(6px)' }}
                                        transition={{ duration: 0.4, ease: 'easeOut' }}
                                        className="relative flex h-full flex-col justify-between"
                                    >
                                        <blockquote className="font-display text-[1.15rem] italic leading-8 text-theme-text-primary sm:text-[1.55rem]">
                                            {quoteContent}
                                        </blockquote>
                                        <div className="mt-6 flex items-center justify-between gap-4">
                                            <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-theme-text-secondary/75">
                                                {quoteAuthor}
                                            </p>
                                            <div className="flex items-center gap-1.5">
                                                {quotes.slice(0, 5).map((item, index) => (
                                                    <button
                                                        key={item.id}
                                                        type="button"
                                                        aria-label={`Chuyển sang câu ${index + 1}`}
                                                        onClick={() => setQuoteIndex(index)}
                                                        className={`h-2.5 rounded-full transition-all duration-200 ease-in-out ${index === quoteIndex % Math.max(quotes.length, 1) ? 'w-8 bg-theme-accent' : 'w-2.5 bg-theme-secondary'}`}
                                                    />
                                                ))}
                                            </div>
                                        </div>
                                    </motion.div>
                                </AnimatePresence>
                            </div>
                        </div>

                    </div>

                    <div className="mt-4">
                        <div className="mb-4">
                            <MoodWordChips selected={homeMoodWords} onChange={setHomeMoodWords} />
                        </div>
                        {homeMoodWords.length > 0 && (
                            <motion.button
                                type="button"
                                onClick={() =>
                                    navigate(ROUTE_PATHS.checkin, { state: { moodWords: homeMoodWords } })
                                }
                                className="mt-4 inline-flex items-center gap-2 rounded-full bg-theme-accent text-white px-5 py-2.5 text-sm font-semibold transition duration-200 ease-in-out hover:bg-theme-accent/80 cursor-pointer"
                            >
                                Ghi chép thêm
                                <motion.div animate={{ x: [0, 3, 0] }} transition={{ duration: 1.5, repeat: Infinity }}>
                                    <ArrowRight className="h-4 w-4" />
                                </motion.div>
                            </motion.button>
                        )}
                    </div>
                </section>

                <motion.button
                    type="button"
                    onClick={() => navigate(ROUTE_PATHS.nutrition)}
                    whileHover={{ y: -4 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                    className="group w-full rounded-[2.5rem] bg-theme-surface/60 p-7 text-left backdrop-blur-xl shadow-sm border border-theme-border/50 transition-all active:scale-[0.98]"
                >
                    <div className="grid gap-5 lg:grid-cols-[220px_1fr_auto] lg:items-center cursor-pointer">
                        <div className="relative overflow-hidden rounded-[24px] min-h-[170px] shadow-sm">
                            <Mascot
                                variant="eat"
                                size="xl"
                                alt="Serene đang ăn nhẹ"
                                className="absolute inset-0 m-auto h-32 w-32"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/55 via-black/20 to-transparent" />
                            <div className="absolute inset-x-0 bottom-0 p-4 text-white">
                                <p className="text-xs uppercase tracking-[0.19em] text-theme-text-secondary">Nuôi dưỡng cơ thể</p>
                                <p className="mt-1 text-xs font-semibold">Ăn đủ để mood cũng được nâng lên</p>
                            </div>
                        </div>

                        <div className="flex-1">
                            <p className="text-xs uppercase tracking-[0.2em] font-bold text-theme-text-secondary">Món ăn hôm nay</p>
                            <h2 className="mt-2.5 font-display text-2xl text-theme-text-primary group-hover:text-theme-accent transition-colors">
                                {nutritionTip?.dish || 'Yến mạch + trái cây + hạt'}
                            </h2>
                            <p className="mt-3 leading-relaxed text-theme-text-secondary">
                                {nutritionTip?.benefit || 'Bữa ăn đủ đạm và chất xơ giúp ổn định mood, giảm cảm giác tụt năng lượng.'}
                            </p>
                        </div>
                        <ArrowRight className="h-5 w-5 text-theme-text-secondary transition group-hover:translate-x-1" />
                    </div>
                </motion.button>

             
                {detailReminder && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="fixed inset-0 z-70 flex items-center justify-center bg-black/40 px-4 backdrop-blur-sm"
                    >
                        <article className="w-full max-w-xl rounded-3xl bg-theme-surface p-6 shadow-2xl relative overflow-hidden border border-theme-border/50">
                            <div className="absolute top-0 left-0 w-full h-1 bg-theme-accent opacity-50" />
                            <div className="mb-5 flex items-center justify-between">
                                <h3 className="font-display text-2xl text-theme-text-primary">{detailReminder.detailTitle}</h3>
                                <button
                                    type="button"
                                    onClick={() => setDetailReminderId(null)}
                                    className="rounded-full bg-theme-surface/50 hover:bg-theme-surface p-2 text-theme-text-secondary border border-theme-border/20 transition-colors"
                                >
                                    <X className="h-5 w-5" />
                                </button>
                            </div>
                            <div className="space-y-4 text-theme-text-secondary leading-relaxed">
                                <p>{detailReminder.importance}</p>
                                <div className="rounded-2xl bg-theme-accent/10 p-4">
                                    <p className="text-sm font-semibold text-theme-accent uppercase tracking-wider mb-1">Cảnh báo</p>
                                    <p className="text-theme-text-primary">{detailReminder.downside}</p>
                                </div>
                            </div>
                            {detailReminder.route && (
                                <button
                                    onClick={() => navigate(detailReminder.route!)}
                                    className="mt-6 w-full rounded-2xl bg-theme-accent py-4 text-sm font-bold uppercase tracking-widest text-white shadow-lg transition hover:brightness-105 active:scale-95"
                                >
                                    Thực hiện ngay
                                </button>
                            )}
                        </article>
                    </motion.div>
                )}
            </div>
        </div>
    )
}
