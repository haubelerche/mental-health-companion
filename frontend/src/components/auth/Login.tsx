import { useState } from 'react'
import type { ComponentProps } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import bg from '../../assets/bg.png'
import { api } from '../../lib/api'
export default function Login() {
    type FormSubmitHandler = NonNullable<ComponentProps<'form'>['onSubmit']>
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const navigate = useNavigate()

    const handleSubmit: FormSubmitHandler = async (event) => {
        event.preventDefault()
        if (submitting) return
        setSubmitting(true)
        try {
            await api.login({ email, password })
            await api.ensureCsrfToken()
            const policy = await api.getCurrentPolicy()
            await api.acknowledgePolicy(policy.version)
            toast.success('Đăng nhập thành công')
            navigate('/serene/chat')
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Đăng nhập thất bại')
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div className="auth-page">
            <div className="fixed inset-0">
                <img
                    alt="Serene dawn"
                    src={bg}
                    className="auth-bg-image"
                />
                <div className="absolute inset-0 bg-white/10" />
                <div className="absolute inset-0 bg-linear-to-b from-white/5 via-transparent to-white/10" />
            </div>

            <div className="auth-noise" />

            <main className="auth-main px-6 py-10">
                <div className="mb-8 text-center">
                    <h1 className="auth-brand">
                        Serene
                    </h1>
                    <p className="auth-brand-sub">
                        Digital Sanctuary
                    </p>
                </div>

                <section className="auth-card max-w-md p-8 sm:p-10">
                    <header className="mb-10 text-center">
                        <h2 className="font-display text-2xl text-serene-ink sm:text-[28px]">
                            Chào mừng bạn trở lại
                        </h2>
                        <p className="mt-2 text-sm text-serene-muted/90">
                            Tìm lại sự bình yên trong tâm hồn.
                        </p>
                    </header>

                    <form className="space-y-8" onSubmit={handleSubmit}>
                        <div>
                            <label
                                htmlFor="email"
                                className="auth-label mb-2 pl-1 font-medium tracking-[0.3em]"
                            >
                                Email
                            </label>
                            <input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(event) => setEmail(event.target.value)}
                                placeholder="your@email.com"
                                className="auth-input-line"
                            />
                        </div>

                        <div>
                            <div className="mb-2 flex items-end justify-between gap-3">
                                <label
                                    htmlFor="password"
                                    className="auth-label pl-1 font-medium tracking-[0.3em]"
                                >
                                    Mật khẩu
                                </label>
                                <button
                                    type="button"
                                    className="text-[10px] font-medium uppercase tracking-[0.3em] text-serene-primary/60 transition hover:text-serene-primary"
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
                                className="auth-input-line"
                            />
                        </div>

                        <div className="pt-2">
                            <button
                                type="submit"
                                className="auth-cta disabled:cursor-not-allowed disabled:opacity-70"
                                disabled={submitting}
                            >
                                {submitting ? 'Đang đăng nhập...' : 'Bước vào'}
                            </button>
                        </div>
                    </form>

                    <footer className="mt-12 text-center">
                        <p className="text-xs tracking-tight text-serene-muted/60">
                            Bạn chưa có tài khoản?{' '}
                            <Link
                                to="/register"
                                className="auth-link"
                            >
                                Tham gia ngay
                            </Link>
                        </p>
                    </footer>
                </section>

         
            </main>
        </div>
    )
}