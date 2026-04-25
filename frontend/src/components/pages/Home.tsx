import {
    AirVent,
    ArrowRight,
    BookOpen,
    Cloud,
    Leaf,
    Play,
    Sparkles,
    Volume2,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import type { ReactNode } from 'react'
import exercise from '../../assets/exercise.png'
import journal from '../../assets/journal.png'
import ethereal from '../../assets/ethereal.png'
import forest from '../../assets/forest.png'
import { homeService } from '../../services/homeService'
import { ROUTE_PATHS } from '../../routes/paths'

type MoodCard = {
    icon: ReactNode
    title: string
    desc: string
    active?: boolean
    apiMood: string
    emoji?: string
}

type QuickItem = {
    image: string
    title: string
    desc: string
    icon: ReactNode
    route: string
}

const moods: MoodCard[] = [
    {
        icon: <Leaf className="h-7 w-7" />,
        title: 'Bình yên',
        desc: 'Nhẹ như mặt nước phẳng lặng.',
        apiMood: 'calm',
        emoji: '🍃',
    },
    {
        icon: <Cloud className="h-7 w-7" />,
        title: 'Lắng lại',
        desc: 'Một cơn mưa nhỏ trong lòng.',
        apiMood: 'melancholic',
        emoji: '☁️',
    },
    {
        icon: <Sparkles className="h-7 w-7" />,
        title: 'Rạng rỡ',
        desc: 'Năng lượng đang mở ra.',
        apiMood: 'bright',
        emoji: '✨',
    },
    {
        icon: <AirVent className="h-7 w-7" />,
        title: 'Bồn chồn',
        desc: 'Cần một nhịp thở sâu.',
        apiMood: 'restless',
        emoji: '🌬️',
    },
]


const quickItems: QuickItem[] = [
    {
        image: exercise,
        title: 'Gentle Flow',
        desc: 'Đánh thức cơ thể với chuyển động có chủ đích.',
        icon: <ArrowRight className="h-5 w-5" />,
        route: ROUTE_PATHS.exercises,
    },
    {
        image: journal,
        title: 'Journal Prompt',
        desc: 'Điều gì hôm nay nhẹ hơn ngày hôm qua?',
        icon: <BookOpen className="h-5 w-5" />,
        route: ROUTE_PATHS.checkin,
    },
    {
        image: ethereal,
        title: 'Ethereal Tides',
        desc: 'Âm thanh đại dương để tập trung và hồi phục.',
        icon: <Volume2 className="h-5 w-5" />,
        route: ROUTE_PATHS.resources,
    },
]

const PERSONA_TABS = [
    { id: 'checkin',   label: 'Check-in nhanh',     sub: 'An · 2 phút',    emoji: '☀️', next: ROUTE_PATHS.checkin },
    { id: 'screening', label: 'Làm bài sàng lọc',   sub: 'Lửa · ~5 phút', emoji: '📋', next: ROUTE_PATHS.screening },
    { id: 'chat',      label: 'Trò chuyện ngay',     sub: 'Mây · luôn sẵn', emoji: '💬', next: ROUTE_PATHS.chat },
]

export default function Home() {
    const navigate = useNavigate()
    const [checkedInMood, setCheckedInMood] = useState<string | null>(null)
    const [quote, setQuote] = useState<{ text: string; author?: string | null } | null>(null)
    const [submittingMood, setSubmittingMood] = useState<string | null>(null)

    const handlePersonaTab = (next: string) => {
        navigate(next)
    }

    useEffect(() => {
        let mounted = true
        homeService
            .feed()
            .then((data) => {
                if (!mounted) return
                setCheckedInMood(data.mood_today.mood)
                setQuote(data.quote_of_day)
            })
            .catch(() => undefined)
        return () => {
            mounted = false
        }
    }, [])

    const moodCards = useMemo(
        () =>
            moods.map((mood) => ({
                ...mood,
                active: checkedInMood ? checkedInMood === mood.apiMood : Boolean(mood.active),
            })),
        [checkedInMood],
    )

    const onCheckinMood = async (mood: MoodCard) => {
        if (submittingMood) return
        try {
            setSubmittingMood(mood.apiMood)
            await homeService.checkin({ mood: mood.apiMood, emoji: mood.emoji })
            setCheckedInMood(mood.apiMood)
            toast.success('Đã lưu mood check-in hôm nay.')
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Không thể lưu check-in'
            toast.info(message)
        } finally {
            setSubmittingMood(null)
        }
    }

    return (
        <div className="space-y-12 lg:space-y-16">

            <h2 className="font-display text-5xl leading-tight text-white sm:text-6xl lg:text-7xl">
                Hôm nay
                <span className="font-display italic font-semibold text-serene-ink/80"> thế giới nội tâm </span>
                của bạn đang như thế nào?
            </h2>

            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 xl:gap-6">
                {moodCards.map((mood) => (
                    <article
                        key={mood.title}
                        onClick={() => void onCheckinMood(mood)}
                        className={[
                            'rounded-[26px] border px-6 py-7 backdrop-blur-xl transition cursor-pointer',
                            mood.active
                                ? 'border-serene-primary/20 bg-serene-primary/90 text-serene-on-primary shadow-lg'
                                : 'border-white/45 bg-white/55 hover:bg-white/70',
                        ].join(' ')}
                        aria-busy={submittingMood === mood.apiMood}
                    >
                        <div className={mood.active ? 'text-serene-accent' : 'text-serene-primary'}>
                            {mood.icon}
                        </div>
                        <h3
                            className={[
                                'mt-7 font-display text-3xl',
                                mood.active ? 'text-serene-on-primary' : 'text-serene-ink',
                            ].join(' ')}
                        >
                            {mood.title}
                        </h3>
                        <p
                            className={[
                                'mt-2 text-sm',
                                mood.active ? 'text-serene-on-primary/75' : 'text-serene-muted/85',
                            ].join(' ')}
                        >
                            {mood.desc}
                        </p>
                    </article>
                ))}
            </section>

            <section className="grid gap-3 sm:grid-cols-3">
                {PERSONA_TABS.map((tab) => (
                    <button
                        key={tab.id}
                        type="button"
                        onClick={() => handlePersonaTab(tab.next)}
                        className="flex items-center gap-4 rounded-[26px] border border-white/45 bg-white/55 px-5 py-4 backdrop-blur-xl transition hover:bg-white/70 active:scale-[0.98] text-left"
                    >
                        <span className="text-2xl" aria-hidden="true">{tab.emoji}</span>
                        <div className="min-w-0">
                            <p className="font-semibold text-serene-ink text-base leading-tight">{tab.label}</p>
                            <p className="text-sm text-serene-muted mt-0.5">{tab.sub}</p>
                        </div>
                        <span className="ml-auto text-serene-muted text-lg" aria-hidden="true">›</span>
                    </button>
                ))}
            </section>

            <section className="grid gap-8 lg:grid-cols-2 lg:gap-10">
                <article className="group relative overflow-hidden rounded-[34px] shadow-[0_30px_70px_rgba(47,52,46,0.26)] ">
                    <img
                        src={forest}
                        alt="Lối đi trong rừng"
                        className="absolute inset-0 h-full w-full object-cover transition duration-700 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-linear-to-t from-serene-primary/90 via-serene-primary/20 to-transparent" />
                    <div className="absolute bottom-0 left-0 w-full p-8 sm:p-10">
                        <p className="text-xs uppercase tracking-[0.25em] text-serene-accent/90">
                            Gợi ý cho bạn
                        </p>
                        <h3 className="mt-4 font-display text-4xl text-serene-on-primary sm:text-5xl">
                            Thiền Sáng
                            <br />
                            Giữa Rừng
                        </h3>
                        <div className="mt-7 flex flex-wrap items-center gap-4">
                            <button
                                type="button"
                                onClick={() => navigate(ROUTE_PATHS.exercises)}
                                className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 font-display text-xl italic text-serene-primary transition hover:bg-serene-bg"
                            >
                                Bắt đầu
                                <Play className="h-4 w-4" />
                            </button>
                            <span className="text-sm text-serene-on-primary/80">
                                12 phút · Level 1
                            </span>
                        </div>
                    </div>
                </article>

                <div className="space-y-5 lg:space-y-7">
                    {quickItems.map((item) => (
                        <button
                            key={item.title}
                            type="button"
                            onClick={() => navigate(item.route)}
                            className="group flex items-center gap-4 rounded-3xl border border-white/30 bg-white/50 p-4 backdrop-blur-xl transition-colors hover:bg-white/70"
                        >
                            <img
                                src={item.image}
                                alt={item.title}
                                className="h-24 w-24 rounded-2xl object-cover shadow-xl transition duration-200 group-hover:grayscale-0 lg:grayscale"
                            />
                            <div className="flex-1">
                                <h4 className="font-display text-3xl text-serene-ink">{item.title}</h4>
                                <p className="mt-1 text-sm text-serene-muted">{item.desc}</p>
                            </div>
                            <span className="text-serene-muted transition group-hover:text-serene-primary">
                                {item.icon}
                            </span>
                        </button>
                    ))}
                </div>
            </section>

            <section className="rounded-4xl border border-white/30 bg-serene-primary/80 px-7 py-14 text-center backdrop-blur-xl sm:px-12 lg:px-20 lg:py-20">
                <Leaf className="mx-auto h-12 w-12 text-serene-accent/80" />
                <blockquote className="mx-auto mt-6 max-w-4xl font-display text-3xl italic leading-snug text-serene-on-primary sm:text-5xl">
                    {quote?.text ? `“${quote.text}”` : '“Giây phút hiện tại là nơi duy nhất sự sống thực sự tồn tại.”'}
                </blockquote>
                <p className="mt-5 text-xs uppercase tracking-[0.25em] text-serene-on-primary/65">
                    {quote?.author || 'Thích Nhất Hạnh'}
                </p>
            </section>
        </div>
    )
}
