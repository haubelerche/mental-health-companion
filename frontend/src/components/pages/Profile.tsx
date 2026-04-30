import { motion } from 'framer-motion'
import { ArrowLeft, Settings, Lock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { ROUTE_PATHS } from '../../routes/paths'
import { onboardingService, type OnboardingProfile } from '../../services/onboardingService'
import { EMOTIONAL_OPTIONS, PRIMARY_CONCERN_OPTIONS, SUPPORT_OPTIONS, AGE_OPTIONS, PRACTICE_OPTIONS, STRESS_LABELS } from './onboarding/onboard.option'
import {
    User,
    Calendar,
    HeartPulse,
    Target,
    LifeBuoy,
    Activity,
    Moon,
    Sun,
    Sparkles,
    CheckCircle,
} from 'lucide-react'
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
    const findLabel = (list: { id: string; label: string }[] | undefined, id?: string | null) => {
        if (!id || !list) return 'Chưa cập nhật'
        const found = list.find((i) => i.id === id)
        return found ? found.label : id
    }

    const ageGroupLabel = findLabel(AGE_OPTIONS, onboardingData?.age_group)
    const concernLabel = findLabel(PRIMARY_CONCERN_OPTIONS, onboardingData?.primary_concern ?? undefined)
    const supportLevelLabel = findLabel(SUPPORT_OPTIONS, onboardingData?.support_level ?? undefined)
    const nicknameLabel = onboardingData?.nickname || 'Chưa cập nhật'
    const emotionalStateLabel = (() => {
        const found = EMOTIONAL_OPTIONS.find((o) => o.id === onboardingData?.emotional_state)
        return found ? found.label : 'Chưa cập nhật'
    })()
    const stressLevelLabel = onboardingData?.stress_level !== undefined ? STRESS_LABELS[onboardingData.stress_level] ?? String(onboardingData.stress_level) : 'Chưa cập nhật'
    const wakeTimeLabel = onboardingData?.wake_time || 'Chưa cập nhật'
    const bedTimeLabel = onboardingData?.bed_time || 'Chưa cập nhật'
    const practicesLabel = onboardingData?.practice_ids && onboardingData.practice_ids.length > 0 ? onboardingData.practice_ids.map((id) => PRACTICE_OPTIONS.find((p) => p.id === id)?.label || id).join(', ') : 'Chưa cập nhật'
    const onboardingCompletedAt = onboardingData?.completed_at ? new Date(onboardingData.completed_at).toLocaleString('vi-VN') : null



    return (
        <div className="min-h-screen bg-white/35 backdrop-blur-xl rounded-3xl">
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
                <h1 className="font-display text-3xl italic text-serene-ink flex-1">Hồ sơ cá nhân</h1>
            </motion.div>

            {/* Content */}
            <div className="mx-auto max-w-2xl px-4 py-6 sm:px-6 sm:py-8">
                {/* Avatar & Basic Info */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="mb-8 rounded-3xl border border-white/35 bg-white/70 p-6 shadow-sm"
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
                    className="mb-6 rounded-3xl border border-white/35 bg-white/70 p-6 shadow-sm"
                >
                    <h3 className="mb-4 font-display text-3xl text-serene-primary font-semibold">Thông tin tài khoản</h3>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                            <span className=" text-serene-muted font-semibold">Tên hiển thị</span>
                            <span className=" text-serene-ink text-sm">{user.displayName}</span>
                        </div>
                        <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                            <span className=" text-serene-muted font-semibold">Email</span>
                            <span className=" text-serene-ink text-sm break-all">{user.email}</span>
                        </div>

                        <div className="flex items-center justify-between py-2">
                            <span className=" text-serene-muted font-semibold">Trạng thái</span>
                            <span className="flex items-center gap-2 font-medium text-serene-primary">
                                <span className="inline-block w-2 h-2 rounded-full bg-serene-primary" />
                                Đã kích hoạt
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
                        className="mb-6 rounded-3xl border border-white/35 bg-white/70 p-6 shadow-sm"
                    >
                        <h3 className="mb-4 font-display text-3xl text-serene-primary font-semibold">Về bạn</h3>
                        <div className="space-y-4">

                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <div className="flex items-center gap-2 text-serene-muted font-semibold">
                                    <User className="h-4 w-4" />
                                    Nickname
                                </div>
                                <span className="text-serene-ink text-sm">{nicknameLabel}</span>
                            </div>

                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <div className="flex items-center gap-2 text-serene-muted font-semibold">
                                    <Calendar className="h-4 w-4" />
                                    Nhóm tuổi
                                </div>
                                <span className="text-serene-ink text-sm">{ageGroupLabel}</span>
                            </div>

                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <div className="flex items-center gap-2 text-serene-muted font-semibold">
                                    <HeartPulse className="h-4 w-4" />
                                    Tâm trạng hiện tại
                                </div>
                                <span className="text-serene-ink text-sm">{emotionalStateLabel}</span>
                            </div>

                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <div className="flex items-center gap-2 text-serene-muted font-semibold">
                                    <Target className="h-4 w-4" />
                                    Mối quan tâm chính
                                </div>
                                <span className="text-serene-ink text-sm">{concernLabel}</span>
                            </div>

                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <div className="flex items-center gap-2 text-serene-muted font-semibold">
                                    <LifeBuoy className="h-4 w-4" />
                                    Mức hỗ trợ
                                </div>
                                <span className="text-serene-ink text-sm">{supportLevelLabel}</span>
                            </div>

                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <div className="flex items-center gap-2 text-serene-muted font-semibold">
                                    <Activity className="h-4 w-4" />
                                    Mức căng thẳng (0-10)
                                </div>
                                <span className="text-serene-ink text-sm">{stressLevelLabel}</span>
                            </div>

                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <div className="flex items-center gap-2 text-serene-muted font-semibold">
                                    <Moon className="h-4 w-4" />
                                    Ngủ lúc
                                </div>
                                <span className="text-serene-ink text-sm">{bedTimeLabel}</span>
                            </div>

                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <div className="flex items-center gap-2 text-serene-muted font-semibold">
                                    <Sun className="h-4 w-4" />
                                    Thức dậy lúc
                                </div>
                                <span className="text-serene-ink text-sm">{wakeTimeLabel}</span>
                            </div>

                            <div className="flex items-center justify-between py-2 border-b border-serene-border/50">
                                <div className="flex items-center gap-2 text-serene-muted font-semibold">
                                    <Sparkles className="h-4 w-4" />
                                    Thói quen ưu tiên
                                </div>
                                <span className="text-serene-ink text-sm">{practicesLabel}</span>
                            </div>

                            <div className="flex items-center justify-between py-2">
                                <div className="flex items-center gap-2 text-serene-muted font-semibold">
                                    <CheckCircle className="h-4 w-4" />
                                    Onboarding hoàn thành
                                </div>
                                <span className="text-serene-ink text-sm">
                                    {onboardingCompletedAt ?? 'Chưa hoàn thành'}
                                </span>
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
                        className="w-full flex items-center gap-3 rounded-2xl  bg-white/70 px-4 py-3 text-serene-ink transition hover:bg-serene-surface border border-serene-border"
                    >
                        <Settings size={18} />
                        <span className="font-medium">Cài đặt ứng dụng</span>
                    </button>

                    <button
                        onClick={() => navigate(ROUTE_PATHS.forget)}
                        className="w-full flex items-center gap-3 rounded-2xl  bg-white/70 px-4 py-3 text-serene-ink transition hover:bg-serene-surface border border-serene-border"
                    >
                        <Lock size={18} />
                        <span className="font-medium">Đổi mật khẩu</span>
                    </button>

                </motion.div>
            </div>
        </div>
    )
}
