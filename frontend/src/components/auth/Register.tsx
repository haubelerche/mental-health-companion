import { useState } from 'react'
import type { ComponentProps } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import { ApiRequestError } from '../../api/types'
import { useAuth } from '../../hooks/useAuth'
import { ROUTE_PATHS } from '../../routes/paths'
import { ArrowLeft } from 'lucide-react'
import { authService } from '@/services/authService'
import LogoGoogle from '../../assets/branding/icons8-google-logo-100.png'
import LogoFacebook from '../../assets/branding/icons8-facebook-96.png'
import bgLogin from '../../assets/motion/login-signup.gif'

export default function Register() {
    type FormSubmitHandler = NonNullable<ComponentProps<'form'>['onSubmit']>
    const [fullName, setFullName] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [voiceConsent] = useState<boolean>(false)
    const navigate = useNavigate()
    const { signup, isLoading } = useAuth()
    const [oauthLoading, setOauthLoading] = useState<null | 'google' | 'facebook'>(null)

    const handleOAuthLogin = (provider: 'google' | 'facebook') => {
        const returnTo = `${window.location.origin}${ROUTE_PATHS.oauthCallback}`
        const startUrl = authService.startOAuth(provider, returnTo)
        setOauthLoading(provider)
        window.location.assign(startUrl)
    }

    const strongPasswordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/

    const handleSubmit: FormSubmitHandler = async (event) => {
        event.preventDefault()
        const clickStartedAt = performance.now()

        if (!strongPasswordRegex.test(password)) {
            toast.error('Mật khẩu phải có ít nhất 8 ký tự, gồm chữ hoa, chữ thường, số và ký tự đặc biệt.')
            setPassword('')
            setConfirmPassword('')
            return
        }

        if (password !== confirmPassword) {
            toast.error('Mật khẩu xác nhận không khớp.')
            return
        }
        try {
            const res = await signup({
                display_name: fullName.trim(),
                email: email.trim(),
                password,
                disclaimer_accepted: true,
                voice_consent: voiceConsent,
            })
            if (res.verification_required) {
                toast.success(res.message || 'Đăng ký thành công. Vui lòng kiểm tra email để xác thực tài khoản.')
            } else {
                toast.success('Đăng ký thành công. Chào mừng bạn đến với Serene!')
            }
            navigate(ROUTE_PATHS.onboarding)
            console.info('[auth-metrics] signup.click_to_navigate_ms', Math.round(performance.now() - clickStartedAt))
        } catch (error) {
            console.info('[auth-metrics] signup.failed_ms', Math.round(performance.now() - clickStartedAt))
            if (error instanceof ApiRequestError) {
                toast.error(error.message)
                return
            }

            toast.error('Đăng ký thất bại. Vui lòng thử lại sau.')
        }
    }

    return (
        <div className="auth-page">
            <div className="fixed inset-0">
                <div
                    className="serene-fullscreen-motion-bg serene-fullscreen-motion-bg--absolute h-full w-full"
                    style={{
                        backgroundImage: `url('${bgLogin.replace(/'/g, "%27")}')`,
                        backgroundSize: 'cover',
                        backgroundPosition: 'center',
                        backgroundRepeat: 'no-repeat',
                    }}
                    aria-hidden
                />
                <div className="absolute inset-0 bg-serene-primary/10 mix-blend-overlay" />
            </div>

            <nav className="fixed top-0 z-20 w-full px-8 py-6">
                <Link to={ROUTE_PATHS.landing} className="font-display text-3xl italic text-serene-ink">Serene</Link>
            </nav>

            <main className="auth-main">
                <section className="auth-card max-w-xl p-8 sm:p-12">
                    <header className="mb-10 text-center">
                        <div className="flex items-center justify-center gap-3">
                            <Link to={ROUTE_PATHS.login} >
                                <ArrowLeft className="h-6 w-6" />
                            </Link>
                            <h1 className="font-display text-4xl text-serene-ink sm:text-5xl">Bắt đầu hành trình</h1>
                        </div>
                        <p className="mt-3 text-xs uppercase tracking-[0.22em] text-serene-muted/80">
                            Tạo tài khoản cá nhân của bạn
                        </p>
                    </header>

                    <form className="space-y-6" onSubmit={handleSubmit}>

                        <div className="space-y-1">
                            <label className="auth-label ml-1" htmlFor="fullName">
                                Họ và Tên
                            </label>
                            <input
                                id="fullName"
                                type="text"
                                value={fullName}
                                onChange={(event) => setFullName(event.target.value)}
                                placeholder="Nguyễn Văn A"
                                className="auth-input-soft"
                                required
                            />
                        </div>



                        <div className="space-y-1">
                            <label className="auth-label ml-1" htmlFor="email">
                                Email
                            </label>
                            <input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(event) => setEmail(event.target.value)}
                                placeholder="email của bạn..."
                                className="auth-input-soft"
                                required
                            />
                        </div>

                        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                            <div className="space-y-1">
                                <label className="auth-label ml-1" htmlFor="password">
                                    Mật khẩu
                                </label>
                                <input
                                    id="password"
                                    type="password"
                                    value={password}
                                    onChange={(event) => setPassword(event.target.value)}
                                    placeholder="••••••••"
                                    className="auth-input-soft"
                                    required
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="auth-label ml-1" htmlFor="confirmPassword">
                                    Xác nhận mật khẩu
                                </label>
                                <input
                                    id="confirmPassword"
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(event) => setConfirmPassword(event.target.value)}
                                    placeholder="••••••••"
                                    className="auth-input-soft"
                                    required
                                />
                            </div>
                        </div>

                      

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="auth-cta"
                        >
                            {isLoading ? 'Đang tạo tài khoản...' : 'Bắt đầu hành trình'}
                        </button>
                         <div className="my-8 flex items-center gap-4 text-[10px] uppercase tracking-[0.32em] text-serene-muted">
                        <span className="h-px flex-1 bg-serene-outline" />
                        <span>Hoặc</span>
                        <span className="h-px flex-1 bg-serene-outline" />
                    </div>

                    <div className="flex flex-col gap-4">
                        <button
                            type="button"
                            onClick={() => handleOAuthLogin('google')}
                            disabled={Boolean(oauthLoading)}
                            className="inline-flex items-center justify-center gap-3 rounded-2xl border border-serene-outline/70 cursor-pointer bg-white/70 px-4 py-2 text-sm font-medium text-serene-ink transition hover:border-serene-primary/50 hover:bg-white disabled:cursor-not-allowed disabled:opacity-70"
                        >
                            <img src={LogoGoogle} alt="Google" className="h-7 w-7" />
                            {oauthLoading === 'google' ? 'Đang mở Google...' : 'Tiếp tục với Google'}
                        </button>
                        <button
                            type="button"
                            onClick={() => handleOAuthLogin('facebook')}
                            disabled={Boolean(oauthLoading)}
                            className="inline-flex items-center justify-center gap-3 rounded-2xl border border-serene-outline/70 cursor-pointer bg-white/70 px-4 py-2 text-sm font-medium text-serene-ink transition hover:border-serene-primary/50 hover:bg-white disabled:cursor-not-allowed disabled:opacity-70"
                        >
                            <img src={LogoFacebook} alt="Facebook" className="h-7 w-7" />
                            {oauthLoading === 'facebook' ? 'Đang mở Facebook...' : 'Tiếp tục với Facebook'}
                        </button>
                    </div>

                        <p className="pt-1 text-center text-sm text-serene-muted">
                            Đã có tài khoản?{' '}
                            <Link to={ROUTE_PATHS.login} className="auth-link">
                                Đăng nhập ngay
                            </Link>
                        </p>
                    </form>
                </section>
            </main>

            <footer className="auth-footer-meta">
                <div>© 2026 Serene. All Rights Reserved.</div>
                <div className="rounded-full bg-serene-bg/40 px-4 py-2 backdrop-blur-md">
                    Hotline: <span className="font-bold text-serene-ink">1800-599-920</span>
                </div>
            </footer>
        </div>
    )
}
