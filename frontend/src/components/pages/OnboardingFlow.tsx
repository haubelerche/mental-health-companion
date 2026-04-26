import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronLeft, ChevronRight, Sparkles, Check } from 'lucide-react'
import { ROUTE_PATHS } from '../../routes/paths'

// ── Types ──────────────────────────────────────────────────────────────────────
type OnboardingData = {
  nickname: string
  gender: string
  ageGroup: string
  concerns: string[]
  stressFreq: number
  wakeTime: string
  bedTime: string
  goals: string[]
}

const TOTAL_STEPS = 8

// ── Step content ──────────────────────────────────────────────────────────────
const GENDER_OPTIONS = [
  { id: 'male', icon: '🙋', label: 'Nam' },
  { id: 'female', icon: '🙋‍♀️', label: 'Nữ' },
  { id: 'nonbinary', icon: '🌈', label: 'Non-binary' },
  { id: 'prefer_not', icon: '🤫', label: 'Không tiết lộ' },
]

const AGE_OPTIONS = [
  { id: '15-18', label: '15 – 18', desc: 'Học sinh' },
  { id: '18-22', label: '18 – 22', desc: 'Sinh viên' },
  { id: '22-26', label: '22 – 26', desc: 'Người mới đi làm' },
  { id: '26-30', label: '26 – 30', desc: 'Chuyên nghiệp' },
]

const CONCERNS = [
  { id: 'study_stress', icon: '📚', label: 'Căng thẳng học tập' },
  { id: 'social_anxiety', icon: '😰', label: 'Lo âu xã hội' },
  { id: 'burnout', icon: '🔥', label: 'Kiệt sức' },
  { id: 'loneliness', icon: '🌧️', label: 'Cô đơn' },
  { id: 'insomnia', icon: '🌙', label: 'Mất ngủ' },
  { id: 'mild_depression', icon: '💧', label: 'Trầm cảm nhẹ' },
]

const STRESS_LABELS = ['Rất hiếm', 'Đôi khi', 'Vài lần/tuần', 'Mỗi ngày', 'Liên tục']

const GOALS = [
  { id: 'mood', icon: '🌊', label: 'Ổn định tâm trạng', desc: 'Cân bằng cảm xúc hàng ngày' },
  { id: 'sleep', icon: '🌙', label: 'Ngủ tốt hơn', desc: 'Cải thiện chất lượng giấc ngủ' },
  { id: 'habits', icon: '🌱', label: 'Xây dựng thói quen', desc: 'Check-in & luyện tập đều đặn' },
]

// ── Animation variants ─────────────────────────────────────────────────────────
const slideVariants = {
  enter: (dir: number) => ({ x: dir > 0 ? 48 : -48, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir: number) => ({ x: dir > 0 ? -48 : 48, opacity: 0 }),
}

// ── Sub-components ─────────────────────────────────────────────────────────────
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
      className={`relative flex w-full items-center gap-3 rounded-2xl border px-5 py-4 text-left transition-all active:scale-[0.98] ${
        selected
          ? 'border-serene-primary bg-serene-primary/10 text-serene-ink shadow-sm'
          : 'border-serene-border bg-white/70 text-serene-ink hover:border-serene-primary/40 hover:bg-white/90'
      }`}
    >
      {children}
      {selected && (
        <span className="ml-auto flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-serene-primary">
          <Check className="h-3 w-3 text-white" />
        </span>
      )}
    </button>
  )
}

// ── Step components ─────────────────────────────────────────────────────────────
function StepSplash({ onNext }: { onNext: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <motion.div
        initial={{ scale: 0.7, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 20 }}
        className="mb-8 flex h-24 w-24 items-center justify-center rounded-3xl bg-serene-primary shadow-[0_16px_40px_rgba(77,99,89,0.35)]"
      >
        <Sparkles className="h-12 w-12 text-serene-accent" />
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="font-display text-5xl text-serene-ink sm:text-6xl"
      >
        Serene
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="mt-5 max-w-xs text-xl leading-relaxed text-serene-muted"
      >
        Bạn không cần hoàn hảo.
        <br />
        Bạn chỉ cần{' '}
        <em className="font-display not-italic text-serene-primary">hiện diện.</em>
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="mt-10 grid grid-cols-3 gap-4 text-center"
      >
        {[
          { emoji: '🧠', label: 'AI đồng hành' },
          { emoji: '🔒', label: 'Riêng tư' },
          { emoji: '💚', label: 'Gen Z' },
        ].map((item) => (
          <div key={item.label} className="rounded-2xl border border-serene-border bg-white/60 px-3 py-3">
            <div className="text-2xl">{item.emoji}</div>
            <div className="mt-1 text-xs font-medium text-serene-muted">{item.label}</div>
          </div>
        ))}
      </motion.div>

      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        type="button"
        onClick={onNext}
        className="mt-12 w-full max-w-xs rounded-full bg-serene-primary py-4 font-semibold text-serene-on-primary shadow-lg shadow-serene-primary/25 transition hover:brightness-105 active:scale-[0.97]"
      >
        Bắt đầu nào ✨
      </motion.button>
    </div>
  )
}

function StepNickname({
  value,
  onChange,
}: {
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-4xl text-serene-ink">Bạn muốn mình gọi bạn là gì?</h2>
        <p className="mt-2 text-sm text-serene-muted">Tên thật, biệt danh, hay bất kỳ cái tên nào bạn thích.</p>
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Nhập tên của bạn..."
        maxLength={32}
        autoFocus
        className="w-full rounded-2xl border border-serene-border bg-white/80 px-5 py-4 text-2xl font-medium text-serene-ink placeholder-serene-muted/60 outline-none transition focus:border-serene-primary focus:ring-2 focus:ring-serene-primary/20"
      />
      {value && (
        <motion.p
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-base text-serene-muted"
        >
          Xin chào,{' '}
          <span className="font-semibold text-serene-ink">{value}</span> 👋
        </motion.p>
      )}
    </div>
  )
}

function StepGender({
  value,
  onChange,
}: {
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-display text-4xl text-serene-ink">Giới tính của bạn là?</h2>
        <p className="mt-2 text-sm text-serene-muted">Giúp Serene cá nhân hoá trải nghiệm phù hợp hơn.</p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {GENDER_OPTIONS.map((opt) => (
          <OptionPill key={opt.id} selected={value === opt.id} onClick={() => onChange(opt.id)}>
            <span className="text-2xl">{opt.icon}</span>
            <span className="font-medium">{opt.label}</span>
          </OptionPill>
        ))}
      </div>
    </div>
  )
}

function StepAgeGroup({
  value,
  onChange,
}: {
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-display text-4xl text-serene-ink">Bạn thuộc nhóm tuổi nào?</h2>
        <p className="mt-2 text-sm text-serene-muted">Serene sẽ điều chỉnh nội dung phù hợp với giai đoạn của bạn.</p>
      </div>
      <div className="space-y-3">
        {AGE_OPTIONS.map((opt) => (
          <OptionPill key={opt.id} selected={value === opt.id} onClick={() => onChange(opt.id)}>
            <div>
              <p className="font-semibold text-serene-ink">{opt.label} tuổi</p>
              <p className="text-sm text-serene-muted">{opt.desc}</p>
            </div>
          </OptionPill>
        ))}
      </div>
    </div>
  )
}

function StepConcerns({
  value,
  onChange,
}: {
  value: string[]
  onChange: (v: string[]) => void
}) {
  const toggle = (id: string) => {
    onChange(value.includes(id) ? value.filter((c) => c !== id) : [...value, id])
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-display text-4xl text-serene-ink">Điều gì đang ảnh hưởng bạn?</h2>
        <p className="mt-2 text-sm text-serene-muted">Chọn những điều phù hợp. Bạn có thể chọn nhiều mục.</p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {CONCERNS.map((item) => {
          const selected = value.includes(item.id)
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => toggle(item.id)}
              className={`flex flex-col items-start rounded-2xl border px-4 py-3.5 text-left transition-all active:scale-[0.97] ${
                selected
                  ? 'border-serene-primary bg-serene-primary/10'
                  : 'border-serene-border bg-white/70 hover:border-serene-primary/40'
              }`}
            >
              <span className="mb-2 text-2xl">{item.icon}</span>
              <span className={`text-sm font-medium leading-tight ${selected ? 'text-serene-primary' : 'text-serene-ink'}`}>
                {item.label}
              </span>
              {selected && (
                <span className="mt-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-serene-primary">
                  <Check className="h-2.5 w-2.5 text-white" />
                </span>
              )}
            </button>
          )
        })}
      </div>
      {value.length === 0 && (
        <p className="text-center text-xs text-serene-muted">Bạn cũng có thể bỏ qua nếu không muốn chia sẻ.</p>
      )}
    </div>
  )
}

function StepStressFreq({
  value,
  onChange,
}: {
  value: number
  onChange: (v: number) => void
}) {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="font-display text-4xl text-serene-ink">Bạn hay bị căng thẳng không?</h2>
        <p className="mt-2 text-sm text-serene-muted">Kéo thanh trượt để chọn mức độ phù hợp nhất.</p>
      </div>

      <div className="space-y-6">
        <div className="flex h-16 items-center justify-center">
          <motion.p
            key={value}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="font-display text-3xl text-serene-primary"
          >
            {STRESS_LABELS[value]}
          </motion.p>
        </div>

        <div className="px-2">
          <input
            type="range"
            min={0}
            max={4}
            value={value}
            onChange={(e) => onChange(Number(e.target.value))}
            className="h-2 w-full cursor-pointer appearance-none rounded-full bg-serene-border accent-serene-primary"
          />
          <div className="mt-3 flex justify-between">
            {STRESS_LABELS.map((label, i) => (
              <div
                key={label}
                className={`flex flex-col items-center text-[10px] ${i === value ? 'text-serene-primary font-semibold' : 'text-serene-muted'}`}
              >
                <span className={`mb-1 h-2 w-2 rounded-full ${i === value ? 'bg-serene-primary' : 'bg-serene-border'}`} />
                {i === 0 ? 'Hiếm' : i === 4 ? 'Luôn luôn' : ''}
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-serene-border bg-white/60 p-4">
          <p className="text-sm text-serene-muted">
            {value <= 1
              ? '✨ Tuyệt vời — Serene sẽ giúp bạn duy trì trạng thái tốt này.'
              : value === 2
                ? '💛 Căng thẳng thỉnh thoảng là bình thường. Serene có những bài tập giúp ích.'
                : '💚 Serene hiểu điều này không dễ. Hãy cùng bắt đầu từng bước nhỏ.'}
          </p>
        </div>
      </div>
    </div>
  )
}

function TimePicker({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-serene-muted">{label}</p>
      <input
        type="time"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-2xl border border-serene-border bg-white/80 px-5 py-4 text-2xl font-medium text-serene-ink outline-none transition focus:border-serene-primary focus:ring-2 focus:ring-serene-primary/20"
      />
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
        <h2 className="font-display text-4xl text-serene-ink">Lịch ngủ của bạn thế nào?</h2>
        <p className="mt-2 text-sm text-serene-muted">
          Serene sẽ nhắc check-in vào đúng thời điểm trong ngày của bạn.
        </p>
      </div>

      <div className="space-y-4">
        <div className="rounded-2xl border border-serene-border bg-white/70 p-5">
          <div className="mb-1 flex items-center gap-2">
            <span className="text-xl">🌅</span>
            <span className="font-semibold text-serene-ink">Buổi sáng</span>
          </div>
          <TimePicker label="Bạn thường thức dậy lúc mấy giờ?" value={wakeTime} onChange={onChangeWake} />
        </div>
        <div className="rounded-2xl border border-serene-border bg-white/70 p-5">
          <div className="mb-1 flex items-center gap-2">
            <span className="text-xl">🌙</span>
            <span className="font-semibold text-serene-ink">Buổi tối</span>
          </div>
          <TimePicker label="Bạn thường đi ngủ lúc mấy giờ?" value={bedTime} onChange={onChangeBed} />
        </div>
      </div>
    </div>
  )
}

function StepGoals({
  value,
  onChange,
}: {
  value: string[]
  onChange: (v: string[]) => void
}) {
  const toggle = (id: string) => {
    onChange(value.includes(id) ? value.filter((g) => g !== id) : [...value, id])
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-display text-4xl text-serene-ink">Bạn muốn đạt được điều gì?</h2>
        <p className="mt-2 text-sm text-serene-muted">Chọn 1–3 mục tiêu. Có thể thay đổi sau.</p>
      </div>
      <div className="space-y-3">
        {GOALS.map((goal) => {
          const selected = value.includes(goal.id)
          return (
            <button
              key={goal.id}
              type="button"
              onClick={() => toggle(goal.id)}
              className={`flex w-full items-center gap-4 rounded-2xl border px-5 py-4 text-left transition-all active:scale-[0.97] ${
                selected
                  ? 'border-serene-primary bg-serene-primary/10'
                  : 'border-serene-border bg-white/70 hover:border-serene-primary/40 hover:bg-white/90'
              }`}
            >
              <span className="text-3xl">{goal.icon}</span>
              <div className="flex-1">
                <p className={`font-semibold ${selected ? 'text-serene-primary' : 'text-serene-ink'}`}>{goal.label}</p>
                <p className="text-sm text-serene-muted">{goal.desc}</p>
              </div>
              {selected && (
                <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-serene-primary">
                  <Check className="h-3.5 w-3.5 text-white" />
                </span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────
export function OnboardingFlow() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)
  const [direction, setDirection] = useState(1)
  const [data, setData] = useState<OnboardingData>({
    nickname: '',
    gender: '',
    ageGroup: '',
    concerns: [],
    stressFreq: 2,
    wakeTime: '07:00',
    bedTime: '23:00',
    goals: [],
  })

  const isSplash = currentStep === 0
  const stepIndex = currentStep - 1 // 0-based for actual steps
  const progressFraction = currentStep / (TOTAL_STEPS - 1)

  const canAdvance = useCallback(() => {
    if (isSplash) return true
    if (stepIndex === 0) return data.nickname.trim().length >= 1
    if (stepIndex === 1) return !!data.gender
    if (stepIndex === 2) return !!data.ageGroup
    if (stepIndex === 3) return true // concerns optional
    if (stepIndex === 4) return true // stress freq always valid
    if (stepIndex === 5) return !!(data.wakeTime && data.bedTime)
    if (stepIndex === 6) return data.goals.length >= 1
    return true
  }, [isSplash, stepIndex, data])

  const next = useCallback(() => {
    if (!canAdvance()) return
    setDirection(1)
    if (currentStep >= TOTAL_STEPS - 1) {
      // Save to localStorage and redirect
      try {
        localStorage.setItem('serene_onboarding', JSON.stringify({ ...data, completedAt: new Date().toISOString() }))
      } catch {
        // ignore storage errors
      }
      navigate(ROUTE_PATHS.home)
      return
    }
    setCurrentStep((s) => s + 1)
  }, [canAdvance, currentStep, data, navigate])

  const prev = () => {
    if (currentStep === 0) return
    setDirection(-1)
    setCurrentStep((s) => s - 1)
  }

  const isLastStep = currentStep === TOTAL_STEPS - 1

  return (
    <div className="flex min-h-screen flex-col bg-serene-bg">
      {/* Progress bar */}
      {!isSplash && (
        <div className="px-5 pt-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={prev}
              className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border border-serene-border bg-white/70 text-serene-muted transition hover:bg-white"
              aria-label="Quay lại"
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
              onClick={() => navigate(ROUTE_PATHS.home)}
              className="text-xs font-medium text-serene-muted transition hover:text-serene-ink"
            >
              Bỏ qua
            </button>
          </div>
          <p className="mt-2 text-right text-[11px] text-serene-muted">
            {currentStep} / {TOTAL_STEPS - 1}
          </p>
        </div>
      )}

      {/* Step content */}
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
            {currentStep === 0 && <StepSplash onNext={next} />}
            {currentStep === 1 && (
              <StepNickname value={data.nickname} onChange={(v) => setData((d) => ({ ...d, nickname: v }))} />
            )}
            {currentStep === 2 && (
              <StepGender value={data.gender} onChange={(v) => setData((d) => ({ ...d, gender: v }))} />
            )}
            {currentStep === 3 && (
              <StepAgeGroup value={data.ageGroup} onChange={(v) => setData((d) => ({ ...d, ageGroup: v }))} />
            )}
            {currentStep === 4 && (
              <StepConcerns
                value={data.concerns}
                onChange={(v) => setData((d) => ({ ...d, concerns: v }))}
              />
            )}
            {currentStep === 5 && (
              <StepStressFreq
                value={data.stressFreq}
                onChange={(v) => setData((d) => ({ ...d, stressFreq: v }))}
              />
            )}
            {currentStep === 6 && (
              <StepSchedule
                wakeTime={data.wakeTime}
                bedTime={data.bedTime}
                onChangeWake={(v) => setData((d) => ({ ...d, wakeTime: v }))}
                onChangeBed={(v) => setData((d) => ({ ...d, bedTime: v }))}
              />
            )}
            {currentStep === 7 && (
              <StepGoals value={data.goals} onChange={(v) => setData((d) => ({ ...d, goals: v }))} />
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* CTA button (hidden on splash, splash has its own button) */}
      {!isSplash && (
        <div className="px-5 pb-10">
          <button
            type="button"
            onClick={next}
            disabled={!canAdvance()}
            className="flex w-full items-center justify-center gap-2 rounded-full bg-serene-primary py-4 font-semibold text-serene-on-primary shadow-lg shadow-serene-primary/20 transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-40 active:scale-[0.97]"
          >
            {isLastStep ? 'Bắt đầu hành trình 🌱' : 'Tiếp theo'}
            {!isLastStep && <ChevronRight className="h-5 w-5" />}
          </button>
        </div>
      )}
    </div>
  )
}
