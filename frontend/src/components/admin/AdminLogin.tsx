
import { useState } from 'react'
import type { ComponentProps } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'react-toastify'
import { Loader2, ShieldCheck } from 'lucide-react'
import { ApiRequestError } from '../../api/types'
import { ROUTE_PATHS } from '../../routes/paths'
import { adminAuthService } from '../../services/adminAuthService.ts'

export default function AdminLogin() {
  type FormSubmitHandler = NonNullable<ComponentProps<'form'>['onSubmit']>
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit: FormSubmitHandler = async (event) => {
    event.preventDefault()
    setErrorMessage('')
    setIsSubmitting(true)

    try {
      const response = await adminAuthService.login({
        email: email.trim(),
        password,
        totp_code: totpCode.trim(),
      })

      setSubmitted(true)
      toast.success(`Đăng nhập admin thành công (${response.admin_id})`)
    } catch (error) {
      if (error instanceof ApiRequestError) {
        setErrorMessage(error.message)
        toast.error(error.message)
      } else {
        setErrorMessage('Đăng nhập admin thất bại. Vui lòng thử lại sau.')
        toast.error('Đăng nhập admin thất bại. Vui lòng thử lại sau.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="fixed inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(11,95,88,0.26),transparent_46%),linear-gradient(180deg,rgba(5,28,26,0.94)_0%,rgba(9,38,36,0.88)_100%)]" />
        <div className="absolute inset-0 bg-black/10" />
      </div>

      <div className="auth-noise" />

      <main className="auth-main px-6 py-10">
        <div className="mb-8 text-center">
          <Link to={ROUTE_PATHS.landing} className="auth-brand">
            Serene Admin
          </Link>
          <p className="auth-brand-sub">
            Internal access only
          </p>
        </div>

        <section className="auth-card max-w-md p-8 sm:p-10">
          <header className="mb-8 text-center">
            <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full border border-serene-primary/20 bg-serene-primary/10 text-serene-primary">
              <ShieldCheck className="h-6 w-6" aria-hidden="true" />
            </div>
            <h2 className="font-display text-2xl text-serene-ink sm:text-[28px]">
              Đăng nhập quản trị
            </h2>
            <p className="mt-2 text-sm text-serene-muted/90">
              Luồng này dùng endpoint riêng cho admin, bắt buộc thêm mã TOTP 6 số.
            </p>
          </header>

          <form className="space-y-6" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="admin-email" className="auth-label mb-2 pl-1 font-medium tracking-[0.3em]">
                Email admin
              </label>
              <input
                id="admin-email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="admin@example.com"
                className="auth-input-line"
                autoComplete="username"
                required
              />
            </div>

            <div>
              <label htmlFor="admin-password" className="auth-label mb-2 pl-1 font-medium tracking-[0.3em]">
                Mật khẩu
              </label>
              <input
                id="admin-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
                className="auth-input-line"
                autoComplete="current-password"
                required
              />
            </div>

            <div>
              <label htmlFor="admin-totp" className="auth-label mb-2 pl-1 font-medium tracking-[0.3em]">
                TOTP
              </label>
              <input
                id="admin-totp"
                type="text"
                value={totpCode}
                onChange={(event) => setTotpCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="123456"
                className="auth-input-line"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                required
              />
              <p className="mt-2 text-xs text-serene-muted/70">
                Mã xác thực chỉ có hiệu lực ngắn hạn theo spec.
              </p>
            </div>

            <div aria-live="polite" className="min-h-6 text-sm text-rose-600">
              {errorMessage}
            </div>

            <div className="pt-2">
              <button type="submit" disabled={isSubmitting} className="auth-cta">
                {isSubmitting ? (
                  <span className="inline-flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Đang xác thực...
                  </span>
                ) : (
                  'Đăng nhập admin'
                )}
              </button>
            </div>
          </form>

          <footer className="mt-10 space-y-4 text-center">
            {submitted ? (
              <p className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-800">
                Phiên admin đã được cấp cookie xác thực. Bạn có thể tiếp tục tới các trang nội bộ.
              </p>
            ) : null}
            <p className="text-xs tracking-tight text-serene-muted/60">
              Cần quay lại khu vực người dùng?{' '}
              <Link to={ROUTE_PATHS.login} className="auth-link">
                Đăng nhập thường
              </Link>
            </p>
          </footer>
        </section>
      </main>
    </div>
  )
}