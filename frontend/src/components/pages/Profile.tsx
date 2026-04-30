import { motion } from 'framer-motion'
import { ArrowLeft, Settings, Lock, Info } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { ROUTE_PATHS } from '../../routes/paths'
import { onboardingService, type OnboardingProfile } from '../../services/onboardingService'

export default function Profile() {
    const navigate = useNavigate()
    const { user } = useAuth()
    const [onboardingData, setOnboardingData] = useState<OnboardingProfile | null>(null)
    const [loading, setLoading] = useState(true)

    // Fetch onboarding data
    useEffect(() => {
        const fetchOnboardingData = async () => {
            try {
                const result = await onboardingService.getState()
                if (result.profile) {
                    setOnboardingData(result.profile)
                }
            } catch (error) {
                console.error('Failed to fetch onboarding data:', error)
            } finally {
                setLoading(false)
            }
        }

        fetchOnboardingData()
    }, [])


    if (!user) return null

    // Map onboarding values to display labels
    const ageGroupLabel = onboardingData?.age_group || 'Chưa cập nhật'
    const concernLabel = onboardingData?.primary_concern || 'Chưa cập nhật'
    const supportLevelLabel = onboardingData?.support_level || 'Chưa cập nhật'
    const nicknameLabel = onboardingData?.nickname || 'Chưa cập nhật'
    const emotionalStateLabel = (() => {
        switch (onboardingData?.emotional_state) {
            case 'difficult_recently':
                return 'Gần đây khó khăn'
            case 'ongoing_challenges':
                return 'Khó khăn kéo dài'
            case 'doing_okay':
                return 'Ổn định'
            default:
                return 'Chưa cập nhật'
        }
    })()
    const stressLevelLabel = onboardingData?.stress_level !== undefined ? String(onboardingData.stress_level) : 'Chưa cập nhật'
    const wakeTimeLabel = onboardingData?.wake_time || 'Chưa cập nhật'
    const bedTimeLabel = onboardingData?.bed_time || 'Chưa cập nhật'
    const practicesLabel = onboardingData?.practice_ids && onboardingData.practice_ids.length > 0 ? onboardingData.practice_ids.join(', ') : 'Chưa cập nhật'
    const onboardingCompletedAt = onboardingData?.completed_at ? new Date(onboardingData.completed_at).toLocaleString('vi-VN') : null

    const createdDate = new Date().toLocaleDateString('vi-VN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    })

    return (
        <div className="min-h-screen bg-white/70 backdrop-blur-xl rounded-3xl">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className=" flex items-center gap-4 border-b border-serene-border rounded-t-3xl bg-serene-bg/95 px-4 py-4 backdrop-blur-sm sm:px-6"
            >
                <button
                    onClick={() => navigate(ROUTE_PATHS.setting)}
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
                    <h3 className="mb-4 font-display text-2xl text-serene-primary font-semibold">Thông tin tài khoản</h3>
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
                        <h3 className="mb-4 font-display text-2xl text-serene-primary font-semibold">Về bạn</h3>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <span className="text-sm text-serene-muted">Nickname</span>
                                <span className="font-medium text-serene-ink">{nicknameLabel}</span>
                            </div>
                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <span className="text-sm text-serene-muted">Nhóm tuổi</span>
                                <span className="font-medium text-serene-ink">{ageGroupLabel}</span>
                            </div>
                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <span className="text-sm text-serene-muted">Tâm trạng hiện tại</span>
                                <span className="font-medium text-serene-ink">{emotionalStateLabel}</span>
                            </div>
                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <span className="text-sm text-serene-muted">Mối quan tâm chính</span>
                                <span className="font-medium text-serene-ink">{concernLabel}</span>
                            </div>
                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <span className="text-sm text-serene-muted">Mức hỗ trợ</span>
                                <span className="font-medium text-serene-ink">{supportLevelLabel}</span>
                            </div>
                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <span className="text-sm text-serene-muted">Mức căng thẳng (0-10)</span>
                                <span className="font-medium text-serene-ink">{stressLevelLabel}</span>
                            </div>
                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <span className="text-sm text-serene-muted">Thời gian thức</span>
                                <span className="font-medium text-serene-ink">{wakeTimeLabel}</span>
                            </div>
                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <span className="text-sm text-serene-muted">Thời gian ngủ</span>
                                <span className="font-medium text-serene-ink">{bedTimeLabel}</span>
                            </div>
                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <span className="text-sm text-serene-muted">Thói quen ưu tiên</span>
                                <span className="font-medium text-serene-ink">{practicesLabel}</span>
                            </div>
                            <div className="flex items-center justify-between py-2">
                                <span className="text-sm text-serene-muted">Onboarding hoàn thành</span>
                                <span className="font-medium text-serene-ink">{onboardingCompletedAt ?? 'Chưa hoàn thành'}</span>
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


                </motion.div>
            </div>
        </div>
    )
}
