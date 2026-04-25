import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { policyService } from '../../services/policyService'
import { toast } from 'react-toastify'

const SLIDES = [
  {
    icon: '🤝',
    persona: 'An · Trò Chuyện · Thư Viện · Kết Nối · Nhìn Lại',
    heading: 'Đồng hành, không chẩn đoán',
    body: 'Các nhân vật AI trong Serene chỉ hỗ trợ và tham vấn thông tin — không thay thế chuyên gia sức khoẻ tâm thần.',
  },
  {
    icon: '🆘',
    persona: 'Kết Nối',
    heading: 'Khủng hoảng — ưu tiên người thật',
    body: 'Khi có nguy cơ, hãy liên hệ đường dây nóng 1800-599-920 hoặc cấp cứu 115 ngay. Serene sẽ luôn hiển thị hotline khi cần.',
  },
  {
    icon: '🔒',
    persona: 'Nhìn Lại',
    heading: 'Dữ liệu của bạn, an toàn với bạn',
    body: 'Thông tin nhạy cảm được mã hoá và ẩn danh hoá trước khi lưu. Bạn có thể xoá dữ liệu bất cứ lúc nào trong Cài đặt.',
  },
  {
    icon: '🗣️',
    persona: 'Trò Chuyện',
    heading: 'AI vẫn có thể nhầm',
    body: 'Phản hồi của AI dựa trên ngữ cảnh cuộc trò chuyện — không phải chẩn đoán lâm sàng. Luôn tham khảo chuyên gia khi nghi ngờ.',
  },
  {
    icon: '✅',
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

  const handleNext = async () => {
    if (!isLast) {
      setStep(s => s + 1)
      return
    }
    setLoading(true)
    try {
      await policyService.acknowledge()
      navigate('/serene')
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
            <div className="text-5xl mb-4">{slide.icon}</div>
            <p className="text-[10px] font-semibold text-[var(--color-serene-muted)] mb-2 tracking-widest uppercase">
              {slide.persona}
            </p>
            <h2 className="font-[var(--font-display)] text-2xl text-[var(--color-serene-ink)] mb-4 leading-snug">
              {slide.heading}
            </h2>
            <p className="text-[var(--color-serene-muted)] leading-relaxed text-sm">{slide.body}</p>
          </motion.div>
        </AnimatePresence>

        <button
          onClick={handleNext}
          disabled={loading}
          className="mt-5 w-full bg-[var(--color-serene-primary)] hover:bg-[var(--color-serene-primary-dim)] text-[var(--color-serene-on-primary)] py-3.5 rounded-2xl font-semibold text-sm transition-all disabled:opacity-50"
        >
          {isLast ? (loading ? 'Đang lưu…' : 'Tôi đồng ý ✓') : 'Tiếp theo →'}
        </button>

        {step > 0 && (
          <button
            onClick={() => setStep(s => s - 1)}
            disabled={loading}
            className="mt-3 w-full text-sm text-[var(--color-serene-muted)] hover:text-[var(--color-serene-ink)] transition"
          >
            ← Quay lại
          </button>
        )}
      </div>
    </div>
  )
}
