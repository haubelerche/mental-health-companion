import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import bg from '../../assets/bg.png'

export default function Register() {
    const [fullName, setFullName] = useState('')
    const [school, setSchool] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [acknowledged, setAcknowledged] = useState(false)
    const navigate = useNavigate()

    const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        if (!acknowledged || !fullName || !school || !email || !password || password !== confirmPassword) {
            return
        }

        console.log({ fullName, school, email })
        navigate('/home')
    }

    return (
        <div className="relative min-h-screen overflow-hidden bg-[#faf9f5] text-[#2f342e]">
            <div className="fixed inset-0">
                <img
                    alt="Dawn sky over ocean"
                    src={bg}
                    className="h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-[#4d6359]/10 mix-blend-overlay" />
            </div>

            <nav className="fixed top-0 z-20 w-full px-8 py-6">
                <div className="font-display text-3xl italic text-[#2f342e]">Serene</div>
            </nav>

            <main className="relative z-10 flex min-h-screen items-center justify-center px-4 py-24">
                <section className="w-full max-w-xl rounded-4xl bg-[#faf9f5]/65 p-8 shadow-[0_40px_80px_rgba(47,52,46,0.08)] backdrop-blur-2xl sm:p-12">
                    <header className="mb-10 text-center">
                        <h1 className="font-display text-4xl text-[#2f342e] sm:text-5xl">Bắt đầu hành trình</h1>
                        <p className="mt-3 text-xs uppercase tracking-[0.22em] text-[#5c605a]/80">
                            Tạo tài khoản cá nhân của bạn
                        </p>
                    </header>

                    <form className="space-y-6" onSubmit={handleSubmit}>
                        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                            <div className="space-y-1">
                                <label className="ml-1 block text-[10px] uppercase tracking-[0.22em] text-[#5c605a]" htmlFor="fullName">
                                    Họ và Tên
                                </label>
                                <input
                                    id="fullName"
                                    type="text"
                                    value={fullName}
                                    onChange={(event) => setFullName(event.target.value)}
                                    placeholder="Nguyễn Văn A"
                                    className="w-full rounded-2xl border-none bg-[#edeee8]/65 px-4 py-3 text-[#2f342e] placeholder:text-[#787c75]/70 focus:ring-1 focus:ring-[#4d6359]"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="ml-1 block text-[10px] uppercase tracking-[0.22em] text-[#5c605a]" htmlFor="school">
                                    Trường Đại học
                                </label>
                                <input
                                    id="school"
                                    type="text"
                                    value={school}
                                    onChange={(event) => setSchool(event.target.value)}
                                    placeholder="Đại học Bách Khoa Hà Nội"
                                    className="w-full rounded-2xl border-none bg-[#edeee8]/65 px-4 py-3 text-[#2f342e] placeholder:text-[#787c75]/70 focus:ring-1 focus:ring-[#4d6359]"
                                />
                            </div>
                        </div>

                        <div className="space-y-1">
                            <label className="ml-1 block text-[10px] uppercase tracking-[0.22em] text-[#5c605a]" htmlFor="email">
                                Email
                            </label>
                            <input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(event) => setEmail(event.target.value)}
                                placeholder="email@hust.edu.vn"
                                className="w-full rounded-2xl border-none bg-[#edeee8]/65 px-4 py-3 text-[#2f342e] placeholder:text-[#787c75]/70 focus:ring-1 focus:ring-[#4d6359]"
                            />
                        </div>

                        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                            <div className="space-y-1">
                                <label className="ml-1 block text-[10px] uppercase tracking-[0.22em] text-[#5c605a]" htmlFor="password">
                                    Mật khẩu
                                </label>
                                <input
                                    id="password"
                                    type="password"
                                    value={password}
                                    onChange={(event) => setPassword(event.target.value)}
                                    placeholder="••••••••"
                                    className="w-full rounded-2xl border-none bg-[#edeee8]/65 px-4 py-3 text-[#2f342e] placeholder:text-[#787c75]/70 focus:ring-1 focus:ring-[#4d6359]"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="ml-1 block text-[10px] uppercase tracking-[0.22em] text-[#5c605a]" htmlFor="confirmPassword">
                                    Xác nhận mật khẩu
                                </label>
                                <input
                                    id="confirmPassword"
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(event) => setConfirmPassword(event.target.value)}
                                    placeholder="••••••••"
                                    className="w-full rounded-2xl border-none bg-[#edeee8]/65 px-4 py-3 text-[#2f342e] placeholder:text-[#787c75]/70 focus:ring-1 focus:ring-[#4d6359]"
                                />
                            </div>
                        </div>

                        <div className="rounded-2xl border-l-2 border-[#4d6359]/30 bg-[#d0e8db]/20 p-4">
                            <label className="flex items-start gap-3 text-xs leading-relaxed text-[#5c605a] sm:text-sm" htmlFor="disclaimer">
                                <input
                                    id="disclaimer"
                                    type="checkbox"
                                    checked={acknowledged}
                                    onChange={(event) => setAcknowledged(event.target.checked)}
                                    className="mt-0.5 h-5 w-5 rounded border-[#afb3ac] bg-[#faf9f5]/50 text-[#4d6359] focus:ring-[#4d6359]"
                                />
                                <span>
                                    Mình hiểu <span className="font-semibold text-[#4d6359]">Serene</span> là AI đồng hành, không phải bác sĩ. Trong trường hợp khẩn cấp, mình sẽ gọi <span className="font-bold text-[#2f342e]">1800-599-920</span> hoặc <span className="font-bold text-[#2f342e]">115</span>.
                                </span>
                            </label>
                        </div>

                        <button
                            type="submit"
                            disabled={!acknowledged}
                            className="w-full rounded-full bg-[#4d6359] py-4 text-sm font-medium text-[#e5fdf0] shadow-lg shadow-[#4d6359]/20 transition duration-300 hover:bg-[#42574d] hover:scale-[1.01] active:scale-95 disabled:cursor-not-allowed disabled:opacity-70"
                        >
                            Bắt đầu hành trình
                        </button>

                        <p className="pt-1 text-center text-sm text-[#5c605a]">
                            Đã có tài khoản?{' '}
                            <Link to="/login" className="font-semibold text-[#4d6359] hover:underline">
                                Đăng nhập ngay
                            </Link>
                        </p>
                    </form>
                </section>
            </main>

            <footer className="relative z-10 flex w-full flex-col items-center justify-between gap-4 px-8 py-8 text-xs uppercase tracking-[0.2em] text-[#5c605a]/75 md:flex-row">
                <div>© 2026 Serene. All Rights Reserved.</div>
                <div className="rounded-full bg-[#faf9f5]/40 px-4 py-2 backdrop-blur-md">
                    Hotline: <span className="font-bold text-[#2f342e]">1800-599-920</span>
                </div>
            </footer>
        </div>
    )
}