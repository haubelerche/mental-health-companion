import { useEffect, useMemo, useState } from 'react'
import type { ComponentProps } from 'react'
import { ArrowLeft, KeyRound, Mail } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import { ApiRequestError } from '../../api/types'
import bg2 from '../../assets/backgrounds/bg-morning.png'
import { ROUTE_PATHS } from '../../routes/paths'
import { authService } from '../../services/authService'

export default function Forget() {
    type FormSubmitHandler = NonNullable<ComponentProps<'form'>['onSubmit']>
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()

    const [step, setStep] = useState<1 | 2>(1)
    const [isSubmitting, setIsSubmitting] = useState(false)

    const [email, setEmail] = useState('')
    const [token, setToken] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')

    const strongPasswordRegex = useMemo(
        () => /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/,
        [],
    )

    useEffect(() => {
        const tokenFromQuery = searchParams.get('token')
        if (!tokenFromQuery) return
        setToken(tokenFromQuery)
        setStep(2)
    }, [searchParams])

    const handleRequestReset: FormSubmitHandler = async (event) => {
        event.preventDefault()

        setIsSubmitting(true)
        try {
            await authService.forgotPassword({
                email: email.trim(),
            })
            toast.success('Nếu email tồn tại, liên kết đặt lại mật khẩu đã được gửi.')
            setStep(2)
        } catch (error) {
            if (error instanceof ApiRequestError) {
                toast.error(error.message)
            } else {
                toast.error('Không thể gửi yêu cầu. Vui lòng thử lại sau.')
            }
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleResetPassword: FormSubmitHandler = async (event) => {
        event.preventDefault()

        if (!token.trim()) {
            toast.error('Vui lòng nhập mã token reset từ email.')
            return
        }

        if (!strongPasswordRegex.test(newPassword)) {
            toast.error('Mật khẩu phải có ít nhất 8 ký tự, gồm chữ hoa, chữ thường, số và ký tự đặc biệt.')
            setNewPassword('')
            setConfirmPassword('')
            return
        }

        if (newPassword !== confirmPassword) {
            toast.error('Mật khẩu xác nhận không khớp.')
            return
        }

        setIsSubmitting(true)
        try {
            await authService.resetPassword({
                token: token.trim(),
                new_password: newPassword,
            })
            toast.success('Đổi mật khẩu thành công. Vui lòng đăng nhập lại.')
            navigate(ROUTE_PATHS.login)
        } catch (error) {
            if (error instanceof ApiRequestError) {
                toast.error(error.message)
            } else {
                toast.error('Đặt lại mật khẩu thất bại. Vui lòng thử lại sau.')
            }
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <div className="auth-page">
            <div className="fixed inset-0">
                <img
                    alt="Calm ocean backdrop"
                    src={bg2}
                    className="auth-bg-image"
                />
                <div className="absolute inset-0 bg-serene-primary/10 mix-blend-overlay" />
                <div className="absolute inset-0 bg-linear-to-b from-white/5 via-transparent to-white/10" />
            </div>

            <main className="auth-main px-6 py-10">
                <section className="auth-card max-w-xl p-8 sm:p-10">
                    <header className="mb-8 text-center">
                        <div className="mb-5 flex items-center justify-center gap-3">
                            <Link to={ROUTE_PATHS.login}>
                                <ArrowLeft className="h-5 w-5 text-serene-muted transition hover:text-serene-ink" />
                            </Link>
                            <h1 className="font-display text-3xl text-serene-ink sm:text-4xl">
                                Quên mật khẩu
                            </h1>
                        </div>
                        <p className="text-xs uppercase tracking-[0.2em] text-serene-muted/80">
                            Hoàn tất theo 2 bước rõ ràng
                        </p>
                    </header>

                    <div className="mb-8 rounded-2xl bg-serene-surface/50 p-4">
                        <div className="flex items-center justify-between gap-4 text-xs uppercase tracking-[0.15em]">
                            <div className={`flex items-center rounded-full p-3 gap-2 ${step === 1 ? 'text-serene-surface bg-serene-primary' : 'text-serene-muted/80'}`}>
                                <span className={`grid h-7 w-7 place-items-center rounded-full border ${step === 1 ? 'border-serene-primary bg-serene-accent/40' : 'border-serene-outline/50'}`}>
                                    <Mail className="h-4 w-4" />
                                </span>
                                <span>1. Nhập email</span>
                            </div>

                            <div className="h-px flex-1 bg-serene-outline/40" />

                            <div className={`flex items-center rounded-full p-3 gap-2 ${step === 2 ? 'text-serene-surface bg-serene-primary' : 'text-serene-muted/80'}`}>
                                <span className={`grid h-7 w-7 place-items-center rounded-full border ${step === 2 ? 'border-serene-primary bg-serene-accent/40' : 'border-serene-outline/50'}`}>
                                    <KeyRound className="h-4 w-4" />
                                </span>
                                <span>2. Mật khẩu mới</span>
                            </div>
                        </div>
                    </div>

                    {step === 1 ? (
                        <form className="space-y-6" onSubmit={handleRequestReset}>
                            <div className="space-y-1">
                                <label htmlFor="email" className="auth-label ml-1">
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

                            <div className="auth-disclaimer">
                                <p className="text-xs leading-relaxed text-serene-muted sm:text-sm">
                                    Sau khi gửi, hãy kiểm tra email để lấy mã token reset hoặc liên kết đặt lại mật khẩu.
                                </p>
                            </div>

                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="auth-cta"
                            >
                                {isSubmitting ? 'Đang gửi yêu cầu...' : 'Tiếp tục'}
                            </button>
                        </form>
                    ) : (
                        <form className="space-y-6" onSubmit={handleResetPassword}>
                            <div className="space-y-1">
                                <label htmlFor="token" className="auth-label ml-1">
                                    Token reset từ email
                                </label>
                                <input
                                    id="token"
                                    type="text"
                                    value={token}
                                    onChange={(event) => setToken(event.target.value)}
                                    placeholder="dán token hoặc mở link từ email"
                                    className="auth-input-soft"
                                    required
                                />
                            </div>

                            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                                <div className="space-y-1">
                                    <label htmlFor="newPassword" className="auth-label ml-1">
                                        Mật khẩu mới
                                    </label>
                                    <input
                                        id="newPassword"
                                        type="password"
                                        value={newPassword}
                                        onChange={(event) => setNewPassword(event.target.value)}
                                        placeholder="••••••••"
                                        className="auth-input-soft"
                                        required
                                    />
                                </div>

                                <div className="space-y-1">
                                    <label htmlFor="confirmPassword" className="auth-label ml-1">
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

                            <div className="auth-disclaimer">
                                <p className="text-xs leading-relaxed text-serene-muted sm:text-sm">
                                    Mật khẩu mới cần tối thiểu 8 ký tự, có chữ hoa, chữ thường, số và ký tự đặc biệt.
                                </p>
                            </div>

                            <div className="flex gap-3 justify-center">
                                {/* <button
                                    type="button"
                                    onClick={() => setStep(1)}
                                    className="w-1/3 rounded-full border border-serene-outline/60 px-4 py-3 text-xs uppercase tracking-[0.2em] text-serene-muted transition hover:border-serene-primary hover:text-serene-primary"
                                >
                                    Quay lại
                                </button> */}
                            
                                <button
                                    type="submit"
                                    disabled={isSubmitting}
                                    className="auth-cta w-2/3"
                                >
                                    {isSubmitting ? 'Đang cập nhật...' : 'Đổi mật khẩu'}
                                </button>
                            </div>
                        </form>
                    )}

                    <footer className="mt-8 text-center">
                        <p className="text-xs tracking-tight text-serene-muted/70">
                            Đã nhớ mật khẩu?{' '}
                            <Link to={ROUTE_PATHS.login} className="auth-link">
                                Đăng nhập
                            </Link>
                        </p>
                    </footer>
                </section>
            </main>
        </div>
    )
}
