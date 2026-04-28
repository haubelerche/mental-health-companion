import { ShieldCheck, FileText, BarChart3, KeyRound } from 'lucide-react'

const adminHighlights = [
    {
        title: 'Crisis logs',
        description: 'Theo dõi sự kiện SOS, phân loại mức độ và review theo khoảng thời gian.',
        icon: FileText,
    },
    {
        title: 'Aggregate dashboard',
        description: 'Xem số liệu ẩn danh cho tổ chức, trường học, và xu hướng tổng quan.',
        icon: BarChart3,
    },
    {
        title: 'Admin auth policy',
        description: 'Phiên ngắn hạn, MFA bắt buộc, và allowlist IP theo spec.',
        icon: KeyRound,
    },
]

export default function AdminDashboard() {
    return (
        <div className="auth-page">
            <div className="fixed inset-0">
                <div className="absolute inset-0 bg-serene-primary/20" />
                <div className="absolute inset-0 bg-black/10" />
            </div>

            <div className="auth-noise" />

            <main className="auth-main px-6 py-10">
                <section className="auth-card mx-auto max-w-3xl p-8 sm:p-10">
                    <header className="mb-8 flex flex-col gap-4 text-center sm:mb-10">
                        <div className="mx-auto inline-flex h-14 w-14 items-center justify-center rounded-full border border-serene-primary/20 bg-serene-primary/10 text-serene-primary">
                            <ShieldCheck className="h-7 w-7" aria-hidden="true" />
                        </div>
                        <div>
                            <h1 className="font-display text-3xl text-serene-ink sm:text-[34px]">
                                Admin workspace
                            </h1>
                            <p className="mt-2 text-sm text-serene-muted/90 sm:text-base">
                                Phiên quản trị đã sẵn sàng. Backend sẽ tiếp tục kiểm tra cookie, role và IP allowlist cho các endpoint `/admin/*`.
                            </p>
                        </div>
                    </header>

                    <div className="grid gap-4 md:grid-cols-3">
                        {adminHighlights.map((item) => {
                            const Icon = item.icon

                            return (
                                <article
                                    key={item.title}
                                    className="rounded-3xl border border-white/10 bg-white/70 p-5 shadow-[0_18px_45px_rgba(6,26,24,0.12)] backdrop-blur"
                                >
                                    <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-serene-primary/10 text-serene-primary">
                                        <Icon className="h-5 w-5" aria-hidden="true" />
                                    </div>
                                    <h2 className="text-lg font-semibold text-serene-ink">
                                        {item.title}
                                    </h2>
                                    <p className="mt-2 text-sm leading-6 text-serene-muted/90">
                                        {item.description}
                                    </p>
                                </article>
                            )
                        })}
                    </div>
                </section>
            </main>
        </div>
    )
}