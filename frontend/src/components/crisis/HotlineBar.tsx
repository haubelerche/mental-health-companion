import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Phone, X } from 'lucide-react'

type Hotline = {
  name: string
  number: string
}

type HotlineBarProps = {
  visible: boolean
  hotlines?: Hotline[]
}

const DEFAULT_HOTLINES: Hotline[] = [
  { name: 'Hỗ trợ 24/7', number: '1800-599-920' },
  { name: 'Cấp cứu', number: '115' },
]

export function HotlineBar({ visible, hotlines = DEFAULT_HOTLINES }: HotlineBarProps) {
  const [dismissed, setDismissed] = useState(false)
  // Track previous visible value to detect false → true transition (new SOS trigger)
  const [prevVisible, setPrevVisible] = useState(visible)

  if (visible !== prevVisible) {
    setPrevVisible(visible)
    if (visible) setDismissed(false)
  }

  return (
    <AnimatePresence>
      {visible && !dismissed && (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 280, damping: 28 }}
          className="fixed bottom-20 left-3 right-3 z-50 bg-white border border-red-100 rounded-3xl shadow-2xl p-4"
        >
          <div className="flex items-start justify-between mb-3">
            <div>
              <p className="text-[10px] font-bold text-red-500 uppercase tracking-widest mb-0.5">
                Hỗ trợ khẩn
              </p>
              <p className="text-xs text-[var(--color-serene-muted)] leading-relaxed">
                Bạn không đơn độc. Có người sẵn sàng nghe bạn.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setDismissed(true)}
              className="text-[var(--color-serene-outline)] hover:text-[var(--color-serene-muted)] transition ml-3 flex-shrink-0"
              aria-label="Đóng thông báo hỗ trợ"
            >
              <X size={15} />
            </button>
          </div>
          <div className="flex gap-2 flex-wrap">
            {hotlines.map(h => (
              <a
                key={h.number}
                href={`tel:${h.number.replace(/[-\s]/g, '')}`}
                className="flex items-center gap-1.5 bg-red-50 hover:bg-red-100 text-red-600 rounded-full px-3 py-1.5 text-xs font-semibold transition-all"
              >
                <Phone size={11} aria-hidden="true" />
                {h.name} · {h.number}
              </a>
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
