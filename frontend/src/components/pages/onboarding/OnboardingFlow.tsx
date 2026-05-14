import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Brain,
    ChevronLeft,
    ChevronRight,
    Check,
    Footprints,
    Heart,
    MessageCircle,
    Moon,
    NotebookPen,
    Sparkles,
    Sun,
    Target,
    Wind,
    type LucideIcon,
} from 'lucide-react'
import { ROUTE_PATHS } from '../../../routes/paths'
import {
    buildDailyPlan,
    buildPlanReason,
    onboardingService,
    type DailyPlanIconId,
    type EmotionalState,
    type OnboardingProfile,
    type SupportLevel,
} from '../../../services/onboardingService'

const DAILY_PLAN_ICONS: Record<DailyPlanIconId, LucideIcon> = {
    sun: Sun,
    wind: Wind,
    notebook: NotebookPen,
    message: MessageCircle,
    heart: Heart,
    footprints: Footprints,
    moon: Moon,
    target: Target,
    brain: Brain,
}

function DailyPlanStepIcon({ id }: { id: DailyPlanIconId }) {
    const Icon = DAILY_PLAN_ICONS[id]
    return <Icon className="h-5 w-5 shrink-0 text-serene-primary" aria-hidden />
}
import { useAuth } from '../../../hooks/useAuth'
import bgGradient from '../../../assets/backgrounds/bg-resource.png'
import { AGE_OPTIONS, EMOTIONAL_OPTIONS, PRACTICE_OPTIONS, PRIMARY_CONCERN_OPTIONS, STRESS_LABELS, SUPPORT_OPTIONS, type OnboardingDraft } from './onboard.option'


const slideVariants = {
    enter: (dir: number) => ({ x: dir > 0 ? 48 : -48, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (dir: number) => ({ x: dir > 0 ? -48 : 48, opacity: 0 }),
}

function OptionPill({
    selected,
    onClick,
    children,
}: {
    selected: boolean
    onClick: () => void
    children: React.ReactNode
}) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={`relative flex w-full items-center gap-3 rounded-2xl border px-5 py-4 text-left transition-all active:scale-[0.98] ${selected
                ? 'border-serene-primary bg-serene-primary/10 text-theme-primary shadow-sm'
                : 'border-serene-border bg-theme-surface/70 text-theme-primary hover:border-serene-primary/40 hover:bg-theme-accent/20'
                }`}
        >
            {children}
            {selected && (
                <span className="ml-auto flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-serene-primary">
                    <Check className="h-3 w-3 text-white" />
                </span>
            )}
        </button>
    )
}

function StepSplash({ onNext }: { onNext: () => void }) {
    return (
        <div className="flex flex-col items-center justify-center py-14 text-center">
            <motion.div
                initial={{ scale: 0.7, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: 'spring', stiffness: 220, damping: 18 }}
                className="mb-7 flex h-24 w-24 items-center justify-center rounded-3xl bg-serene-primary shadow-[0_16px_40px_rgba(77,99,89,0.35)]"
            >
                <Sparkles className="h-12 w-12 text-serene-accent" />
            </motion.div>

            <motion.h1
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.12 }}
                className="font-display text-5xl text-theme-primary sm:text-6xl"
            >
                Serene
            </motion.h1>

            <motion.p
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="mt-5 max-w-sm text-lg leading-relaxed text-theme-secondary"
            >
                Cùng mình thiết lập một nhịp chăm sóc vừa vặn với bạn, để phần
                <span className="font-semibold text-serene-primary"> Hôm nay của bạn </span>
                thật sự hữu ích ngay từ ngày đầu.
            </motion.p>

            <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.35 }}
                type="button"
                onClick={onNext}
                className="mt-12 w-full max-w-xs rounded-full bg-serene-primary py-4 font-semibold text-serene-on-primary shadow-lg shadow-serene-primary/25 transition hover:brightness-105 active:scale-[0.97]"
            >
                Bắt đầu nào
            </motion.button>
        </div>
    )
}

function StepNickname({ value, onChange }: { value: string; onChange: (v: string) => void }) {
    return (
        <div className="space-y-6">
            <div>
                <h2 className="font-display text-4xl text-theme-primary">Mình nên gọi bạn là gì?</h2>
                <p className="mt-2 text-sm text-theme-secondary">Tên thật, biệt danh, hay bất kỳ cái tên nào bạn thấy thoải mái.</p>
            </div>
            <input
                type="text"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder="Nhập tên bạn muốn dùng..."
                maxLength={64}
                autoFocus
                className="w-full rounded-2xl border border-serene-border bg-theme-surface/80 px-5 py-4 text-2xl font-medium text-theme-primary placeholder-theme-secondary/60 outline-none transition focus:border-serene-primary focus:ring-2 focus:ring-serene-primary/20"
            />
        </div>
    )
}

function StepDisclaimer({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
    return (
        <div className="space-y-6">
            <div>
                <h2 className="font-display text-4xl text-theme-primary">Nơi mọi cảm xúc được lắng nghe</h2>
                <p className="mt-2 text-sm text-theme-secondary">
                    Serene được xây dựng để trở thành người bạn đồng hành, giúp bạn thấu hiểu bản thân và tìm thấy sự bình yên trong tâm trí.
                </p>
            </div>
            <div className="rounded-2xl border border-serene-border bg-theme-surface/80 p-5 text-sm leading-relaxed text-theme-secondary">
                Tuy nhiên, các nhân vật AI không có chức năng thay thế bác sĩ hay các lộ trình trị liệu chuyên sâu.
                Hãy tìm đến chuyên gia y tế khi bạn cần một chẩn đoán y khoa chính thức.
            </div>
            <label className="flex items-start gap-3 rounded-2xl border border-serene-border bg-theme-surface/70 px-4 py-4 text-sm text-theme-secondary">
                <input
                    type="checkbox"
                    checked={value}
                    onChange={(event) => onChange(event.target.checked)}
                    className="mt-0.5 h-5 w-5 rounded border-serene-outline text-serene-primary focus:ring-serene-primary"
                />
                <span>Mình đã đọc và đồng ý với nội dung trên để tiếp tục thiết lập Serene.</span>
            </label>
        </div>
    )
}

function StepEmotionalState({ value, onChange }: { value: EmotionalState | ''; onChange: (v: EmotionalState) => void }) {
    return (
        <div className="space-y-5">
            <div>
                <h2 className="font-display text-4xl text-theme-primary">Dạo này bạn thấy thế nào?</h2>
                <p className="mt-2 text-sm text-theme-secondary">Chọn câu gần nhất với trạng thái hiện tại của bạn.</p>
            </div>
            <div className="space-y-3">
                {EMOTIONAL_OPTIONS.map((opt) => (
                    <OptionPill key={opt.id} selected={value === opt.id} onClick={() => onChange(opt.id)}>
                        <opt.Icon className="h-7 w-7 shrink-0 text-serene-primary" aria-hidden />
                        <div>
                            <p className="font-semibold text-theme-primary">{opt.label}</p>
                            <p className="text-sm text-theme-secondary">{opt.desc}</p>
                        </div>
                    </OptionPill>
                ))}
            </div>
        </div>
    )
}

function StepPrimaryConcern({
    value,
    emotionalState,
    onChange,
}: {
    value: string
    emotionalState: EmotionalState | ''
    onChange: (v: string) => void
}) {
    const title = emotionalState === 'doing_okay' ? 'Bạn muốn ưu tiên điều gì nhất lúc này?' : 'Điều nào đang ảnh hưởng bạn nhiều nhất?'
    return (
        <div className="space-y-5">
            <div>
                <h2 className="font-display text-4xl text-theme-primary">{title}</h2>
                <p className="mt-2 text-sm text-theme-secondary">Bạn có thể bỏ qua câu này nếu chưa muốn chia sẻ.</p>
            </div>
            <div className="space-y-3">
                {PRIMARY_CONCERN_OPTIONS.map((opt) => (
                    <OptionPill key={opt.id} selected={value === opt.id} onClick={() => onChange(value === opt.id ? '' : opt.id)}>
                        {opt.Icon ? <opt.Icon className="h-6 w-6 shrink-0 text-serene-primary" aria-hidden /> : null}
                        <span className="font-medium text-theme-primary">{opt.label}</span>
                    </OptionPill>
                ))}
            </div>
        </div>
    )
}

function StepSupportLevel({ value, onChange }: { value: SupportLevel | ''; onChange: (v: SupportLevel | '') => void }) {
    return (
        <div className="space-y-5">
            <div>
                <h2 className="font-display text-4xl text-theme-primary">Mạng hỗ trợ của bạn hiện thế nào?</h2>
                <p className="mt-2 text-sm text-theme-secondary">Gia đình, bạn bè, đồng nghiệp... Câu này dùng để điều chỉnh gợi ý kết nối phù hợp.</p>
            </div>
            <div className="space-y-3">
                {SUPPORT_OPTIONS.map((opt) => (
                    <OptionPill key={opt.id} selected={value === opt.id} onClick={() => onChange(value === opt.id ? '' : (opt.id as SupportLevel))}>
                        <div>
                            <p className="font-semibold text-theme-primary">{opt.label}</p>
                            <p className="text-sm text-theme-secondary">{opt.desc}</p>
                        </div>
                    </OptionPill>
                ))}
            </div>
        </div>
    )
}

function StepAgeGroup({ value, onChange }: { value: string; onChange: (v: string) => void }) {
    return (
        <div className="space-y-5">
            <div>
                <h2 className="font-display text-4xl text-theme-primary">Bạn thuộc nhóm tuổi nào?</h2>
                <p className="mt-2 text-sm text-theme-secondary">Giúp Serene điều chỉnh nội dung phù hợp hơn.</p>
            </div>
            <div className="space-y-3">
                {AGE_OPTIONS.map((opt) => (
                    <OptionPill key={opt.id} selected={value === opt.id} onClick={() => onChange(opt.id)}>
                        <span className="font-medium text-theme-primary">{opt.label}</span>
                    </OptionPill>
                ))}
            </div>
        </div>
    )
}

function StepPractices({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
    const toggle = (id: string) => {
        onChange(value.includes(id) ? value.filter((item) => item !== id) : [...value, id].slice(0, 6))
    }
    return (
        <div className="space-y-5">
            <div>
                <h2 className="font-display text-4xl text-theme-primary">Bạn muốn luyện tập điều gì?</h2>
                <p className="mt-2 text-sm text-theme-secondary">Chọn tất cả mục bạn quan tâm (ít nhất 1 mục).</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
                {PRACTICE_OPTIONS.map((item) => {
                    const selected = value.includes(item.id)
                    return (
                        <button
                            key={item.id}
                            type="button"
                            onClick={() => toggle(item.id)}
                            className={`rounded-2xl cursor-pointer border px-4 py-3 text-left transition active:scale-[0.98] ${selected
                                ? 'border-serene-primary bg-theme-accent/20'
                                : 'border-serene-border bg-theme-surface/70 hover:bg-theme-accent/20'
                                }`}
                        >
                            <div className="mb-1 flex text-theme-primary">
                                <item.Icon className="h-6 w-6" aria-hidden />
                            </div>
                            <p className={`text-sm font-medium ${selected ? 'text-theme-accent-dim' : 'text-theme-primary'}`}>{item.label}</p>
                        </button>
                    )
                })}
            </div>
        </div>
    )
}

function StepSchedule({
    wakeTime,
    bedTime,
    onChangeWake,
    onChangeBed,
}: {
    wakeTime: string
    bedTime: string
    onChangeWake: (v: string) => void
    onChangeBed: (v: string) => void
}) {
    return (
        <div className="space-y-6">
            <div>
                <h2 className="font-display text-4xl text-theme-primary">Lịch sinh hoạt của bạn</h2>
                <p className="mt-2 text-sm text-theme-secondary">Serene dùng mốc giờ này để đề xuất check-in sáng/tối phù hợp hơn.</p>
            </div>

            <div className="space-y-4">
                <div className="rounded-2xl border border-serene-border bg-theme-surface/70 p-5">
                    <p className="mb-2 text-sm font-medium text-theme-secondary">Bạn thường thức dậy lúc</p>
                    <input
                        type="time"
                        value={wakeTime}
                        onChange={(e) => onChangeWake(e.target.value)}
                        className="w-full rounded-2xl border border-serene-border bg-theme-surface/80 px-4 py-3 text-2xl font-medium text-theme-primary outline-none transition focus:border-serene-primary focus:ring-2 focus:ring-theme-primary/20"
                    />
                </div>
                <div className="rounded-2xl border border-serene-border bg-theme-surface/70 p-5">
                    <p className="mb-2 text-sm font-medium text-theme-secondary">Bạn thường đi ngủ lúc</p>
                    <input
                        type="time"
                        value={bedTime}
                        onChange={(e) => onChangeBed(e.target.value)}
                        className="w-full rounded-2xl border border-serene-border bg-theme-surface/80 px-4 py-3 text-2xl font-medium text-theme-primary outline-none transition focus:border-serene-primary focus:ring-2 focus:ring-serene-primary/20"
                    />
                </div>
            </div>
        </div>
    )
}

function StepStressLevel({ value, onChange }: { value: number; onChange: (v: number) => void }) {
    return (
        <div className="space-y-7">
            <div>
                <h2 className="font-display text-4xl text-theme-primary">Bạn đang quản lý stress và cảm xúc thế nào?</h2>
                <p className="mt-2 text-sm text-theme-secondary">Thông tin này chỉ để cá nhân hóa gợi ý, không thay thế đánh giá lâm sàng.</p>
            </div>
            <div className="rounded-2xl border border-serene-border bg-theme-surface/70 p-6">
                <div className="flex h-14 items-center justify-center">
                    <motion.p
                        key={value}
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="font-display text-3xl text-theme-primary"
                    >
                        {STRESS_LABELS[value]}
                    </motion.p>
                </div>
                <input
                    type="range"
                    min={0}
                    max={4}
                    value={value}
                    onChange={(e) => onChange(Number(e.target.value))}
                    className="mt-2 h-2 w-full cursor-pointer appearance-none rounded-full bg-serene-border accent-serene-primary"
                />
            </div>
        </div>
    )
}

function StepSummary({
    draft,
    isSubmitting,
}: {
    draft: OnboardingDraft
    isSubmitting: boolean
}) {
    const profile: OnboardingProfile = {
        disclaimer_accepted: draft.disclaimerAccepted,
        nickname: draft.nickname.trim(),
        age_group: draft.ageGroup,
        emotional_state: draft.emotionalState || 'doing_okay',
        primary_concern: draft.primaryConcern || null,
        support_level: draft.supportLevel || null,
        stress_level: draft.stressLevel,
        wake_time: draft.wakeTime,
        bed_time: draft.bedTime,
        practice_ids: draft.practiceIds,
    }
    const planItems = buildDailyPlan(profile)
    const reason = buildPlanReason(profile)

    return (
        <div className="space-y-6">
            <div>
                <h2 className="font-display text-4xl text-theme-primary">Kế hoạch cá nhân của bạn đã sẵn sàng</h2>
                <p className="mt-2 text-sm text-theme-secondary">{reason}</p>
            </div>
            <div className="space-y-3">
                {planItems.map((item) => (
                    <div key={item.id} className="flex items-center gap-3 rounded-2xl border border-serene-border bg-theme-surface/70 px-4 py-3">
                        <DailyPlanStepIcon id={item.icon} />
                        <p className="font-medium text-theme-primary">{item.label}</p>
                    </div>
                ))}
            </div>
            <p className="text-xs text-theme-secondary">
                Bạn luôn có thể cập nhật các lựa chọn này sau trong Cài đặt.
            </p>
            {isSubmitting && <p className="text-sm font-medium text-serene-primary">Đang lưu thiết lập của bạn...</p>}
        </div>
    )
}

export function OnboardingFlow() {
    const navigate = useNavigate()
    const { user, markOnboardingCompleted } = useAuth()
    const [currentStep, setCurrentStep] = useState(0)
    const [direction, setDirection] = useState(1)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [draft, setDraft] = useState<OnboardingDraft>({
        disclaimerAccepted: false,
        nickname: user?.displayName || '',
        ageGroup: '',
        emotionalState: '',
        primaryConcern: '',
        supportLevel: '',
        stressLevel: 2,
        wakeTime: '07:30',
        bedTime: '22:30',
        practiceIds: [],
    })

    useEffect(() => {
        let mounted = true
        onboardingService
            .getState()
            .then((state) => {
                if (!mounted || !state.profile) return
                const profile = state.profile
                setDraft((prevState) => ({
                    ...prevState,
                    disclaimerAccepted: Boolean(profile.disclaimer_accepted),
                    nickname: profile.nickname || prevState.nickname,
                    ageGroup: profile.age_group || prevState.ageGroup,
                    emotionalState: (profile.emotional_state as EmotionalState) || prevState.emotionalState,
                    primaryConcern: profile.primary_concern || '',
                    supportLevel: (profile.support_level as SupportLevel | null) || '',
                    stressLevel: profile.stress_level ?? prevState.stressLevel,
                    wakeTime: profile.wake_time || prevState.wakeTime,
                    bedTime: profile.bed_time || prevState.bedTime,
                    practiceIds: profile.practice_ids?.length ? profile.practice_ids : prevState.practiceIds,
                }))
            })
            .catch(() => undefined)

        return () => {
            mounted = false
        }
    }, [])

    const totalSteps = 11
    const isSplash = currentStep === 0
    const isLastStep = currentStep === totalSteps - 1
    const progressFraction = currentStep / (totalSteps - 1)

    const canAdvance = useMemo(() => {
        if (isSplash) return true
        if (currentStep === 1) return draft.disclaimerAccepted
        if (currentStep === 2) return draft.nickname.trim().length > 0
        if (currentStep === 3) return Boolean(draft.emotionalState)
        if (currentStep === 4) return true
        if (currentStep === 5) return true
        if (currentStep === 6) return Boolean(draft.ageGroup)
        if (currentStep === 7) return draft.practiceIds.length > 0
        if (currentStep === 8) return Boolean(draft.wakeTime) && Boolean(draft.bedTime)
        if (currentStep === 9) return true
        return true
    }, [isSplash, currentStep, draft])

    const completeOnboarding = useCallback(async () => {
        if (!draft.emotionalState) return
        setIsSubmitting(true)
        const payload = {
            disclaimer_accepted: draft.disclaimerAccepted,
            nickname: draft.nickname.trim(),
            age_group: draft.ageGroup,
            emotional_state: draft.emotionalState,
            primary_concern: draft.primaryConcern || null,
            support_level: draft.supportLevel || null,
            stress_level: draft.stressLevel,
            wake_time: draft.wakeTime,
            bed_time: draft.bedTime,
            practice_ids: draft.practiceIds,
        }
        try {
            await onboardingService.complete(payload)
            markOnboardingCompleted(false)
            navigate(`${ROUTE_PATHS.home}?tour=first_run`, { replace: true })
        } finally {
            setIsSubmitting(false)
        }
    }, [draft, markOnboardingCompleted, navigate])

    const skipOnboarding = useCallback(async () => {
        setIsSubmitting(true)
        try {
            await onboardingService.skip()
            markOnboardingCompleted(true)
            navigate(ROUTE_PATHS.home, { replace: true })
        } finally {
            setIsSubmitting(false)
        }
    }, [markOnboardingCompleted, navigate])

    const next = useCallback(async () => {
        if (!canAdvance || isSubmitting) return
        if (isLastStep) {
            await completeOnboarding()
            return
        }
        setDirection(1)
        setCurrentStep((value) => Math.min(totalSteps - 1, value + 1))
    }, [canAdvance, completeOnboarding, isLastStep, isSubmitting, totalSteps])

    const prev = useCallback(() => {
        if (currentStep === 0 || isSubmitting) return
        setDirection(-1)
        setCurrentStep((value) => Math.max(0, value - 1))
    }, [currentStep, isSubmitting])

    return (
        <div className='relative min-h-screen flex justify-center'>
            <div className='fixed inset-0 -z-20'>
                <img src={bgGradient} alt="" className='w-full h-full object-cover' />
            </div>
            <main className="w-full max-w-4xl px-4 py-10 flex flex-col justify-center ">
                <div className='bg-theme-surface rounded-3xl shadow-lg p-6'>
                    {!isSplash && (
                        <div className="p-6">
                            <div className="flex items-center gap-3">
                                <button
                                    type="button"
                                    onClick={prev}
                                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-theme-border bg-theme-surface/70 text-theme-secondary transition hover:bg-white"
                                    aria-label="Quay lại"
                                    disabled={isSubmitting}
                                >
                                    <ChevronLeft className="h-5 w-5" />
                                </button>
                                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-serene-border">
                                    <motion.div
                                        className="h-full rounded-full bg-serene-primary"
                                        animate={{ width: `${progressFraction * 100}%` }}
                                        transition={{ duration: 0.35, ease: 'easeOut' }}
                                    />
                                </div>
                                <button
                                    type="button"
                                    onClick={() => {
                                        void skipOnboarding()
                                    }}
                                    className="font-medium text-theme-secondary transition hover:text-theme-primary disabled:opacity-50 cursor-pointer"
                                    disabled={isSubmitting || (currentStep <= 1 && !draft.disclaimerAccepted)}
                                >
                                    Bỏ qua
                                </button>
                            </div>
                            <p className="mt-2 text-right text-[11px] text-theme-secondary">
                                {currentStep} / {totalSteps - 1}
                            </p>
                        </div>
                    )}

                    <div className="flex-1 overflow-hidden px-5 pb-8 pt-6">
                        <AnimatePresence mode="wait" custom={direction}>
                            <motion.div
                                key={currentStep}
                                custom={direction}
                                variants={slideVariants}
                                initial="enter"
                                animate="center"
                                exit="exit"
                                transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
                            >
                                {currentStep === 0 && <StepSplash onNext={() => void next()} />}
                                {currentStep === 1 && (
                                    <StepDisclaimer
                                        value={draft.disclaimerAccepted}
                                        onChange={(value) => setDraft((prevState) => ({ ...prevState, disclaimerAccepted: value }))}
                                    />
                                )}
                                {currentStep === 2 && (
                                    <StepNickname value={draft.nickname} onChange={(value) => setDraft((prevState) => ({ ...prevState, nickname: value }))} />
                                )}
                                {currentStep === 3 && (
                                    <StepEmotionalState
                                        value={draft.emotionalState}
                                        onChange={(value) => setDraft((prevState) => ({ ...prevState, emotionalState: value }))}
                                    />
                                )}
                                {currentStep === 4 && (
                                    <StepPrimaryConcern
                                        value={draft.primaryConcern}
                                        emotionalState={draft.emotionalState}
                                        onChange={(value) => setDraft((prevState) => ({ ...prevState, primaryConcern: value }))}
                                    />
                                )}
                                {currentStep === 5 && (
                                    <StepSupportLevel
                                        value={draft.supportLevel}
                                        onChange={(value) => setDraft((prevState) => ({ ...prevState, supportLevel: value }))}
                                    />
                                )}
                                {currentStep === 6 && (
                                    <StepAgeGroup value={draft.ageGroup} onChange={(value) => setDraft((prevState) => ({ ...prevState, ageGroup: value }))} />
                                )}
                                {currentStep === 7 && (
                                    <StepPractices
                                        value={draft.practiceIds}
                                        onChange={(value) => setDraft((prevState) => ({ ...prevState, practiceIds: value }))}
                                    />
                                )}
                                {currentStep === 8 && (
                                    <StepSchedule
                                        wakeTime={draft.wakeTime}
                                        bedTime={draft.bedTime}
                                        onChangeWake={(value) => setDraft((prevState) => ({ ...prevState, wakeTime: value }))}
                                        onChangeBed={(value) => setDraft((prevState) => ({ ...prevState, bedTime: value }))}
                                    />
                                )}
                                {currentStep === 9 && (
                                    <StepStressLevel value={draft.stressLevel} onChange={(value) => setDraft((prevState) => ({ ...prevState, stressLevel: value }))} />
                                )}
                                {currentStep === 10 && <StepSummary draft={draft} isSubmitting={isSubmitting} />}
                            </motion.div>
                        </AnimatePresence>
                    </div>

                    {!isSplash && (
                        <div className="px-5 pb-10">
                            <button
                                type="button"
                                onClick={() => void next()}
                                disabled={!canAdvance || isSubmitting}
                                className="flex w-full items-center justify-center gap-2 rounded-full bg-serene-primary py-4 font-semibold text-serene-on-primary shadow-lg shadow-serene-primary/20 transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-40 active:scale-[0.97]"
                            >
                                {isLastStep ? 'Xác nhận và bắt đầu' : 'Tiếp theo'}
                                {!isLastStep && <ChevronRight className="h-5 w-5" />}
                            </button>
                        </div>
                    )}
                </div>
            </main>
        </div>

    )
}
