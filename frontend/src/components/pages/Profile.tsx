import { motion } from 'framer-motion'
import { ArrowLeft, Settings, Lock, User, Calendar, HeartPulse, Target, LifeBuoy, Activity, Moon, Sun, Sparkles, CheckCircle, ShieldCheck, Mail, Smartphone, Clock, Heart, Star, Pencil } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { ROUTE_PATHS } from '../../routes/paths'
import { onboardingService, type OnboardingProfile } from '../../services/onboardingService'
import { EMOTIONAL_OPTIONS, PRIMARY_CONCERN_OPTIONS, SUPPORT_OPTIONS, AGE_OPTIONS, PRACTICE_OPTIONS, STRESS_LABELS } from './onboarding/onboard.option'
import { useThemeContext } from '../../contexts/ThemeContext'
import Loading from '../ui/Loading'
import avatar from '../../assets/avatar.png'

type UserStats = {
    label: string
    value: string
    icon: typeof Star
    color: string
}

const STATS: UserStats[] = [
    { label: 'Cấp độ', value: 'Bậc thầy Tĩnh lặng', icon: Star, color: 'text-amber-500' },
    { label: 'Số giờ thiền', value: '128 giờ', icon: Clock, color: 'text-theme-accent' },
    { label: 'Tương tác', value: '450+', icon: Heart, color: 'text-rose-500' },
]

export default function Profile() {
    const navigate = useNavigate()
    const { user } = useAuth()
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const [onboardingData, setOnboardingData] = useState<OnboardingProfile | null>(null)
    const [loading, setLoading] = useState(true)

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

    const findLabel = (list: { id: string; label: string }[] | undefined, id?: string | null) => {
        if (!id || !list) return 'Chưa cập nhật'
        const found = list.find((i) => i.id === id)
        return found ? found.label : id
    }

    const ageGroupLabel = findLabel(AGE_OPTIONS, onboardingData?.age_group)
    const concernLabel = findLabel(PRIMARY_CONCERN_OPTIONS, onboardingData?.primary_concern ?? undefined)
    const supportLevelLabel = findLabel(SUPPORT_OPTIONS, onboardingData?.support_level ?? undefined)
    const nicknameLabel = onboardingData?.nickname || user.displayName || 'Chưa cập nhật'
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
        <div className="mx-auto max-w-5xl space-y-8 pb-20 text-theme-text-primary">
            {/* Header Card */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className={`relative overflow-hidden rounded-[3rem] ${isDark ? 'bg-black/40 border border-white/10' : 'bg-theme-surface/40'} p-8 shadow-2xl backdrop-blur-3xl md:p-12`}
            >
                <div className="absolute right-0 top-0 -mr-20 -mt-20 h-64 w-64 rounded-full bg-theme-accent/10 blur-3xl" />
                <div className="absolute bottom-0 left-0 -mb-20 -ml-20 h-64 w-64 rounded-full bg-theme-accent/5 blur-3xl" />

                <div className="relative flex flex-col items-center gap-10 lg:flex-row lg:items-start">
                    <div className="relative">
                        <div className="h-44 w-44 overflow-hidden rounded-full shadow-2xl md:h-52 md:w-52">
                            <img src={avatar} alt="Profile" className="h-full w-full object-cover" />
                        </div>
                        <button
                            type="button"
                            className="absolute bottom-3 right-3 flex h-12 w-12 items-center justify-center rounded-full bg-theme-accent text-white shadow-xl transition hover:scale-110 active:scale-95"
                        >
                            <Pencil className="h-5 w-5" />
                        </button>
                    </div>

                    <div className="flex-1 text-center lg:text-left">
                        <div className="flex flex-wrap items-center justify-center gap-4 lg:justify-start">
                            <h1 className="font-display text-5xl italic text-theme-text-primary md:text-6xl">{nicknameLabel}</h1>
                            <span className="flex items-center gap-1.5 rounded-full bg-theme-accent/10 px-4 py-1.5 text-[10px] font-bold uppercase tracking-[0.2em] text-theme-accent">
                                <ShieldCheck className="h-3.5 w-3.5" />
                                Verified Member
                            </span>
                        </div>

                        <div className="mt-6 flex flex-wrap justify-center gap-6 lg:justify-start">
                            <div className="flex items-center gap-2 text-theme-text-secondary">
                                <Mail className="h-4.5 w-4.5 opacity-60" />
                                <span className="text-sm md:text-base">{user.email}</span>
                            </div>
                            <div className="flex items-center gap-2 text-theme-text-secondary">
                                <Smartphone className="h-4.5 w-4.5 opacity-60" />
                                <span className="text-sm md:text-base">090 * * * 1234</span>
                            </div>
                        </div>

                        <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
                            {STATS.map((stat) => {
                                const Icon = stat.icon
                                return (
                                    <div
                                        key={stat.label}
                                        className={`flex flex-col items-center rounded-3xl ${isDark ? 'bg-white/5 border border-white/5' : 'bg-theme-surface/50'} p-5 shadow-sm transition hover:bg-theme-surface/70 lg:items-start`}
                                    >
                                        <Icon className={`h-6 w-6 ${stat.color} mb-3`} />
                                        <p className="text-[10px] font-bold uppercase tracking-widest text-theme-text-secondary/60">
                                            {stat.label}
                                        </p>
                                        <p className="mt-1 font-display text-xl text-theme-text-primary">{stat.value}</p>
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                </div>
            </motion.div>

            <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
                {/* Main Content */}
                <section className="space-y-6 lg:col-span-2">
                    {/* Detailed Info */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        className={`rounded-[2.5rem] ${isDark ? 'bg-black/30 border border-white/10' : 'bg-theme-surface/40'} p-8 shadow-xl backdrop-blur-2xl`}
                    >
                        <div className="mb-8 flex items-center justify-between">
                            <h2 className="font-display text-3xl italic text-theme-text-primary">Thông tin cá nhân</h2>
                            <button
                                onClick={() => navigate(ROUTE_PATHS.setting)}
                                type="button"
                                className="text-xs font-bold uppercase tracking-widest text-theme-accent hover:opacity-70"
                            >
                                Chỉnh sửa
                            </button>
                        </div>

                        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                            <div className="space-y-1.5">
                                <p className="text-[10px] font-bold uppercase tracking-widest text-theme-text-secondary/50">Tên thật</p>
                                <div className="flex items-center gap-3 rounded-2xl border border-theme-border/20 bg-theme-surface/30 px-5 py-3.5">
                                    <User className="h-4 w-4 text-theme-accent/60" />
                                    <span className="text-sm font-medium">{user.displayName}</span>
                                </div>
                            </div>
                            <div className="space-y-1.5">
                                <p className="text-[10px] font-bold uppercase tracking-widest text-theme-text-secondary/50">Nickname Serene</p>
                                <div className="flex items-center gap-3 rounded-2xl border border-theme-border/20 bg-theme-surface/30 px-5 py-3.5">
                                    <Sparkles className="h-4 w-4 text-theme-accent/60" />
                                    <span className="text-sm font-medium">{nicknameLabel}</span>
                                </div>
                            </div>
                        </div>
                    </motion.div>

                    {/* Onboarding Data */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className={`rounded-[2.5rem] ${isDark ? 'bg-black/30 border border-white/10' : 'bg-theme-surface/40'} p-8 shadow-xl backdrop-blur-2xl`}
                    >
                        <h2 className="mb-8 font-display text-3xl italic text-theme-text-primary">Hành trình tâm thức</h2>
                        {loading ? (
                            <Loading text="Đang tải dữ liệu..." />
                        ) : onboardingData ? (
                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                                {[
                                    { icon: HeartPulse, label: 'Tâm trạng', value: emotionalStateLabel },
                                    { icon: Target, label: 'Mối quan tâm', value: concernLabel },
                                    { icon: Activity, label: 'Căng thẳng', value: stressLevelLabel },
                                    { icon: Sun, label: 'Thức dậy', value: wakeTimeLabel },
                                    { icon: Moon, label: 'Đi ngủ', value: bedTimeLabel },
                                    { icon: LifeBuoy, label: 'Hỗ trợ', value: supportLevelLabel },
                                ].map((item, idx) => {
                                    const Icon = item.icon
                                    return (
                                        <div key={idx} className={`flex items-center gap-4 rounded-3xl ${isDark ? 'bg-white/5 border border-white/5' : 'bg-theme-surface/20'} p-4 transition hover:bg-theme-surface/40`}>
                                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-theme-accent/10 text-theme-accent">
                                                <Icon className="h-5 w-5" />
                                            </div>
                                            <div>
                                                <p className="text-[9px] font-bold uppercase tracking-widest text-theme-text-secondary/50">{item.label}</p>
                                                <p className="text-sm font-medium text-theme-text-primary line-clamp-1">{item.value}</p>
                                            </div>
                                        </div>
                                    )
                                })}
                                <div className="col-span-full mt-4 rounded-3xl bg-theme-accent/5 p-6">
                                    <p className="text-[10px] font-bold uppercase tracking-widest text-theme-accent/70">Thói quen ưu tiên</p>
                                    <p className="mt-2 text-sm leading-relaxed italic">{practicesLabel}</p>
                                </div>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-10 text-center">
                                <p className="text-sm text-theme-text-secondary">Bạn chưa hoàn thành khảo sát mục tiêu cá nhân.</p>
                                <button onClick={() => navigate(ROUTE_PATHS.onboarding)} className="mt-4 text-xs font-bold uppercase tracking-widest text-theme-accent">Bắt đầu ngay</button>
                            </div>
                        )}
                    </motion.div>
                </section>

                {/* Sidebar */}
                <section className="space-y-8">
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 }}
                        className={`rounded-[2.5rem] ${isDark ? 'bg-black/30 border border-white/10' : 'bg-theme-surface/40'} p-8 shadow-xl backdrop-blur-2xl`}
                    >
                        <h2 className="mb-6 font-display text-2xl italic text-theme-text-primary">Bảo mật & Tài khoản</h2>
                        <div className="space-y-3">
                            <button
                                onClick={() => navigate(ROUTE_PATHS.forget)}
                                className={`flex w-full items-center justify-between rounded-2xl ${isDark ? 'bg-white/5 border border-white/5' : 'bg-theme-surface/20'} px-5 py-4 transition hover:bg-theme-surface/40`}
                            >
                                <div className="flex items-center gap-3">
                                    <Lock className="h-4 w-4 text-theme-text-secondary" />
                                    <span className="text-sm font-medium">Đổi mật khẩu</span>
                                </div>
                            </button>
                            <button
                                onClick={() => navigate(ROUTE_PATHS.setting)}
                                className={`flex w-full items-center justify-between rounded-2xl ${isDark ? 'bg-white/5 border border-white/5' : 'bg-theme-surface/20'} px-5 py-4 transition hover:bg-theme-surface/40`}
                            >
                                <div className="flex items-center gap-3">
                                    <Settings className="h-4 w-4 text-theme-text-secondary" />
                                    <span className="text-sm font-medium">Cài đặt chung</span>
                                </div>
                            </button>
                        </div>
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.4 }}
                        className="group relative overflow-hidden rounded-[2.5rem] bg-theme-accent p-8 text-white shadow-2xl"
                    >
                        <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-white/20 blur-2xl transition group-hover:scale-150" />
                        <h3 className="relative z-10 font-display text-2xl italic">Serene Premium</h3>
                        <p className="relative z-10 mt-2 text-sm text-white/80">
                            Mở khóa toàn bộ kho tài nguyên chữa lành và các bài thực hành nâng cao.
                        </p>
                        <button
                            type="button"
                            className="relative z-10 mt-8 w-full rounded-2xl bg-white/95 py-4 text-xs font-bold uppercase tracking-widest text-theme-accent shadow-xl transition hover:bg-white active:scale-95"
                        >
                            Nâng cấp ngay
                        </button>
                    </motion.div>
                </section>
            </div>
        </div>
    )
}
