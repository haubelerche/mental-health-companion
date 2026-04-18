import {
    AirVent,
    ArrowRight,
    BookOpen,
    Cloud,
    Group,
    Home as HomeIcon,
    Leaf,
    PanelLeft,
    PanelLeftClose,
    Play,
    Settings,
    Sparkles,
    Volume2,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { useState } from 'react'
import Sidebar from '../layout/Sidebar'
import bg from '../../assets/bg3.png'
import exercise from '../../assets/exercise.png'
import journal from '../../assets/journal.png'
import ethereal from '../../assets/ethereal.png'
import forest from '../../assets/forest.png'

type MoodCard = {
    icon: ReactNode
    title: string
    desc: string
    active?: boolean
}

type QuickItem = {
    image: string
    title: string
    desc: string
    icon: ReactNode
}

const moods: MoodCard[] = [
    {
        icon: <Leaf className="h-7 w-7" />,
        title: 'Bình yên',
        desc: 'Nhẹ như mặt nước phẳng lặng.',
    },
    {
        icon: <Cloud className="h-7 w-7" />,
        title: 'Lắng lại',
        desc: 'Một cơn mưa nhỏ trong lòng.',
        active: true,
    },
    {
        icon: <Sparkles className="h-7 w-7" />,
        title: 'Rạng rỡ',
        desc: 'Năng lượng đang mở ra.',
    },
    {
        icon: <AirVent className="h-7 w-7" />,
        title: 'Bồn chồn',
        desc: 'Cần một nhịp thở sâu.',
    },
]

const quickItems: QuickItem[] = [
    {
        image: exercise,
        title: 'Gentle Flow',
        desc: 'Đánh thức cơ thể với chuyển động có chủ đích.',
        icon: <ArrowRight className="h-5 w-5" />,
    },
    {
        image: journal,
        title: 'Journal Prompt',
        desc: 'Điều gì hôm nay nhẹ hơn ngày hôm qua?',
        icon: <BookOpen className="h-5 w-5" />,
    },
    {
        image: ethereal,
        title: 'Ethereal Tides',
        desc: 'Âm thanh đại dương để tập trung và hồi phục.',
        icon: <Volume2 className="h-5 w-5" />,
    },
]

const navItems = [
    { icon: <HomeIcon className="h-5 w-5" />, label: 'Home', active: true },
    { icon: <Sparkles className="h-5 w-5" />, label: 'Chat' },
    { icon: <Leaf className="h-5 w-5" />, label: 'Reflect' },
    { icon: <BookOpen className="h-5 w-5" />, label: 'Resources' },
    { icon: <Group className="h-5 w-5" />, label: 'Connect' },
]

export default function Home() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)

    return (
        <div className="relative min-h-screen overflow-x-hidden  text-serene-ink">
            <div className="fixed inset-0 -z-20">
                <img
                    src={bg}
                    alt="Mặt biển lúc hoàng hôn"
                    className="h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-white/20" />
            </div>

            <div className="fixed inset-0 -z-10 pointer-events-none opacity-[0.03] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />

            <Sidebar navItems={navItems} isOpen={isSidebarOpen} />

            <main
                className={[
                    'min-h-screen transition-all duration-300',
                    isSidebarOpen ? 'lg:ml-72' : 'lg:ml-0',
                ].join(' ')}
            >
                <header className="sticky top-0 z-30 flex items-center justify-between border-b border-white/35 px-5 py-4 backdrop-blur-xl sm:px-8 lg:px-12">
                    <div className="flex items-center gap-3 sm:gap-4">
                        <button
                            type="button"
                            onClick={() => setIsSidebarOpen((prev) => !prev)}
                            className="rounded-full p-2 text-white/90 transition hover:bg-white/25"
                            aria-label={isSidebarOpen ? 'Ẩn sidebar' : 'Hiện sidebar'}
                        >
                            {isSidebarOpen ? (
                                <PanelLeftClose className="h-5 w-5" />
                            ) : (
                                <PanelLeft className="h-5 w-5" />
                            )}
                        </button>
                        <img
                            src="https://lh3.googleusercontent.com/aida-public/AB6AXuC6xpig2l3SMnAnmPD3226klv7fSDDOAMHWjUcCZaakIEznH7s6gqVLuhEbeQ_ioWvn515mTic_UfBHcOp799nLyXYwNMRIrHn-dwI-g2tFHEOcNNCrWuoTCKErn1V0RYZ6Mr1Wl7evlwFzsL4tHYsEfQWmGwaz1HKOirvXAuuFa1IvMCQwBLMCe-SBnR0VSZDTIvV_m9VYUGHjpEZ7c9J6p_GIXUM-MY6KD5l6LKA2L2ylmr9tsRl5Sn05lyM2SsF6x-eveAtafiM"
                            alt="Ảnh hồ sơ"
                            className="h-11 w-11 rounded-full border-2 border-white/70 object-cover"
                        />
                        <p className="font-display text-lg text-white sm:text-2xl">
                            Buổi sáng tốt lành nhé Elena!
                        </p>
                    </div>
                    <div className="flex items-center gap-2 sm:gap-4">
                        <button
                            type="button"
                            className="rounded-full p-2 text-white/90 transition hover:bg-white/25"
                        >
                            <Sparkles className="h-5 w-5" />
                        </button>
                        <button
                            type="button"
                            className="rounded-full p-2 text-white/90 transition hover:bg-white/25"
                        >
                            <Settings className="h-5 w-5" />
                        </button>
                    </div>
                </header>

                <div className="mx-auto max-w-7xl space-y-12 px-5 pb-28 pt-8 sm:px-8 lg:space-y-16 lg:px-12 lg:py-12">
                    <section className="grid items-end gap-8 lg:grid-cols-12 lg:gap-12">
                        <div className="lg:col-span-8">
                            <h2 className="font-display text-5xl leading-tight text-white sm:text-6xl lg:text-7xl">
                                Hôm nay <span className='italic font-display text-serene-ink'>thế giới nội tâm </span>của bạn đang như thế nào?
                            </h2>
                        </div>
                        <p className="text-base leading-relaxed text-serene-ink/85 lg:col-span-4 lg:pb-3 lg:text-lg">
                            Chậm lại một nhịp. Sương đang tan dần và ngày mới thuộc về bạn.
                        </p>
                    </section>

                    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 xl:gap-6">
                        {moods.map((mood) => (
                            <article
                                key={mood.title}
                                className={[
                                    'rounded-[26px] border px-6 py-7 backdrop-blur-xl transition',
                                    mood.active
                                        ? 'border-serene-primary/20 bg-serene-primary/90 text-serene-on-primary shadow-lg'
                                        : 'border-white/45 bg-white/55 hover:bg-white/70',
                                ].join(' ')}
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
                                <article
                                    key={item.title}
                                    className="group flex items-center gap-4 rounded-3xl border border-white/35 bg-white/55 p-4 backdrop-blur-xl transition hover:bg-white/72"
                                >
                                    <img
                                        src={item.image}
                                        alt={item.title}
                                        className="h-24 w-24 rounded-2xl object-cover shadow-md transition duration-500 group-hover:grayscale-0 lg:grayscale"
                                    />
                                    <div className="flex-1">
                                        <h4 className="font-display text-3xl text-serene-ink">{item.title}</h4>
                                        <p className="mt-1 text-sm text-serene-muted">{item.desc}</p>
                                    </div>
                                    <span className="text-serene-muted transition group-hover:text-serene-primary">
                                        {item.icon}
                                    </span>
                                </article>
                            ))}
                        </div>
                    </section>

                    <section className="rounded-[34px] border border-white/35 bg-serene-primary/80 px-7 py-14 text-center backdrop-blur-xl sm:px-12 lg:px-20 lg:py-20">
                        <Leaf className="mx-auto h-12 w-12 text-serene-accent/80" />
                        <blockquote className="mx-auto mt-6 max-w-3xl font-display text-3xl italic leading-snug text-serene-on-primary sm:text-5xl">
                            “Giây phút hiện tại là nơi duy nhất sự sống thực sự tồn tại.”
                        </blockquote>
                        <p className="mt-5 text-xs uppercase tracking-[0.25em] text-serene-on-primary/65">
                            Thich Nhat Hanh
                        </p>
                    </section>
                </div>

               
            </main>
        </div>
    )
}
