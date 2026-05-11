import { useState } from 'react'
import type { ComponentProps } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import { Loader2, ShieldCheck, Info, ExternalLink, Key, Copy, Check } from 'lucide-react'
import { ApiRequestError } from '../../api/types'
import { ROUTE_PATHS } from '../../routes/paths'
import { adminAuthService } from '../../services/adminAuthService.ts'

export default function AdminLogin() {
  type FormSubmitHandler = NonNullable<ComponentProps<'form'>['onSubmit']>
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [copied, setCopied] = useState(false)

  const secretKey = "PML6ZW4Q7WC5LVTB7G362BYGP4P3ZDZN"

  const handleCopy = () => {
    navigator.clipboard.writeText(secretKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    toast.info('Đã sao chép Secret Key')
  }

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

      toast.success(`Đăng nhập admin thành công (${response.admin_id})`)
      navigate(ROUTE_PATHS.adminDashboard)
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
    <div className="auth-page min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background with animated gradient */}
      <div className="fixed inset-0">
        <div className="absolute inset-0 bg-slate-950" />
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-500/10 blur-[120px] rounded-full animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-500/10 blur-[120px] rounded-full animate-pulse" />
        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-20 pointer-events-none" />
      </div>

      <main className="relative z-10 w-full max-w-md">
        <div className="mb-10 text-center animate-in fade-in slide-in-from-top-4 duration-700">
          <Link to={ROUTE_PATHS.landing} className="text-4xl font-black text-white tracking-tighter hover:text-indigo-400 transition-colors">
            SERENE <span className="text-indigo-500">ADMIN</span>
          </Link>
          <p className="text-slate-500 text-[10px] mt-2 font-black tracking-[0.3em] uppercase">Secure Administration Access</p>
        </div>

        <section className="bg-slate-900/60 backdrop-blur-2xl border border-white/10 p-8 sm:p-10 rounded-[2.5rem] shadow-2xl animate-in zoom-in-95 duration-500">
          <header className="mb-8 text-center">
            <div className="h-14 w-14 rounded-2xl bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30 mx-auto mb-4">
              <ShieldCheck className="h-7 w-7 text-indigo-400" />
            </div>
            <h2 className="text-2xl font-bold text-white">Xác thực Quản trị</h2>
            <p className="text-slate-400 text-sm mt-1">Hệ thống yêu cầu bảo mật 2 lớp.</p>
          </header>

          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@gmail.com"
                className="w-full bg-white/5 border border-white/10 rounded-2xl px-5 py-3.5 text-white placeholder:text-slate-600 focus:border-indigo-500/50 focus:bg-white/[0.08] transition-all outline-none"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Mật khẩu</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-white/5 border border-white/10 rounded-2xl px-5 py-3.5 text-white placeholder:text-slate-600 focus:border-indigo-500/50 focus:bg-white/[0.08] transition-all outline-none"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Mã bảo mật (OTP)</label>
              <input
                type="text"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="123456"
                className="w-full bg-white/5 border border-white/10 rounded-2xl px-5 py-3.5 text-white placeholder:text-slate-600 focus:border-indigo-500/50 focus:bg-white/[0.08] transition-all outline-none font-mono tracking-[0.5em] text-center text-xl"
                maxLength={6}
                required
              />
            </div>

            {errorMessage && (
              <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs px-4 py-3 rounded-xl animate-in shake duration-300">
                {errorMessage}
              </div>
            )}

            <button type="submit" disabled={isSubmitting} className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-4 rounded-2xl transition-all shadow-lg shadow-indigo-600/20 flex items-center justify-center gap-2 group active:scale-[0.98]">
              {isSubmitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <Key className="h-5 w-5" />}
              Đăng nhập hệ thống
            </button>
          </form>

          <div className="mt-8 pt-6 border-t border-white/5">
            <div className="bg-amber-400/5 border border-amber-400/10 p-5 rounded-2xl">
              <div className="flex items-center gap-2 text-amber-400 font-bold text-[10px] uppercase tracking-widest mb-3">
                <Info size={12} /> Hướng dẫn lấy mã OTP
              </div>
              <div className="space-y-3">
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Bạn có thể dùng ứng dụng <b>Google Authenticator</b> hoặc truy cập <a href="https://2fa.live" target="_blank" className="text-amber-400 underline font-bold inline-flex items-center gap-0.5 hover:text-amber-300">2FA.live <ExternalLink size={8} /></a> và dán Secret Key dưới đây:
                </p>
                <div 
                    onClick={handleCopy}
                    className="group relative bg-black/40 p-3 rounded-xl border border-white/5 font-mono text-[11px] text-amber-400/90 break-all cursor-pointer hover:bg-black/60 transition-all flex items-center justify-between gap-2"
                >
                  <span className="truncate">{secretKey}</span>
                  {copied ? <Check size={14} className="text-emerald-400 shrink-0" /> : <Copy size={14} className="opacity-40 group-hover:opacity-100 shrink-0" />}
                  
                  {copied && (
                      <span className="absolute -top-8 left-1/2 -translate-x-1/2 bg-emerald-500 text-white text-[10px] px-2 py-1 rounded shadow-lg animate-in fade-in slide-in-from-bottom-1">
                          Copied!
                      </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>

        <footer className="mt-8 text-center animate-in fade-in duration-1000 delay-500">
           <Link to={ROUTE_PATHS.login} className="text-slate-500 hover:text-white transition-colors text-[10px] font-black uppercase tracking-widest inline-flex items-center gap-2 group">
            Quay lại User Login
            <div className="h-1 w-1 rounded-full bg-slate-500 group-hover:bg-white transition-colors" />
          </Link>
        </footer>
      </main>
    </div>
  )
}
