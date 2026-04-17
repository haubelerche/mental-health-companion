import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import bg2 from '../../assets/bg2.png'

export default function Register() {
    const [fullName, setFullName] = useState('')
    const [school, setSchool] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [acknowledged, setAcknowledged] = useState(false)
    const navigate = useNavigate()


    const strongPasswordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/

    const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault()

        if (!strongPasswordRegex.test(password)) {
            toast.error('Mật khẩu phải có ít nhất 8 ký tự, gồm chữ hoa, chữ thường, số và ký tự đặc biệt.')
            setPassword('')
            setConfirmPassword('')
            return
        }

        if (!confirmPassword) {
            toast.error('Vui lòng xác nhận mật khẩu.')
            return
        }

        if (password !== confirmPassword) {
            toast.error('Mật khẩu xác nhận không khớp.')
            return
        }


        console.log({ fullName, school, email })
        toast.success('Đăng ký thành công. Chào mừng bạn đến với Serene!')
        navigate('/home')
    }

    return (
        <div className="auth-page">
            <div className="fixed inset-0">
                <img
                    alt="Dawn sk over oceany"
                    src={bg2}
                    className="auth-bg-image"
                />
                <div className="absolute inset-0 bg-serene-primary/10 mix-blend-overlay" />
            </div>

            <nav className="fixed top-0 z-20 w-full px-8 py-6">
                <div className="font-display text-3xl italic text-serene-ink">Serene</div>
            </nav>

            <main className="auth-main">
                <section className="auth-card max-w-xl p-8 sm:p-12">
                    <header className="mb-10 text-center">
                        <h1 className="font-display text-4xl text-serene-ink sm:text-5xl">Bắt đầu hành trình</h1>
                        <p className="mt-3 text-xs uppercase tracking-[0.22em] text-serene-muted/80">
                            Tạo tài khoản cá nhân của bạn
                        </p>
                    </header>

                    <form className="space-y-6" onSubmit={handleSubmit}>
                        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
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
                                <label className="auth-label ml-1" htmlFor="school">
                                    Trường Đại học
                                </label>
                                <input
                                    id="school"
                                    type="text"
                                    value={school}
                                    onChange={(event) => setSchool(event.target.value)}
                                    placeholder="Đại học Bách Khoa Hà Nội"
                                    className="auth-input-soft"
                                    required
                                />
                            </div>
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
                                placeholder="email@hust.edu.vn"
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

                        <div className="auth-disclaimer">
                            <label className="flex items-start gap-3 text-xs leading-relaxed text-serene-muted sm:text-sm" htmlFor="disclaimer">
                                <input
                                    id="disclaimer"
                                    type="checkbox"
                                    checked={acknowledged}
                                    onChange={(event) => setAcknowledged(event.target.checked)}
                                    className="mt-0.5 h-5 w-5 rounded border-serene-outline bg-serene-bg/50 text-serene-primary focus:ring-serene-primary"
                                    required
                                />
                                <span>
                                    Mình hiểu <span className="font-semibold text-serene-primary">Serene</span> là AI đồng hành, không phải bác sĩ. Trong trường hợp khẩn cấp, mình sẽ gọi <span className="font-bold text-serene-ink">1800-599-920</span> hoặc <span className="font-bold text-serene-ink">115</span>.
                                </span>
                            </label>
                        </div>

                        <button
                            type="submit"
                            className="auth-cta"
                        >
                            Bắt đầu hành trình
                        </button>

                        <p className="pt-1 text-center text-sm text-serene-muted">
                            Đã có tài khoản?{' '}
                            <Link to="/login" className="auth-link">
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