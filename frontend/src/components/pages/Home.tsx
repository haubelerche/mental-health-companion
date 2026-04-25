import {
    ArrowRight,
    BookOpen,
    Leaf,
    Play,
    Volume2,
    MessageSquareText,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import exercise from '../../assets/exercise.png'
import journal from '../../assets/journal.png'
import ethereal from '../../assets/ethereal.png'
import forest from '../../assets/forest.png'
import { homeService } from '../../services/homeService'
import { ROUTE_PATHS } from '../../routes/paths'

type ModeCard = {
    icon: ReactNode
    title: string
    desc: string
    meta: string
    route: string
    featured?: boolean
}

type QuickItem = {
    image: string
    title: string
    desc: string
    icon: ReactNode
    route: string
}

const modeCards: ModeCard[] = [
    {
        icon: <Leaf className="h-7 w-7" />,
        title: 'Check-in nhanh',
        desc: 'Ghi nhận cảm xúc hiện tại trong vài chạm.',
        meta: 'An · 2 phút',
        route: ROUTE_PATHS.checkin,
        featured: true,
    },
    {
        icon: <BookOpen className="h-7 w-7" />,
        title: 'Làm bài sàng lọc',
        desc: 'PHQ-9/GAD-7 ngắn để hiểu tín hiệu của bạn.',
        meta: 'Lửa · ~5 phút',
        route: ROUTE_PATHS.screening,
    },
    {
        icon: <MessageSquareText className="h-7 w-7" />,
        title: 'Trò chuyện ngay',
        desc: 'Mây luôn sẵn sàng lắng nghe và đồng hành.',
        meta: 'Mây · luôn sẵn',
        route: ROUTE_PATHS.chat,
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

export default function Home() {
    const navigate = useNavigate()
    const [quote, setQuote] = useState<{ text: string; author?: string | null } | null>(null)

    useEffect(() => {
        let mounted = true
        homeService
            .feed()
            .then((data) => {
                if (!mounted) return
                setQuote(data.quote_of_day)
            })
            .catch(() => undefined)
        return () => {
            mounted = false
        }
    }, [])

    return (
        <div className="space-y-12 lg:space-y-16">

            <h2 className="font-display text-5xl leading-tight text-white sm:text-6xl lg:text-7xl">
                Hôm nay
                <span className="font-display italic font-semibold text-serene-ink/80"> thế giới nội tâm </span>
                của bạn đang như thế nào?
            </h2>

            <section className="grid gap-4 md:grid-cols-3 xl:gap-6">
                {modeCards.map((mode) => (
                    <button
                        key={mode.title}
                        type="button"
                        onClick={() => navigate(mode.route)}
                        className={[
                            'group flex min-h-[150px] h-full flex-col justify-between rounded-[26px] border px-6 py-6 text-left backdrop-blur-xl transition active:scale-[0.98]',
                            mode.featured
                                ? 'border-serene-primary/20 bg-serene-primary/90 text-serene-on-primary shadow-lg'
                                : 'border-white/45 bg-white/55 text-serene-ink hover:bg-white/70',
                        ].join(' ')}
                    >
                        <div className="flex items-start justify-between gap-4">
                            <div className={mode.featured ? 'text-serene-accent' : 'text-serene-primary'}>
                                {mode.icon}
                            </div>
                            <ArrowRight
                                className={[
                                    'h-5 w-5 transition group-hover:translate-x-0.5',
                                    mode.featured ? 'text-serene-on-primary/80' : 'text-serene-muted',
                                ].join(' ')}
                            />
                        </div>
                        <h3
                            className={[
                                'mt-6 font-display text-3xl leading-none',
                                mode.featured ? 'text-serene-on-primary' : 'text-serene-ink',
                            ].join(' ')}
                        >
                            {mode.title}
                        </h3>
                        <p
                            className={[
                                'mt-3 min-h-[2.5rem] text-sm leading-relaxed',
                                mode.featured ? 'text-serene-on-primary/75' : 'text-serene-muted/85',
                            ].join(' ')}
                        >
                            {mode.desc}
                        </p>
                        <span
                            className={[
                                'mt-4 text-xs font-semibold uppercase tracking-[0.22em]',
                                mode.featured ? 'text-serene-on-primary/60' : 'text-serene-primary/70',
                            ].join(' ')}
                        >
                            {mode.meta}
                        </span>
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
