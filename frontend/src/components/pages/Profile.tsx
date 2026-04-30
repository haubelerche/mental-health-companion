import { motion } from 'framer-motion'
import { ArrowLeft, LogOut, Settings, Lock, Info } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { ROUTE_PATHS } from '../../routes/paths'

interface OnboardingData {
  age_group?: string
  primary_concern?: string
  support_level?: string
}

export default function Profile() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [onboardingData, setOnboardingData] = useState<OnboardingData | null>(null)
  const [loading, setLoading] = useState(true)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  // Fetch onboarding data
  useEffect(() => {
    const fetchOnboardingData = async () => {
      try {
        const response = await fetch('/v1/onboarding/state', {
          credentials: 'include',
        })
        if (response.ok) {
          const result = await response.json()
          if (result.success && result.data?.profile) {
            setOnboardingData(result.data.profile)
          }
        }
      } catch (error) {
        console.error('Failed to fetch onboarding data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchOnboardingData()
  }, [])

  const handleLogout = async () => {
    setIsLoggingOut(true)
    try {
      await logout()
      navigate(ROUTE_PATHS.landing)
    } catch (error) {
      console.error('Logout failed:', error)
      setIsLoggingOut(false)
    }
  }

  if (!user) return null

  // Map onboarding values to display labels
  const ageGroupLabel = onboardingData?.age_group || 'Chưa cập nhật'
  const concernLabel = onboardingData?.primary_concern || 'Chưa cập nhật'
  const supportLevelLabel = onboardingData?.support_level || 'Chưa cập nhật'

  const createdDate = new Date().toLocaleDateString('vi-VN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  return (
    <div className="min-h-screen bg-serene-bg">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="sticky top-0 z-30 flex items-center gap-4 border-b border-serene-border bg-serene-bg/95 px-4 py-4 backdrop-blur-sm sm:px-6"
      >
        <button
          onClick={() => navigate(ROUTE_PATHS.home)}
          className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-serene-surface transition text-serene-ink"
          aria-label="Quay lại"
        >
          <ArrowLeft size={20} />
        </button>
        <h1 className="font-display text-2xl italic text-serene-ink flex-1">Hồ sơ</h1>
      </motion.div>

      {/* Content */}
      <div className="mx-auto max-w-2xl px-4 py-6 sm:px-6 sm:py-8">
        {/* Avatar & Basic Info */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8 rounded-3xl bg-serene-surface-card p-6 shadow-sm"
        >
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-16 h-16 rounded-full bg-serene-primary/10">
              <span className="text-2xl">👤</span>
            </div>
            <div className="flex-1">
              <h2 className="font-display text-xl italic text-serene-ink">{user.displayName}</h2>
              <p className="text-sm text-serene-muted">{user.email}</p>
            </div>
          </div>
        </motion.div>

        {/* Account Info Card */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="mb-6 rounded-3xl bg-serene-surface-card p-6 shadow-sm"
        >
          <h3 className="mb-4 font-display text-lg italic text-serene-ink">Thông tin tài khoản</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
              <span className="text-sm text-serene-muted">Tên hiển thị</span>
              <span className="font-medium text-serene-ink">{user.displayName}</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
              <span className="text-sm text-serene-muted">Email</span>
              <span className="font-medium text-serene-ink text-sm break-all">{user.email}</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
              <span className="text-sm text-serene-muted">Ngày tạo tài khoản</span>
              <span className="font-medium text-serene-ink">{createdDate}</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-serene-muted">Trạng thái</span>
              <span className="flex items-center gap-2 font-medium text-serene-primary">
                <span className="inline-block w-2 h-2 rounded-full bg-serene-primary" />
                Hoạt động
              </span>
            </div>
          </div>
        </motion.div>

        {/* About You Card */}
        {!loading && onboardingData && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mb-6 rounded-3xl bg-serene-surface-card p-6 shadow-sm"
          >
            <h3 className="mb-4 font-display text-lg italic text-serene-ink">Về bạn</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                <span className="text-sm text-serene-muted">Nhóm tuổi</span>
                <span className="font-medium text-serene-ink">{ageGroupLabel}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                <span className="text-sm text-serene-muted">Mối quan tâm chính</span>
                <span className="font-medium text-serene-ink">{concernLabel}</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-serene-muted">Mức hỗ trợ</span>
                <span className="font-medium text-serene-ink">{supportLevelLabel}</span>
              </div>
            </div>
          </motion.div>
        )}

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="space-y-3 mb-8"
        >
          <button
            onClick={() => navigate(ROUTE_PATHS.setting)}
            className="w-full flex items-center gap-3 rounded-2xl bg-serene-surface-card px-4 py-3 text-serene-ink transition hover:bg-serene-surface border border-serene-border"
          >
            <Settings size={18} />
            <span className="font-medium">Cài đặt ứng dụng</span>
          </button>

          <button
            onClick={() => navigate(ROUTE_PATHS.forget)}
            className="w-full flex items-center gap-3 rounded-2xl bg-serene-surface-card px-4 py-3 text-serene-ink transition hover:bg-serene-surface border border-serene-border"
          >
            <Lock size={18} />
            <span className="font-medium">Đổi mật khẩu</span>
          </button>

          <button
            disabled
            className="w-full flex items-center gap-3 rounded-2xl bg-serene-surface-card px-4 py-3 text-serene-muted cursor-not-allowed border border-serene-border opacity-60"
          >
            <Info size={18} />
            <span className="font-medium">Về Serene</span>
          </button>

          <button
            onClick={handleLogout}
            disabled={isLoggingOut}
            className="w-full flex items-center gap-3 rounded-2xl bg-serene-primary/10 px-4 py-3 text-serene-primary transition hover:bg-serene-primary/20 border border-serene-primary/30 disabled:opacity-60"
          >
            <LogOut size={18} />
            <span className="font-medium">{isLoggingOut ? 'Đang đăng xuất...' : 'Đăng xuất'}</span>
          </button>
        </motion.div>
      </div>
    </div>
  )
}
