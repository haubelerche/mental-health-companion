import {
    AirVent,
    ArrowRight,
    BookOpen,
    Cloud,
    Group,
    Home as HomeIcon,
    Leaf,
    Play,
    Settings,
    Sparkles,
    Volume2,
} from 'lucide-react'
import type { ReactNode } from 'react'

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
        image:
            'https://lh3.googleusercontent.com/aida-public/AB6AXuCnXeu5um_QkAcXqOSG7nGUuOnP48XcYKYCGYuF6Yp2s2me324xacgKbar-rG79fq6hxvs8hprBe4UCEfSod1CM5oKhrhSetgdIN_EIgkqD1IDp4vz6VJpnxn-MEE0ITYNn1LLUzHvcslZwoLx7CUt96-XrjdSjYkPsDfqGB9dmgz4Jjq0Ln1rPpbSjhJwcdJYt2I6a2Olqkzk25wBTb354IVAag1coVzzFjkfNSYtCU-EkgQ9oiDjZPskFvHlpEV9XYQOvbIofa7E',
        title: 'Gentle Flow',
        desc: 'Đánh thức cơ thể với chuyển động có chủ đích.',
        icon: <ArrowRight className="h-5 w-5" />,
    },
    {
        image:
            'https://lh3.googleusercontent.com/aida-public/AB6AXuBs21FCJxqp42KZIwUg4N4-upWG8JNl7W4pfWXdAuErpztlD3NpIeT-BDzO7blOfngngGFrH5QgIRe2Fueg33itfnf6BJZUZJ0b3O39l_5ihH-NL33Z3Dr34Xe4lTTzEMhi92gDKHvUYlwaeR2CTK_2y6Dc0o95Vjt06tRms1Cjo8M54o546SXjYo-wO9aIOd5dQQ8_UzMoPZmxjbvudO5ceMQqhxSu5UGsM5ftPdUHLjpn3z0OYx6hxJDEJT_DVfGi9l9U5_amc5w',
        title: 'Journal Prompt',
        desc: 'Điều gì hôm nay nhẹ hơn ngày hôm qua?',
        icon: <BookOpen className="h-5 w-5" />,
    },
    {
        image:
            'https://lh3.googleusercontent.com/aida-public/AB6AXuD4usbRwNoTVLbVuUAEB9c9J8QKc_ES53m3UVEzNiB8NTo2pGHb_H9X5QnyTLCDrlweAnpP9Qdk7fgcCN5bb8EXdfU2o4N_UbrgPpcSMwqeci05pdYVlAPnYlD9qmX6SPHPr0oXPSnZPX8DsMWgrkHlt9CrR1nY8nsUDxQViiWRwcZ4Fv6ZLuDT1H7MgZBm058xCkSa7oVuQIZh6Oey-A0ytlBuLjZHMCzIxiB5KaOPT7D5S9Nf1y9SPTuW_-I1pfPEIZNeu4zIjYY',
        title: 'Ethereal Tides',
        desc: 'Âm thanh đại dương để tập trung và hồi phục.',
        icon: <Volume2 className="h-5 w-5" />,
    },
]

const navItems = [
    { icon: HomeIcon, label: 'Home', active: true },
    { icon: Sparkles, label: 'Chat' },
    { icon: Leaf, label: 'Reflect' },
    { icon: BookOpen, label: 'Resources' },
    { icon: Group, label: 'Connect' },
]

export default function Home() {
    return (
        <div className="relative min-h-screen overflow-x-hidden bg-serene-bg text-serene-ink">
            <div className="fixed inset-0 -z-20">
                <img
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuAgvsHOwaA6M02038SSeOlZKKi3Q5pnB5Xyi9ER418uly7djrzAHxxz9A0V53_FTAfdhv7mrWKZXuFoUE0e68y6oYKPJefyncdgtPGtQOJ_9B-jf4gqwpRO_51x8uelov0veT4YG5jjNW2C4sNpI4eFKZw-nB0qKzGLcjshI7uCggwXCkKE9gHE5kWqHuxrL1es2YtVFNyEQxqwpbXCF8xvHgffPu0PM-vyGkrxEYHtwf07_SJzf1U5q5u3RzgLqn1lrlMPJBKrVHA"
                    alt="Mặt biển lúc hoàng hôn"
                    className="h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-white/20" />
            </div>

            <div className="fixed inset-0 -z-10 pointer-events-none opacity-[0.03] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />

            <aside className="fixed left-0 top-0 z-40 hidden h-full w-72 flex-col rounded-r-[32px] border-r border-white/35 bg-white/55 p-8 backdrop-blur-3xl lg:flex">
                <div className="mb-10">
                    <h1 className="font-display text-5xl italic text-serene-ink">Serene</h1>
                    <p className="mt-2 text-[11px] uppercase tracking-[0.28em] text-serene-muted/85">
                        Digital Sanctuary
                    </p>
                </div>

                <nav className="flex flex-1 flex-col gap-3">
                    {navItems.map((item) => {
                        const Icon = item.icon
                        return (
                            <button
                                key={item.label}
                                type="button"
                                className={[
                                    'flex items-center gap-3 rounded-2xl px-3 py-3 text-left transition',
                                    item.active
                                        ? 'border-l-4 border-serene-primary bg-white/70 text-serene-primary shadow-sm'
                                        : 'text-serene-muted hover:bg-white/60 hover:text-serene-ink',
                                ].join(' ')}
                            >
                                <Icon className="h-5 w-5" />
                                <span className="font-display text-xl">{item.label}</span>
                            </button>
                        )
                    })}
                </nav>

                <button
                    type="button"
                    className="mt-8 rounded-2xl bg-serene-primary py-4 font-display text-xl italic text-serene-on-primary shadow-[0_14px_34px_rgba(47,52,46,0.24)] transition hover:brightness-105"
                >
                    Breathe Now
                </button>
            </aside>

            <main className="min-h-screen lg:ml-72">
                <header className="sticky top-0 z-30 flex items-center justify-between border-b border-white/35 bg-white/30 px-5 py-4 backdrop-blur-xl sm:px-8 lg:px-12">
                    <div className="flex items-center gap-3 sm:gap-4">
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
                                Hôm nay thế giới nội tâm
                                <br />
                                của bạn đang như thế nào?
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
                        <article className="group relative min-h-[420px] overflow-hidden rounded-[34px] shadow-[0_30px_70px_rgba(47,52,46,0.26)] lg:min-h-[520px]">
                            <img
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuAqrlqV6K7soDRwnNHIgqWTa8sCWRy8fKXCeNmlMgqvfAbql-OiyjPdh68vAc9TnbEaLN2qNni9Q7Srx2g9ukegLhX2ZcDjVWM-EgaQxloBVcZ7MgFbRvutagUWXFXsvB3w3S-X1xzTQbo_t_lNKRY2TjgBnm9DgpkvBjwum9HS1r7k1UpJlRvRK6LtIUAZGj9KaDMiQIKWP6W_pdGAsrhyjp6cIeutSrYhRFjPulvx4YNj_T1XodOnEMSdOFCJG5fbsqK8tUCY6hw"
                                alt="Lối đi trong rừng"
                                className="absolute inset-0 h-full w-full object-cover transition duration-700 group-hover:scale-105"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-serene-primary/90 via-serene-primary/20 to-transparent" />
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

                <footer className="hidden border-t border-white/30 bg-white/35 px-12 py-8 text-[11px] uppercase tracking-[0.22em] text-serene-muted/85 backdrop-blur-xl lg:flex lg:items-center lg:justify-between">
                    <span>© 2026 Serene</span>
                    <div className="flex items-center gap-10">
                        <button type="button" className="transition hover:text-serene-primary">
                            Trợ giúp
                        </button>
                        <button type="button" className="transition hover:text-serene-primary">
                            Privacy Policy
                        </button>
                        <button type="button" className="transition hover:text-serene-primary">
                            Terms of Peace
                        </button>
                    </div>
                </footer>
            </main>

            <nav className="fixed bottom-4 left-1/2 z-50 flex w-[min(94vw,560px)] -translate-x-1/2 items-center justify-between rounded-3xl border border-white/45 bg-white/70 px-4 py-2 backdrop-blur-xl lg:hidden">
                {navItems.map((item) => {
                    const Icon = item.icon
                    return (
                        <button
                            key={item.label}
                            type="button"
                            className={[
                                'flex flex-1 flex-col items-center gap-1 rounded-2xl py-2 text-[11px] transition',
                                item.active ? 'bg-white text-serene-primary' : 'text-serene-muted',
                            ].join(' ')}
                        >
                            <Icon className="h-4 w-4" />
                            <span>{item.label}</span>
                        </button>
                    )
                })}
            </nav>
        </div>
    )
}
