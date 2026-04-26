import { useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import type { ScreeningResult } from '../../services/screeningService'
import { ROUTE_PATHS } from '../../routes/paths'

type SeverityMeta = {
  label: string
  emoji: string
  color: string
  bgColor: string
  insights: string[]
  actions: Array<{ label: string; path: string; primary?: boolean }>
}

const SEVERITY_MAP: Record<ScreeningResult['severity_label'], SeverityMeta> = {
  minimal: {
    label: 'Nhẹ',
    emoji: '🌱',
    color: 'var(--color-an)',
    bgColor: 'var(--color-an-bg)',
    insights: [
      'Năng lượng và tâm trạng nhìn chung ổn định',
      'Tiếp tục duy trì thói quen hiện tại',
      'Thử một bài tập nhỏ hôm nay',
    ],
    actions: [
      { label: 'Thở cùng Lửa', path: ROUTE_PATHS.exercises, primary: true },
      { label: 'Về trang chính', path: ROUTE_PATHS.home },
    ],
  },
  mild: {
    label: 'Nhẹ vừa',
    emoji: '🌤️',
    color: 'var(--color-an)',
    bgColor: 'var(--color-an-bg)',
    insights: [
      'Có một vài dấu hiệu cần chú ý',
      'Trò chuyện ngắn có thể giúp ích',
      'Nhắc bản thân check-in lại ngày mai',
    ],
    actions: [
      { label: 'Trò chuyện với Mây', path: ROUTE_PATHS.chat, primary: true },
      { label: 'Mở Nhìn Lại', path: ROUTE_PATHS.reflect },
    ],
  },
  moderate: {
    label: 'Trung bình',
    emoji: '🌥️',
    color: 'var(--color-lua)',
    bgColor: 'var(--color-lua-bg)',
    insights: [
      'Cần chú ý hơn đến sức khoẻ tâm thần',
      'Nên trao đổi với ai đó trong 24h tới',
      'Bài tập grounding có thể giúp ổn định ngay',
    ],
    actions: [
      { label: 'Trò chuyện với Mây ngay', path: ROUTE_PATHS.chat, primary: true },
      { label: 'Tập thở với Lửa', path: ROUTE_PATHS.exercises },
    ],
  },
  moderately_severe: {
    label: 'Khá cao',
    emoji: '⛅',
    color: 'var(--color-la-ban)',
    bgColor: 'var(--color-la-ban-bg)',
    insights: [
      'Kết quả cho thấy cần hỗ trợ chuyên nghiệp',
      'Kết Nối có thể chỉ bạn tới nguồn phù hợp',
      'Bạn không cần đi qua điều này một mình',
    ],
    actions: [
      { label: 'Mở Kết Nối', path: ROUTE_PATHS.connect, primary: true },
      { label: 'Trò chuyện với Mây', path: ROUTE_PATHS.chat },
    ],
  },
  severe: {
    label: 'Cao',
    emoji: '🌧️',
    color: 'var(--color-la-ban)',
    bgColor: 'var(--color-la-ban-bg)',
    insights: [
      'Kết quả quan trọng — cần được hỗ trợ sớm',
      'Vui lòng liên hệ Kết Nối hoặc gọi hotline',
      'Bạn đã rất dũng cảm khi làm bài này',
    ],
    actions: [
      { label: 'Mở Kết Nối ngay', path: ROUTE_PATHS.connect, primary: true },
      { label: 'Hotline 1800-599-920', path: 'tel' },
    ],
  },
}

export function ResultsPage() {
  const { state } = useLocation()
  const navigate = useNavigate()
  const result = state?.result as ScreeningResult | undefined
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

  return (
    <div className="min-h-screen px-5 pt-10 pb-28" style={{ backgroundColor: meta.bgColor }}>
      <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}>

        {/* Header */}
        <div className="text-center mb-8">
          <div className="text-6xl mb-3" aria-hidden="true">{meta.emoji}</div>
          <p className="text-[10px] uppercase tracking-widest text-[var(--color-serene-muted)] mb-1">Kết quả</p>
          <h1 className="font-[var(--font-display)] text-3xl text-[var(--color-serene-ink)]">
            Mức{' '}
            <span style={{ color: meta.color }}>{meta.label}</span>
          </h1>
          {result && (
            <p className="text-xs text-[var(--color-serene-muted)] mt-1">
              Điểm: {result.raw_score} · {result.instrument_id?.toUpperCase() ?? result.instrument_id}
            </p>
          )}
        </div>

        {/* Insights */}
        <div className="bg-white rounded-3xl p-5 mb-4 shadow-sm">
          <h3 className="font-semibold text-[var(--color-serene-ink)] mb-3 text-sm">Mình thấy gì</h3>
          <ul className="space-y-2">
            {meta.insights.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-[var(--color-serene-muted)]">
                <span className="mt-0.5 flex-shrink-0" style={{ color: meta.color }} aria-hidden="true">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Disclaimer */}
        <p className="text-[10px] text-[var(--color-serene-muted)] text-center mb-8 px-2 leading-relaxed">
          Đây không phải chẩn đoán lâm sàng. Nếu lo ngại, hãy gặp chuyên gia sức khoẻ tâm thần.
        </p>

        {/* Actions */}
        <div className="flex flex-col gap-3">
          {meta.actions.map((a, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleAction(a.path)}
              className="w-full py-3.5 rounded-2xl font-semibold text-sm transition-all active:scale-[0.97]"
              style={
                a.primary
                  ? { backgroundColor: meta.color, color: 'white' }
                  : { backgroundColor: 'var(--color-serene-surface)', color: 'var(--color-serene-ink)' }
              }
            >
              {a.label}
            </button>
          ))}
        </div>

      </motion.div>
    </div>
  )
}
