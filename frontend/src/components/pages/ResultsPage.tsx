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
import { saveScreeningResult } from '../../utils/screeningResults'

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
      'Bạn đang giữ được nhịp sinh hoạt và cảm xúc khá ổn định',
      'Những khoảng nghỉ nhỏ trong ngày sẽ giúp duy trì trạng thái này lâu hơn',
      'Đừng chờ đến khi quá tải mới chăm sóc bản thân',
    ],
    exercises: [
      { icon: Wind, label: 'Thở hộp', desc: '2 phút · Duy trì cân bằng' },
      { icon: NotebookPen, label: 'Check-in buổi sáng', desc: 'Ghi nhận cảm xúc' },
    ],
    actions: [
      { label: 'Quay về trang chủ', path: ROUTE_PATHS.home },
      { label: 'Mở Nhìn Lại', path: ROUTE_PATHS.reflect },
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
      'Có dấu hiệu bạn đang hơi mệt hoặc căng thẳng trong thời gian gần đây',
      'Việc nghỉ ngơi đúng cách và nói ra cảm xúc có thể giúp đầu óc nhẹ hơn',
      'Hãy chú ý giấc ngủ, mức năng lượng và cảm giác của mình trong vài ngày tới',
    ],
    exercises: [
      { icon: MessageSquareText, label: 'Nói chuyện với Serene', desc: 'Chia sẻ cảm xúc ngay' },
      { icon: Wind, label: 'Thở 4-7-8', desc: '3 phút · Thư giãn' },
    ],
    actions: [
      { label: 'Quay về trang chủ', path: ROUTE_PATHS.home },
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
      'Căng thẳng đang bắt đầu ảnh hưởng rõ hơn đến cảm xúc hoặc sinh hoạt hằng ngày',
      'Bạn không cần tự chịu đựng một mình — trò chuyện với người tin tưởng có thể giúp ích',
      'Ưu tiên nghỉ ngơi, ăn uống đều và giảm bớt áp lực trong 1–2 ngày tới',
    ],
    exercises: [
      { icon: MessageSquareText, label: 'Nói chuyện với Serene', desc: 'Serene sẵn sàng ngay bây giờ' },
      { icon: Activity, label: 'Bài thở grounding', desc: '5 phút · Ổn định cơ thể' },
    ],
    actions: [
      { label: 'Quay về trang chủ', path: ROUTE_PATHS.home },
      { label: 'Mở Nhìn Lại', path: ROUTE_PATHS.reflect },
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
      'Những gì bạn đang trải qua có thể đã vượt quá khả năng tự cân bằng thông thường',
      'Việc tìm kiếm hỗ trợ chuyên nghiệp lúc này là một bước chăm sóc bản thân rất quan trọng',
      'Hãy cố gắng ở gần những người khiến bạn cảm thấy an toàn và được lắng nghe',
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
      'Mức độ căng thẳng hoặc kiệt sức hiện tại có thể đang ảnh hưởng mạnh đến tinh thần của bạn',
      'Bạn xứng đáng nhận được sự hỗ trợ ngay lúc này, thay vì cố gắng chịu đựng thêm',
      'Nếu thấy quá tải hoặc mất kiểm soát, hãy liên hệ người thân hoặc hotline hỗ trợ càng sớm càng tốt',
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
        <span className="text-theme-secondary">{label}</span>
        <span className="font-semibold text-theme-primary">{percent}%</span>
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
      saveScreeningResult(result)
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
      className="min-h-screen pb-28 pt-10 rounded-4xl"
      style={{ backgroundColor: meta.bgColor }}
    >
      <div className="mx-auto max-w-2xl px-5">

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
          <p className="mb-1  uppercase tracking-widest text-serene-primary">Kết quả</p>
          <h1 className="font-display text-4xl text-serene-ink">
            Mức{' '}
            <span style={{ color: meta.color }}>{meta.label}</span>
          </h1>
          {result && (
            <p className="mt-1 text-serene-ink">
              Điểm: {result.raw_score} · {result.instrument_id?.toUpperCase()}
            </p>
          )}
        </div>

        {/* Score visualization — dual bars */}
        <div className="mb-4 rounded-3xl bg-theme-surface p-5 shadow-sm">
          <h3 className="mb-4 font-semibold text-theme-primary text-sm">Điểm số của bạn</h3>
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
          <div className="mt-4 rounded-2xl border border-theme-border bg-theme-surface p-3">
            <p className="text-sm leading-relaxed text-theme-secondary">{meta.interpretation}</p>
          </div>
        </div>

        {/* Insights */}
        <div className="mb-4 rounded-3xl bg-theme-surface p-5 shadow-sm">
          <h3 className="mb-3 font-semibold text-theme-primary text-sm">Serene thấy gì</h3>
          <ul className="space-y-2.5">
            {meta.insights.map((item) => (
              <li key={item} className="flex items-start gap-2.5 text-sm text-theme-secondary">
                <span className="mt-0.5 flex-shrink-0" style={{ color: meta.color }} aria-hidden="true">
                  ●
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Recommended exercises */}
        <div className="mb-4 rounded-3xl bg-theme-surface p-5 shadow-sm">
          <h3 className="mb-3 font-semibold text-theme-primary text-sm">Gợi ý cho bạn</h3>
          <div className="grid grid-cols-2 gap-3">
            {meta.exercises.map((ex) => {
              const ExIcon = ex.icon
              return (
              <button
                key={ex.label}
                type="button"
                onClick={() => navigate(ROUTE_PATHS.exercises)}
                className="flex flex-col items-start rounded-2xl border border-theme-border bg-theme-surface p-3.5 text-left transition hover:bg-theme-accent/10"
              >
                <ExIcon className="mb-2 h-6 w-6 text-theme-accent" aria-hidden />
                <p className="text-sm font-semibold text-theme-primary leading-tight">{ex.label}</p>
                <p className="mt-0.5 text-xs text-serene-secondary">{ex.desc}</p>
              </button>
            )})}
          </div>
        </div>

        {/* Disclaimer */}
        <p className="mb-6 px-2 text-center text-xs leading-relaxed text-serene-muted">
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
                className="flex border border-theme-border bg-theme-surface hover:text-theme-accent cursor-pointer w-full items-center justify-center gap-2 rounded-2xl py-3.5 font-semibold text-sm transition-all active:scale-[0.97]"
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
            className="flex w-full items-center justify-center gap-2 rounded-2xl border border-theme-border bg-theme-surface py-3.5 text-sm font-medium text-theme-primary transition cursor-pointer hover:text-theme-accent active:scale-[0.97]"
          >
            <Share2 className="h-4 w-4" />
            Chia sẻ kết quả
          </button>

          {/* Retake */}
          <button
            type="button"
            onClick={() => navigate(ROUTE_PATHS.screening)}
            className="w-full py-2.5 text-center text-serene-ink transition hover:underline cursor-pointer"
          >
            Làm lại bài test khác
          </button>
        </div>

      </div>
    </motion.div>
  )
}
