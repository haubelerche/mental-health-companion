import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import { LoaderCircle } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { ROUTE_PATHS } from '../../routes/paths'

type OAuthState = 'idle' | 'processing' | 'error'

function getQueryParams(search: string) {
    return new URLSearchParams(search)
}

export default function OAuthCallback() {
    const { refreshUser } = useAuth()
    const navigate = useNavigate()
    const location = useLocation()
    const [state, setState] = useState<OAuthState>('idle')
    const query = useMemo(() => getQueryParams(location.search), [location.search])
    const missingEmail = query.get('oauth_missing_email') === '1'
    const provider = query.get('provider') || 'provider'

    useEffect(() => {
        if (missingEmail) {
            toast.error(`${provider === 'facebook' ? 'Facebook' : 'Google'} chưa trả email xác thực. Vui lòng đăng nhập email hoặc liên kết thủ công.`)
            return
        }

        let cancelled = false
        const finishOAuth = async () => {
            setState('processing')
            try {
                await refreshUser()
                if (!cancelled) {
                    toast.success('Đăng nhập OAuth thành công!')
                    navigate(ROUTE_PATHS.home, { replace: true })
                }
            } catch {
                if (!cancelled) {
                    setState('error')
                    toast.error('Không thể hoàn tất đăng nhập. Vui lòng thử lại.')
                }
            }
        }

        void finishOAuth()

        return () => {
            cancelled = true
        }
    }, [missingEmail, navigate, provider, refreshUser])

    const isError = state === 'error' || missingEmail

    return (
        <div className="auth-page flex items-center justify-center px-6 py-12">
            <div className="auth-noise" />
            <section className="auth-card w-full max-w-lg p-8 text-center sm:p-10">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-serene-accent/30">
                    <LoaderCircle className="h-8 w-8 animate-spin text-serene-primary" />
                </div>

                <h1 className="mt-6 font-display text-3xl text-serene-ink">
                    {isError ? 'Cần thêm một bước nữa' : 'Đang hoàn tất đăng nhập'}
                </h1>
                <p className="mt-3 text-sm leading-6 text-serene-muted">
                    {isError
                        ? 'Một số nhà cung cấp không trả đủ thông tin email. Bạn có thể quay lại trang đăng nhập và thử bằng email/password hoặc liên kết tài khoản sau.'
                        : 'Hệ thống đang xác thực tài khoản OAuth và đồng bộ phiên đăng nhập an toàn.'}
                </p>

                {isError && (
                    <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center">
                        <Link to={ROUTE_PATHS.login} className="auth-cta inline-flex justify-center sm:w-auto">
                            Quay lại đăng nhập
                        </Link>
                        <Link to={ROUTE_PATHS.register} className="rounded-full border border-serene-outline/40 px-6 py-4 text-sm font-medium text-serene-ink transition hover:border-serene-primary/60 hover:bg-serene-accent/20 sm:w-auto">
                            Tạo tài khoản mới
                        </Link>
                    </div>
                )}
            </section>
        </div>
    )
}
