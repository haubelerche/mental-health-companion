import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import bg from '../../assets/bg.png'
export default function Login() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const navigate = useNavigate()

    const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        console.log({ email, password })
        navigate('/home')
    }

    return (
        <div className="relative min-h-screen overflow-hidden bg-[#faf9f5] text-[#2f342e]">
            <div className="fixed inset-0">
                <img
                    alt="Serene dawn"
                    src={bg}
                    className="h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-white/10" />
                <div className="absolute inset-0 bg-linear-to-b from-white/5 via-transparent to-white/10" />
            </div>

            <div className="fixed inset-0 pointer-events-none opacity-[0.03] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />

            <main className="relative z-10 flex min-h-screen flex-col items-center justify-center px-6 py-10">
                <div className="mb-8 text-center">
                    <h1 className="font-display text-7xl italic tracking-tight text-[#2f342e] sm:text-8xl">
                        Serene
                    </h1>
                    <p className="mt-3 text-[10px] uppercase tracking-[0.35em] text-[#2f342e]/60">
                        Digital Sanctuary
                    </p>
                </div>

                <section className="w-full max-w-md rounded-4xl bg-white/65 p-8 shadow-[0_40px_60px_rgba(47,52,46,0.08)] backdrop-blur-2xl sm:p-10">
                    <header className="mb-10 text-center">
                        <h2 className="font-display text-2xl text-[#2f342e] sm:text-[28px]">
                            Chào mừng bạn trở lại
                        </h2>
                        <p className="mt-2 text-sm text-[#5c605a]/90">
                            Tìm lại sự bình yên trong tâm hồn.
                        </p>
                    </header>

                    <form className="space-y-8" onSubmit={handleSubmit}>
                        <div>
                            <label
                                htmlFor="email"
                                className="mb-2 block pl-1 text-[10px] font-medium uppercase tracking-[0.3em] text-[#5c605a]"
                            >
                                Email
                            </label>
                            <input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(event) => setEmail(event.target.value)}
                                placeholder="your@email.com"
                                className="w-full border-0 border-b border-[#afb3ac]/30 bg-transparent px-1 py-3 text-[#2f342e] outline-none transition placeholder:text-[#5c605a]/30 focus:border-[#4d6359] focus:ring-0"
                            />
                        </div>

                        <div>
                            <div className="mb-2 flex items-end justify-between gap-3">
                                <label
                                    htmlFor="password"
                                    className="pl-1 text-[10px] font-medium uppercase tracking-[0.3em] text-[#5c605a]"
                                >
                                    Mật khẩu
                                </label>
                                <button
                                    type="button"
                                    className="text-[10px] font-medium uppercase tracking-[0.3em] text-[#4d6359]/60 transition hover:text-[#4d6359]"
                                >
                                    Quên?
                                </button>
                            </div>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                                placeholder="••••••••"
                                className="w-full border-0 border-b border-[#afb3ac]/30 bg-transparent px-1 py-3 text-[#2f342e] outline-none transition placeholder:text-[#5c605a]/30 focus:border-[#4d6359] focus:ring-0"
                            />
                        </div>

                        <div className="pt-2">
                            <button
                                type="submit"
                                className="w-full rounded-full bg-linear-to-b from-[#4d6359] to-[#42574d] px-6 py-4 font-medium text-[#e5fdf0] shadow-[0_18px_30px_rgba(47,52,46,0.14)] transition duration-300 hover:scale-[1.02] hover:shadow-[0_24px_36px_rgba(47,52,46,0.18)] active:scale-[0.98]"
                            >
                                Bước vào
                            </button>
                        </div>
                    </form>

                    <footer className="mt-12 text-center">
                        <p className="text-xs tracking-tight text-[#5c605a]/60">
                            Bạn chưa có tài khoản?{' '}
                            <Link
                                to="/register"
                                className="font-semibold text-[#4d6359] decoration-2 underline-offset-4 transition hover:underline"
                            >
                                Tham gia ngay
                            </Link>
                        </p>
                    </footer>
                </section>

                <footer className="mt-8 flex items-center gap-4 text-[10px] uppercase tracking-[0.3em] text-[#2f342e] font-bold">
                    <span>© Group 039 VinAI</span>
                    <span className="h-1 w-1 rounded-full bg-[#afb3ac]" />
                    <button type="button" className="transition hover:text-[#4d6359]">
                        Trợ giúp
                    </button>
                    <span className="h-1 w-1 rounded-full bg-[#afb3ac]" />
                    <button type="button" className="transition hover:text-[#4d6359]">
                        Quyền riêng tư
                    </button>
                </footer>
            </main>
        </div>
    )
}