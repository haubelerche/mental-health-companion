import { ArrowRight, ChevronRight, Leaf, MoonStar, Sparkles, Wind } from 'lucide-react'
import bg from '../../assets/bg.png'

const moodBars = [
    { height: 'h-2/3', fill: 'h-1/2' },
    { height: 'h-3/4', fill: 'h-2/3' },
    { height: 'h-1/2', fill: 'h-1/4' },
    { height: 'h-full', fill: 'h-4/5' },
    { height: 'h-3/4', fill: 'h-3/5' },
    { height: 'h-[82%]', fill: 'h-3/4' },
    { height: 'h-2/3', fill: 'h-1/2' },
]

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

export default function Reflect() {
    return (
        <div className="relative min-h-screen overflow-hidden text-serene-ink ">
                <div className="flex-1">
                    <div className="mx-auto flex w-full max-w-5xl flex-col items-center">
                        <section className="border border-white/35 bg-white/60 backdrop-blur-xl w-full rounded-4xl  p-5 shadow-md md:p-10 lg:p-12">
                            <div className="text-center">
                                <h1 className="font-display text-5xl font-light leading-tight text-[#2F342E] md:text-6xl lg:text-7xl">
                                    Chào <span className="italic text-primary font-medium">Elena</span>
                                </h1>
                                <p className="mx-auto mt-5 max-w-2xl text-sm italic leading-relaxed text-on-surface-variant/80 md:text-lg">
                                    Thủy triều tối nay thật êm đềm. Chúng ta hãy cùng nhìn lại nhé?
                                </p>
                            </div>

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
                                                strokeDasharray="515.2"
                                                strokeDashoffset="92.7"
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
                                            <span className="font-display text-5xl font-light text-on-surface md:text-6xl">
                                                82<span className="text-xl opacity-40 md:text-2xl">%</span>
                                            </span>
                                            <span className="mt-2 text-[10px] uppercase tracking-[0.3em] text-primary-dim">
                                                Harmonized
                                            </span>
                                        </div>
                                    </div>
                                    <p className="mx-auto mt-6 max-w-sm text-sm leading-relaxed text-on-surface-variant">
                                        Sự thay đổi nhịp tim và nhịp thở của bạn cải thiện 12% so với ngày hôm qua.
                                    </p>
                                </div>

                                <div className="rounded-[1.75rem] border border-white/25 bg-white/30 p-6 backdrop-blur-md md:p-8">
                                    <div className="mb-6 flex items-end justify-between gap-4">
                                        <div>
                                            <h2 className="font-display text-2xl text-on-surface md:text-[2rem]">Biểu đồ cảm xúc</h2>
                                            <p className="text-[10px] uppercase tracking-[0.28em] text-on-surface-variant/60">
                                                7 ngày qua
                                            </p>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="h-2.5 w-2.5 rounded-full bg-primary" />
                                            <span className="h-2.5 w-2.5 rounded-full bg-white/50" />
                                        </div>
                                    </div>

                                    <div className="flex min-h-40 items-end gap-3 md:min-h-48">
                                        {moodBars.map((bar, index) => (
                                            <div
                                                key={`mood-bar-${index}`}
                                                className={`group relative flex-1 rounded-t-full bg-white/20 ${bar.height}`}
                                            >
                                                <div
                                                    className={`absolute bottom-0 w-full rounded-t-full bg-primary/40 transition-all group-hover:bg-primary ${bar.fill}`}
                                                />
                                            </div>
                                        ))}
                                    </div>

                                    <div className="mt-5 flex justify-between px-1 text-[10px] uppercase tracking-widest text-on-surface-variant/70">
                                        <span>T2</span>
                                        <span className="font-bold text-primary">T6</span>
                                        <span>CN</span>
                                    </div>
                                </div>
                            </div>

                            <section className="mt-8 rounded-3xl border-l-4 border-primary/30 bg-primary/5 p-6 md:p-8">
                                <div className="mb-5 flex items-center gap-4">
                                    <div className="rounded-full bg-primary/10 p-3 text-primary">
                                        <Sparkles className="h-6 w-6" />
                                    </div>
                                    <h2 className="font-display text-2xl italic text-emerald-900 md:text-3xl">
                                        Lời nhắn tuần từ Serene
                                    </h2>
                                </div>
                                <p className="text-base leading-relaxed text-on-surface-variant/90 md:text-lg">
                                    “Sự tĩnh lặng của bạn đạt đỉnh sau những buổi đi dạo trong rừng buổi sáng. Không khí ngày mai sẽ rất trong lành - có lẽ một khoảnh khắc yên bình dưới tán cây sẽ nuôi dưỡng sự tập trung của bạn.”
                                </p>
                            </section>

                            <section className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3 lg:gap-8">
                                <div className="rounded-3xl border border-white/25 bg-white/30 p-6 backdrop-blur-md lg:col-span-2 md:p-8">
                                    <div className="mb-7 flex items-center justify-between gap-4">
                                        <div className="flex items-center gap-3">
                                            <Leaf className="h-5 w-5 text-primary" />
                                            <h3 className="font-display text-2xl text-on-surface">Nhật ký gần đây</h3>
                                        </div>
                                        <span className="text-[10px] uppercase tracking-widest text-on-surface-variant/50">3 giờ trước</span>
                                    </div>

                                    <blockquote className="mb-6 font-display text-2xl italic leading-relaxed text-primary-dim md:text-3xl">
                                        “Đại dương không ép buộc những con sóng, nó chỉ đơn giản để chúng hiện hữu.”
                                    </blockquote>

                                    <button
                                        type="button"
                                        className="inline-flex items-center gap-2 text-xs uppercase tracking-widest text-primary transition-transform hover:translate-x-0.5"
                                    >
                                        Đọc toàn bộ
                                        <ArrowRight className="h-4 w-4" />
                                    </button>
                                </div>

                                <aside className="rounded-3xl border border-white/25 bg-white/30 p-6 backdrop-blur-md md:p-8">
                                    <h3 className="mb-6 font-display text-2xl text-on-surface">Bài tập nhanh</h3>
                                    <div className="space-y-4">
                                        {quickExercises.map((exercise) => {
                                            const Icon = exercise.icon

                                            return (
                                                <button
                                                    key={exercise.title}
                                                    type="button"
                                                    className="group flex w-full items-center gap-4 rounded-xl bg-white/40 p-4 text-left transition-all hover:bg-white/60"
                                                >
                                                    <div className={`flex h-10 w-10 items-center justify-center rounded-full ${exercise.tone}`}>
                                                        <Icon className="h-5 w-5" />
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-bold text-on-surface">{exercise.title}</p>
                                                        <p className="text-[10px] text-on-surface-variant">{exercise.duration}</p>
                                                    </div>
                                                    <ChevronRight className="ml-auto h-4 w-4 text-on-surface-variant/30 transition-transform group-hover:translate-x-1" />
                                                </button>
                                            )
                                        })}
                                    </div>
                                </aside>
                            </section>

                            <div className="mt-8 border-t border-on-surface/5 pt-10 text-center">
                                <p className="font-display text-lg italic text-on-surface/50 md:text-xl">
                                    “Học cách chữa lành là hành trình đẹp đẽ nhất của mỗi con người.”
                                </p>
                            </div>
                        </section>
                    </div>
                </div>
           
        </div>
    )
}
