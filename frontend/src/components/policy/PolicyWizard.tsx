import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { BadgeCheck, HeartHandshake, Lock, MessageCircle } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { policyService } from '../../services/policyService'
import { toast } from 'react-toastify'
import { ROUTE_PATHS } from '../../routes/paths'

type Slide = {
  icon: LucideIcon
  heading: string
  body: string
  persona?: string
}

const SLIDES: Slide[] = [
  {
    icon: HeartHandshake,
    heading: 'Nơi mọi cảm xúc được lắng nghe',
    body:
      'Serene được xây dựng để trở thành người bạn đồng hành, giúp bạn thấu hiểu bản thân và tìm thấy sự bình yên trong tâm trí. Tuy nhiên, các nhân vật AI không có chức năng thay thế bác sĩ hay các lộ trình trị liệu chuyên sâu. Hãy tìm đến chuyên gia y tế khi bạn cần một chẩn đoán y khoa chính thức.',
  },

  {
    icon: Lock,
    persona: 'Nhìn Lại',
    heading: 'Dữ liệu của bạn, an toàn với bạn',
    body: 'Thông tin nhạy cảm được mã hoá và ẩn danh hoá trước khi lưu. Bạn có thể xoá dữ liệu bất cứ lúc nào trong Cài đặt.',
  },
  {
    icon: MessageCircle,
    persona: 'Trò Chuyện',
    heading: 'AI vẫn có thể nhầm',
    body: 'Phản hồi của AI dựa trên ngữ cảnh cuộc trò chuyện — không phải chẩn đoán lâm sàng. Luôn tham khảo chuyên gia khi nghi ngờ.',
  },
  {
    icon: BadgeCheck,
    persona: 'Bạn',
    heading: 'Bạn đã sẵn sàng',
    body: 'Bằng cách nhấn "Tôi đồng ý", bạn xác nhận đã đọc và hiểu các điều trên. Serene sẽ cố gắng hết sức đồng hành cùng bạn.',
  },
]

export function PolicyWizard() {
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const isLast = step === SLIDES.length - 1
  const slide = SLIDES[step]
  const SlideIcon = slide.icon

  const handleNext = async () => {
    if (!isLast) {
      setStep((s) => s + 1)
      return
    }
    setLoading(true)
    try {
      await policyService.acknowledge()
      navigate(ROUTE_PATHS.onboarding)
    } catch {
      toast.error('Có lỗi xảy ra. Vui lòng thử lại.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[var(--color-serene-bg)] flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md">
        {/* Progress dots */}
        <div className="flex gap-2 justify-center mb-8">
          {SLIDES.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                i === step
                  ? 'w-6 bg-[var(--color-serene-primary)]'
                  : i < step
                    ? 'w-3 bg-[var(--color-serene-primary)]/40'
                    : 'w-3 bg-[var(--color-serene-outline)]'
              }`}
            />
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -40 }}
            transition={{ duration: 0.22 }}
            className="bg-white rounded-3xl p-8 shadow-sm text-center"
          >
            <div className="mb-4 flex justify-center">
              <SlideIcon className="h-14 w-14 text-[var(--color-serene-primary)]" aria-hidden />
            </div>
            {slide.persona ? (
              <p className="text-[10px] font-semibold text-[var(--color-serene-muted)] mb-2 tracking-widest uppercase">
                {slide.persona}
              </p>
            ) : null}
            <h2 className="font-[var(--font-display)] text-2xl text-[var(--color-serene-ink)] mb-4 leading-snug">
              {slide.heading}
            </h2>
            <p className="text-[var(--color-serene-muted)] leading-relaxed text-sm">{slide.body}</p>
          </motion.div>
        </AnimatePresence>

        <button
          type="button"
          onClick={handleNext}
          disabled={loading}
          className="mt-5 w-full bg-[var(--color-serene-primary)] hover:bg-[var(--color-serene-primary-dim)] text-[var(--color-serene-on-primary)] py-3.5 rounded-2xl font-semibold text-sm transition-all disabled:opacity-50"
        >
          {isLast ? (loading ? 'Đang lưu…' : 'Tôi đồng ý') : 'Tiếp theo'}
        </button>

        {step > 0 && (
          <button
            type="button"
            onClick={() => setStep((s) => s - 1)}
            disabled={loading}
            className="mt-3 w-full text-sm text-[var(--color-serene-muted)] hover:text-[var(--color-serene-ink)] transition"
          >
            Quay lại
          </button>
        )}
      </div>
    </div>
  )
}
