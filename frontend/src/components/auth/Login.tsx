import { useState } from 'react'
import type { ComponentProps } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import { ArrowRight } from 'lucide-react'
import { ApiRequestError } from '../../api/types'
import { useAuth } from '../../hooks/useAuth'
import { authService } from '../../services/authService'
import { ROUTE_PATHS } from '../../routes/paths'
import LogoGoogle from '../../assets/branding/icons8-google-logo-100.png'
import LogoFacebook from '../../assets/branding/icons8-facebook-96.png'
import bgLogin from '../../assets/motion/login-signup.gif'
import '../pages/landing/landing.css'

export default function Login() {
    type FormSubmitHandler = NonNullable<ComponentProps<'form'>['onSubmit']>
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [oauthLoading, setOauthLoading] = useState<null | 'google' | 'facebook'>(null)
    const navigate = useNavigate()
    const { login, isLoading } = useAuth()

    const handleOAuthLogin = (provider: 'google' | 'facebook') => {
        const returnTo = `${window.location.origin}${ROUTE_PATHS.oauthCallback}`
        const startUrl = authService.startOAuth(provider, returnTo)
        setOauthLoading(provider)
        window.location.assign(startUrl)
    }

    const handleSubmit: FormSubmitHandler = async (event) => {
        event.preventDefault()
        const clickStartedAt = performance.now()

        try {
            await login({
                email: email.trim(),
                password,
            })

            toast.success('Đăng nhập thành công!')
            navigate(ROUTE_PATHS.home)
            console.info('[auth-metrics] login.click_to_navigate_ms', Math.round(performance.now() - clickStartedAt))
        } catch (error) {
            console.info('[auth-metrics] login.failed_ms', Math.round(performance.now() - clickStartedAt))
            if (error instanceof ApiRequestError) {
                toast.error(error.message)
                return
            }

            toast.error('Đăng nhập thất bại. Vui lòng thử lại sau.')
        }
    }

    return (
        <div className="auth-page serene-landing">
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
     
            </div>

            <div className="auth-noise" />

            <main className="auth-main">
                <div className="mb-3 text-center">
                    <Link to={ROUTE_PATHS.landing} className="pixel-headline" 
                      style={{
                        fontFamily: 'var(--font-pixel)',
                        fontSize: 'clamp(6.5rem, 2vw, 4.5rem)',
                        color: 'var(--yellow)',
                        textDecoration: 'none',
                        textShadow: '2px 2px 0 rgba(2,8,18,0.8)',
                        flexShrink: 0,
                        fontWeight: '800',
                        letterSpacing: '2px',
                    }}>
                        Serene
                    </Link>
                </div>

                <div className="auth-card max-w-xl p-8 sm:p-10">
                    <header className="mb-10 text-center">
                        <h1 className="font-display text-4xl text-serene-ink sm:text-5xl">Chào mừng bạn trở lại</h1>
                       <p className="mt-3 text-xs uppercase tracking-[0.22em] text-serene-muted/80">
                            Tìm lại sự bình yên trong tâm hồn
                        </p>
                    </header>

                
                    <form className="space-y-6" onSubmit={handleSubmit}>
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
                                required
                            />
                        </div>

                        <div>

                            <label
                                htmlFor="password"
                                className="auth-label pl-1 font-medium tracking-[0.3em]"
                            >
                                Mật khẩu
                            </label>

                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                                placeholder="••••••••"
                                className="auth-input-line"
                                required

                            />

                        </div>
                        <div>
                            <Link
                                to={ROUTE_PATHS.forget}
                                type="button"
                                className="text-[10px] font-medium uppercase tracking-[0.3em] text-serene-primary transition hover:text-serene-primary"
                            >
                                Quên mật khẩu?
                            </Link>
                        </div>
                        <div className="pt-2">
                            <button
                                type="submit"
                                disabled={isLoading || Boolean(oauthLoading)}
                                className="auth-cta cursor-pointer"
                            >
                                <span className="inline-flex items-center justify-center gap-2">
                                    {isLoading ? 'Đang đăng nhập...' : 'Bước vào'}
                                    {!isLoading && <ArrowRight className="h-4 w-4" />}
                                </span>
                            </button>
                        </div>
                    </form>
                    
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
                            className=" inline-flex items-center justify-center gap-3 rounded-2xl border border-serene-outline/70 cursor-pointer bg-white/70 px-4 py-2 text-sm font-medium text-serene-ink transition hover:border-serene-primary/50 hover:bg-white disabled:cursor-not-allowed disabled:opacity-70"
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

                    <footer className="mt-12 text-center">
                        <p className="text-xs tracking-tight text-serene-muted/60">
                            Bạn chưa có tài khoản?{' '}
                            <Link
                                to={ROUTE_PATHS.register}
                                className="auth-link"
                            >
                                Tham gia ngay
                            </Link>
                        </p>
                    </footer>
                </div>


            </main>
        </div>
    )
}
