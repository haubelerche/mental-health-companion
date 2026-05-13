import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import {
    Activity,
    Cloud,
    CloudRain,
    CloudSun,
    HeartHandshake,
    MessageSquareText,
    NotebookPen,
    Phone,
    Share2,
    Sprout,
    Wind,
} from 'lucide-react'
import type { ScreeningResult } from '../../services/screeningService'
import { ROUTE_PATHS } from '../../routes/paths'

type SeverityMeta = {
  label: string
  headlineIcon: LucideIcon
  color: string
  bgColor: string
  barColor: string
  scorePercent: number
  insights: string[]
  interpretation: string
  actions: Array<{ label: string; path: string; primary?: boolean; icon?: React.ElementType }>
  exercises: Array<{ icon: LucideIcon; label: string; desc: string }>
}

const SEVERITY_MAP: Record<ScreeningResult['severity_label'], SeverityMeta> = {
  minimal: {
    label: 'Rất nhẹ',
    headlineIcon: Sprout,
    color: 'var(--color-an)',
    bgColor: 'var(--color-an-bg)',
    barColor: '#4caf50',
    scorePercent: 12,
    interpretation: 'Tâm trạng và năng lượng của bạn đang ở trạng thái ổn định. Tiếp tục duy trì!',
    insights: [
      'Năng lượng và tâm trạng nhìn chung ổn định',
      'Tiếp tục duy trì thói quen hiện tại',
      'Thử một bài tập nhỏ hôm nay',
    ],
    exercises: [
      { icon: Wind, label: 'Thở hộp', desc: '2 phút · Duy trì cân bằng' },
      { icon: NotebookPen, label: 'Check-in buổi sáng', desc: 'Ghi nhận cảm xúc' },
    ],
    actions: [
      { label: 'Thở cùng Lửa', path: ROUTE_PATHS.exercises, primary: true, icon: Wind },
      { label: 'Về trang chính', path: ROUTE_PATHS.home },
    ],
  },
  mild: {
    label: 'Nhẹ',
    headlineIcon: CloudSun,
    color: 'var(--color-an)',
    bgColor: 'var(--color-an-bg)',
    barColor: '#8bc34a',
    scorePercent: 28,
    interpretation: 'Có một vài dấu hiệu cần chú ý. Trò chuyện ngắn với Serene có thể giúp ích.',
    insights: [
      'Có một vài dấu hiệu cần chú ý',
      'Trò chuyện ngắn có thể giúp ích',
      'Nhắc bản thân check-in lại ngày mai',
    ],
    exercises: [
      { icon: MessageSquareText, label: 'Nói chuyện với Serene', desc: 'Chia sẻ cảm xúc ngay' },
      { icon: Wind, label: 'Thở 4-7-8', desc: '3 phút · Thư giãn' },
    ],
    actions: [
      { label: 'Trò chuyện với Mây', path: ROUTE_PATHS.chat, primary: true, icon: MessageSquareText },
      { label: 'Mở Nhìn Lại', path: ROUTE_PATHS.reflect },
    ],
  },
  moderate: {
    label: 'Trung bình',
    headlineIcon: Cloud,
    color: 'var(--color-lua)',
    bgColor: 'var(--color-lua-bg)',
    barColor: '#ff9800',
    scorePercent: 52,
    interpretation: 'Cần chú ý hơn đến sức khoẻ tâm thần. Nên trao đổi với ai đó trong 24h tới.',
    insights: [
      'Cần chú ý hơn đến sức khoẻ tâm thần',
      'Nên trao đổi với ai đó trong 24h tới',
      'Bài tập grounding có thể giúp ổn định ngay',
    ],
    exercises: [
      { icon: MessageSquareText, label: 'Nói chuyện với Serene', desc: 'Serene sẵn sàng ngay bây giờ' },
      { icon: Activity, label: 'Bài thở grounding', desc: '5 phút · Ổn định cơ thể' },
    ],
    actions: [
      { label: 'Trò chuyện với Mây ngay', path: ROUTE_PATHS.chat, primary: true, icon: MessageSquareText },
      { label: 'Tập thở với Lửa', path: ROUTE_PATHS.exercises, icon: Wind },
    ],
  },
  moderately_severe: {
    label: 'Khá cao',
    headlineIcon: CloudRain,
    color: 'var(--color-la-ban)',
    bgColor: 'var(--color-la-ban-bg)',
    barColor: '#e57373',
    scorePercent: 72,
    interpretation: 'Kết quả cho thấy cần hỗ trợ chuyên nghiệp. Bạn không cần đi qua điều này một mình.',
    insights: [
      'Kết quả cho thấy cần hỗ trợ chuyên nghiệp',
      'Phần Hỗ trợ có thể chỉ bạn tới nguồn phù hợp',
      'Bạn không cần đi qua điều này một mình',
    ],
    exercises: [
      { icon: HeartHandshake, label: 'Tìm nguồn hỗ trợ', desc: 'Hotlines & chuyên gia' },
      { icon: MessageSquareText, label: 'Nói chuyện với Serene', desc: 'Ngay bây giờ' },
    ],
    actions: [
      { label: 'Liên hệ Hỗ trợ', path: ROUTE_PATHS.support, primary: true },
      { label: 'Trò chuyện với Mây', path: ROUTE_PATHS.chat, icon: MessageSquareText },
    ],
  },
  severe: {
    label: 'Cao',
    headlineIcon: CloudRain,
    color: 'var(--color-la-ban)',
    bgColor: 'var(--color-la-ban-bg)',
    barColor: '#c62828',
    scorePercent: 90,
    interpretation: 'Kết quả quan trọng — cần được hỗ trợ sớm. Bạn đã rất dũng cảm khi làm bài này.',
    insights: [
      'Kết quả quan trọng — cần được hỗ trợ sớm',
      'Vui lòng xem phần Hỗ trợ hoặc gọi hotline',
      'Bạn đã rất dũng cảm khi làm bài này',
    ],
    exercises: [
      { icon: Phone, label: 'Hotline 1800-599-920', desc: 'Miễn phí · 24/7' },
      { icon: HeartHandshake, label: 'Liên hệ chuyên gia', desc: 'Hỗ trợ ngay' },
    ],
    actions: [
      { label: 'Liên hệ Hỗ trợ ngay', path: ROUTE_PATHS.support, primary: true },
      { label: 'Hotline 1800-599-920', path: 'tel', icon: Phone },
    ],
  },
}

// ── Score Bar component ────────────────────────────────────────────────────────
function ScoreBar({
  label,
  percent,
  color,
  delay = 0,
}: {
  label: string
  percent: number
  color: string
  delay?: number
}) {
  return (
    <div>
      <div className="mb-1.5 flex justify-between text-sm">
        <span className="text-serene-muted">{label}</span>
        <span className="font-semibold text-serene-ink">{percent}%</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-serene-border/60">
        <motion.div
          className="h-full rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.8, delay, ease: [0.4, 0, 0.2, 1] }}
          style={{ backgroundColor: color }}
        />
      </div>
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────────────────
export function ResultsPage() {
  const { state } = useLocation()
  const navigate = useNavigate()
  const result = state?.result as ScreeningResult | undefined

  useEffect(() => {
    if (result && result.instrument_id) {
      localStorage.setItem(`serene_screening_${result.instrument_id}`, JSON.stringify({
        raw_score: result.raw_score,
        severity_label: result.severity_label,
        timestamp: new Date().toISOString()
      }))
    }
  }, [result])
  const rawSeverity = result?.severity_label
  const severity: ScreeningResult['severity_label'] =
    rawSeverity != null && rawSeverity in SEVERITY_MAP ? rawSeverity : 'minimal'
  const meta = SEVERITY_MAP[severity]

  const handleAction = (path: string) => {
    if (path === 'tel') {
      window.location.assign('tel:1800599920')
      return
    }
    navigate(path)
  }

  const handleShare = async () => {
    const text = `Tôi vừa làm bài test sức khoẻ tâm thần trên Serene — Mức: ${meta.label}. Bạn cũng thử xem nhé!`
    if (navigator.share) {
      try {
        await navigator.share({ title: 'Kết quả Serene', text })
      } catch {
        // user dismissed, ignore
      }
    } else {
      await navigator.clipboard.writeText(text).catch(() => undefined)
    }
  }

  // Max score for the instrument (PHQ-9: 27, GAD-7: 21)
  const maxScore = result?.instrument_id === 'gad7' ? 21 : 27
  const rawScore = result?.raw_score ?? 0
  const rawPercent = Math.round((rawScore / maxScore) * 100)

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      className="min-h-screen pb-28 pt-10"
      style={{ backgroundColor: meta.bgColor }}
    >
      <div className="mx-auto max-w-lg px-5">

        {/* Header */}
        <div className="mb-8 text-center">
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', stiffness: 200, damping: 18 }}
            className="mb-4 flex justify-center"
            aria-hidden="true"
          >
            <meta.headlineIcon className="h-16 w-16" style={{ color: meta.color }} />
          </motion.div>
          <p className="mb-1 text-[10px] uppercase tracking-widest text-serene-muted">Kết quả</p>
          <h1 className="font-display text-4xl text-serene-ink">
            Mức{' '}
            <span style={{ color: meta.color }}>{meta.label}</span>
          </h1>
          {result && (
            <p className="mt-1 text-xs text-serene-muted">
              Điểm: {result.raw_score} · {result.instrument_id?.toUpperCase()}
            </p>
          )}
        </div>

        {/* Score visualization — dual bars */}
        <div className="mb-4 rounded-3xl bg-white p-5 shadow-sm">
          <h3 className="mb-4 font-semibold text-serene-ink text-sm">Điểm số của bạn</h3>
          <div className="space-y-4">
            <ScoreBar
              label="Điểm thực tế"
              percent={rawPercent}
              color={meta.barColor}
              delay={0.1}
            />
            <ScoreBar
              label="Mức độ ảnh hưởng"
              percent={meta.scorePercent}
              color={meta.barColor}
              delay={0.25}
            />
          </div>
          <div className="mt-4 rounded-2xl border border-serene-border/50 bg-serene-surface-2 p-3">
            <p className="text-sm leading-relaxed text-serene-muted">{meta.interpretation}</p>
          </div>
        </div>

        {/* Insights */}
        <div className="mb-4 rounded-3xl bg-white p-5 shadow-sm">
          <h3 className="mb-3 font-semibold text-serene-ink text-sm">Serene thấy gì</h3>
          <ul className="space-y-2.5">
            {meta.insights.map((item) => (
              <li key={item} className="flex items-start gap-2.5 text-sm text-serene-muted">
                <span className="mt-0.5 flex-shrink-0" style={{ color: meta.color }} aria-hidden="true">
                  ●
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Recommended exercises */}
        <div className="mb-4 rounded-3xl bg-white p-5 shadow-sm">
          <h3 className="mb-3 font-semibold text-serene-ink text-sm">Gợi ý cho bạn</h3>
          <div className="grid grid-cols-2 gap-3">
            {meta.exercises.map((ex) => {
              const ExIcon = ex.icon
              return (
              <button
                key={ex.label}
                type="button"
                onClick={() => navigate(ROUTE_PATHS.exercises)}
                className="flex flex-col items-start rounded-2xl border border-serene-border bg-serene-surface-2 p-3.5 text-left transition hover:bg-white"
              >
                <ExIcon className="mb-2 h-6 w-6 text-serene-primary" aria-hidden />
                <p className="text-sm font-semibold text-serene-ink leading-tight">{ex.label}</p>
                <p className="mt-0.5 text-xs text-serene-muted">{ex.desc}</p>
              </button>
            )})}
          </div>
        </div>

        {/* Disclaimer */}
        <p className="mb-6 px-2 text-center text-[10px] leading-relaxed text-serene-muted">
          Đây không phải chẩn đoán lâm sàng. Nếu lo ngại, hãy gặp chuyên gia sức khoẻ tâm thần.
        </p>

        {/* Actions */}
        <div className="space-y-3">
          {meta.actions.map((a) => {
            const Icon = a.icon
            return (
              <button
                key={a.label}
                type="button"
                onClick={() => handleAction(a.path)}
                className="flex w-full items-center justify-center gap-2 rounded-2xl py-3.5 font-semibold text-sm transition-all active:scale-[0.97]"
                style={
                  a.primary
                    ? { backgroundColor: meta.color, color: 'white' }
                    : { backgroundColor: 'white', color: 'var(--color-serene-ink)', border: '1px solid var(--color-serene-border)' }
                }
              >
                {Icon && <Icon className="h-4 w-4" />}
                {a.label}
              </button>
            )
          })}

          {/* Share button */}
          <button
            type="button"
            onClick={handleShare}
            className="flex w-full items-center justify-center gap-2 rounded-2xl border border-serene-border bg-white py-3 text-sm font-medium text-serene-muted transition hover:text-serene-ink active:scale-[0.97]"
          >
            <Share2 className="h-4 w-4" />
            Chia sẻ kết quả
          </button>

          {/* Retake */}
          <button
            type="button"
            onClick={() => navigate(ROUTE_PATHS.screening)}
            className="w-full py-2.5 text-center text-xs text-serene-muted transition hover:text-serene-ink"
          >
            Làm lại bài test khác
          </button>
        </div>

        {/* Chat CTA */}
        <div className="mt-6 rounded-3xl border border-serene-border bg-white p-5">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl bg-serene-primary/10">
              <MessageSquareText className="h-5 w-5 text-serene-primary" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-serene-ink text-sm">Nói chuyện về kết quả này</p>
              <p className="mt-0.5 text-xs text-serene-muted">
                Chat với Serene để hiểu hơn và tìm hướng tiếp theo.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => navigate(ROUTE_PATHS.chat)}
            className="mt-3 w-full rounded-xl bg-serene-primary/10 py-2.5 text-sm font-semibold text-serene-primary transition hover:bg-serene-primary/20"
          >
            Mở Chat
          </button>
        </div>

      </div>
    </motion.div>
  )
}
