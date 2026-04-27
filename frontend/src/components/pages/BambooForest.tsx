import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Check, ChevronLeft, Flame, Info, Leaf, Send, Sparkles, Wind, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import {
  anonymousShareService,
  type BambooCategory,
  type BambooMessage,
} from '../../services/anonymousShareService'
import { ROUTE_PATHS } from '../../routes/paths'

// ── Types & constants ──────────────────────────────────────────────────────────
type Tab = 'write' | 'inbox'
type WriteStage = 'compose' | 'confirm' | 'done'

const MAX_CHARS = 280

const CATEGORIES: Array<{ id: BambooCategory; label: string; icon: string; desc: string }> = [
  { id: 'encouragement', label: 'Lời khích lệ', icon: '🌟', desc: 'Gửi năng lượng tích cực tới ai đó' },
  { id: 'sharing', label: 'Chia sẻ', icon: '🌿', desc: 'Kể điều bạn đang trải qua' },
  { id: 'question', label: 'Hỏi đáp', icon: '🍃', desc: 'Đặt câu hỏi cho thế giới' },
]

const CATEGORY_COLORS: Record<BambooCategory, { bg: string; text: string; border: string }> = {
  encouragement: { bg: '#f0fdf4', text: '#15803d', border: '#bbf7d0' },
  sharing: { bg: '#f0f9ff', text: '#0369a1', border: '#bae6fd' },
  question: { bg: '#fefce8', text: '#a16207', border: '#fef08a' },
}

const CATEGORY_LABELS: Record<BambooCategory, string> = {
  encouragement: 'Lời khích lệ',
  sharing: 'Chia sẻ',
  question: 'Hỏi đáp',
}

const CONFIRM_ITEMS = [
  'Thông điệp không chứa nội dung có hại, kỳ thị hoặc gây tổn thương',
  'Không có thông tin nhận dạng cá nhân (tên, số điện thoại, địa chỉ)',
  'Phù hợp để chia sẻ với một người lạ đang cần hỗ trợ',
]

// ── Helper ─────────────────────────────────────────────────────────────────────
function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'Vừa xong'
  if (m < 60) return `${m} phút trước`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} giờ trước`
  return `${Math.floor(h / 24)} ngày trước`
}

// ── Community Guidelines Modal ─────────────────────────────────────────────────
function GuidelinesModal({ onClose }: { onClose: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 backdrop-blur-sm sm:items-center"
      onClick={onClose}
    >
      <motion.div
        initial={{ y: 60, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 40, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 280, damping: 28 }}
        onClick={(e) => e.stopPropagation()}
        className="mx-4 mb-6 w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl sm:mb-0"
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-display text-2xl text-serene-ink">Nguyên tắc Rừng Trúc</h3>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-full text-serene-muted hover:bg-serene-border/40"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <ul className="space-y-3 text-sm text-serene-muted">
          {[
            { icon: '🌿', text: 'Chia sẻ từ trái tim — không phán xét, không công kích' },
            { icon: '🔒', text: 'Tuyệt đối ẩn danh — không ai biết bạn là ai' },
            { icon: '🛡️', text: 'Không nội dung gây hại, kỳ thị, hoặc thông tin cá nhân' },
            { icon: '💚', text: 'Người nhận cũng là một con người đang cần hỗ trợ — hãy nhẹ nhàng' },
            { icon: '🌊', text: '"Gửi vào dòng suối" = đến tay người lạ; "Đốt an toàn" = không ai đọc' },
          ].map((item) => (
            <li key={item.text} className="flex items-start gap-3">
              <span className="flex-shrink-0 text-lg">{item.icon}</span>
              <span>{item.text}</span>
            </li>
          ))}
        </ul>
        <button
          type="button"
          onClick={onClose}
          className="mt-5 w-full rounded-2xl bg-serene-primary py-3 font-semibold text-serene-on-primary"
        >
          Tôi hiểu rồi
        </button>
      </motion.div>
    </motion.div>
  )
}

// ── Confirm Modal ──────────────────────────────────────────────────────────────
function ConfirmModal({
  message,
  category,
  onSend,
  onBurn,
  onBack,
  sending,
}: {
  message: string
  category: BambooCategory
  onSend: () => void
  onBurn: () => void
  onBack: () => void
  sending: boolean
}) {
  const [checked, setChecked] = useState<boolean[]>(CONFIRM_ITEMS.map(() => false))
  const allChecked = checked.every(Boolean)
  const catStyle = CATEGORY_COLORS[category]

  const toggle = (i: number) =>
    setChecked((prev) => prev.map((v, idx) => (idx === i ? !v : v)))

  return (
    <motion.div
      key="confirm"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm sm:items-center"
    >
      <motion.div
        initial={{ y: 80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 40, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 260, damping: 26 }}
        className="mx-4 mb-4 w-full max-w-md overflow-hidden rounded-3xl bg-white shadow-2xl sm:mb-0"
      >
        {/* Header */}
        <div className="border-b border-serene-border/40 px-6 py-5">
          <div className="flex items-center gap-2">
            <button type="button" onClick={onBack} className="text-serene-muted hover:text-serene-ink">
              <ChevronLeft className="h-5 w-5" />
            </button>
            <h3 className="flex-1 text-center font-display text-xl text-serene-ink">
              Xác nhận thông điệp
            </h3>
          </div>
        </div>

        <div className="max-h-[70vh] overflow-y-auto px-6 py-5">
          {/* Message preview */}
          <div
            className="mb-5 rounded-2xl border p-4"
            style={{ backgroundColor: catStyle.bg, borderColor: catStyle.border }}
          >
            <p
              className="mb-2 text-[10px] font-semibold uppercase tracking-widest"
              style={{ color: catStyle.text }}
            >
              {CATEGORY_LABELS[category]}
            </p>
            <p className="text-sm leading-relaxed text-serene-ink">{message}</p>
          </div>

          {/* Confirmation checklist */}
          <div className="mb-6">
            <p className="mb-3 text-sm font-semibold text-serene-ink">
              Trước khi gửi, hãy xác nhận:
            </p>
            <div className="space-y-3">
              {CONFIRM_ITEMS.map((item, i) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => toggle(i)}
                  className={`flex w-full items-start gap-3 rounded-2xl border p-3.5 text-left transition-all ${
                    checked[i]
                      ? 'border-serene-primary/40 bg-serene-primary/8'
                      : 'border-serene-border bg-white hover:border-serene-primary/30'
                  }`}
                >
                  <span
                    className={`mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border-2 transition-all ${
                      checked[i]
                        ? 'border-serene-primary bg-serene-primary'
                        : 'border-serene-border bg-white'
                    }`}
                  >
                    {checked[i] && <Check className="h-3 w-3 text-white" strokeWidth={3} />}
                  </span>
                  <span className="text-sm leading-snug text-serene-muted">{item}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-col gap-3">
            <button
              type="button"
              onClick={onSend}
              disabled={!allChecked || sending}
              className="flex w-full items-center justify-center gap-2 rounded-full bg-serene-primary py-4 font-semibold text-serene-on-primary shadow-lg shadow-serene-primary/20 transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-40 active:scale-[0.97]"
            >
              <Send className="h-4 w-4" />
              {sending ? 'Đang gửi...' : 'Gửi vào dòng suối 🌊'}
            </button>

            <button
              type="button"
              onClick={onBurn}
              disabled={sending}
              className="flex w-full items-center justify-center gap-2 rounded-full border border-serene-border bg-white py-4 font-semibold text-serene-muted transition hover:bg-orange-50 hover:border-orange-200 hover:text-orange-600 active:scale-[0.97]"
            >
              <Flame className="h-4 w-4" />
              Đốt an toàn 🔥
            </button>

            <p className="text-center text-[11px] text-serene-muted leading-relaxed">
              "Gửi vào dòng suối" — người nhận ngẫu nhiên sẽ đọc thông điệp này.
              <br />
              "Đốt an toàn" — thông điệp sẽ bị xoá ngay, không ai đọc được.
            </p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── Done Splash ────────────────────────────────────────────────────────────────
function DoneSplash({ onReset }: { onReset: () => void }) {
  return (
    <motion.div
      key="done"
      initial={{ opacity: 0, scale: 0.92 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center py-16 text-center"
    >
      <motion.div
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
        className="mb-6 text-6xl"
      >
        🌊
      </motion.div>
      <h2 className="font-display text-3xl text-[#1c4a3d]">Đã gửi vào dòng suối</h2>
      <p className="mt-3 max-w-xs text-sm leading-relaxed text-[#4a7060]/80">
        Thông điệp của bạn đang trên đường đến tay ai đó đang cần nghe điều này. Cảm ơn bạn đã chia sẻ.
      </p>
      <div className="mt-8 flex gap-4">
        <motion.div
          animate={{ x: [-40, 0], opacity: [0, 1] }}
          transition={{ delay: 0.4 }}
          className="rounded-2xl bg-white/60 px-4 py-2 text-sm text-[#4a7060]"
        >
          🌿 Ẩn danh hoàn toàn
        </motion.div>
        <motion.div
          animate={{ x: [40, 0], opacity: [0, 1] }}
          transition={{ delay: 0.55 }}
          className="rounded-2xl bg-white/60 px-4 py-2 text-sm text-[#4a7060]"
        >
          ♥ +5 tim
        </motion.div>
      </div>
      <button
        type="button"
        onClick={onReset}
        className="mt-10 rounded-full border border-[#4a7060]/30 bg-white/50 px-6 py-3 text-sm font-semibold text-[#1c4a3d] backdrop-blur-sm transition hover:bg-white/80"
      >
        Viết thông điệp khác
      </button>
    </motion.div>
  )
}

// ── Burn Splash ────────────────────────────────────────────────────────────────
function BurnSplash({ onReset }: { onReset: () => void }) {
  return (
    <motion.div
      key="burn"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center py-16 text-center"
    >
      <motion.div
        animate={{ scale: [1, 1.15, 1], rotate: [0, 5, -5, 0] }}
        transition={{ duration: 1.2, repeat: 2 }}
        className="mb-6 text-6xl"
      >
        🔥
      </motion.div>
      <h2 className="font-display text-3xl text-[#1c4a3d]">Đã đốt an toàn</h2>
      <p className="mt-3 max-w-xs text-sm leading-relaxed text-[#4a7060]/80">
        Thông điệp đã được xoá hoàn toàn. Đôi khi, chỉ cần viết ra là đủ.
      </p>
      <button
        type="button"
        onClick={onReset}
        className="mt-10 rounded-full border border-[#4a7060]/30 bg-white/50 px-6 py-3 text-sm font-semibold text-[#1c4a3d] backdrop-blur-sm transition hover:bg-white/80"
      >
        Viết lại
      </button>
    </motion.div>
  )
}

// ── Inbox card ─────────────────────────────────────────────────────────────────
function InboxCard({ msg }: { msg: BambooMessage }) {
  const catStyle = CATEGORY_COLORS[msg.category]
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-3xl bg-white/75 p-5 shadow-[0_2px_12px_rgba(47,52,46,0.08)] backdrop-blur-sm"
    >
      <div className="mb-3 flex items-center justify-between">
        <span
          className="rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide"
          style={{ backgroundColor: catStyle.bg, color: catStyle.text }}
        >
          {CATEGORY_LABELS[msg.category]}
        </span>
        <span className="text-[11px] text-[#8a9e94]">{timeAgo(msg.received_at)}</span>
      </div>
      <p className="text-sm leading-relaxed text-[#2f342e]">{msg.content}</p>
      <div className="mt-3 flex items-center gap-1.5 text-[11px] text-[#8a9e94]">
        <Leaf className="h-3 w-3" />
        <span>Người lạ · Ẩn danh</span>
      </div>
    </motion.div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────────
export function BambooForestPage() {
  const navigate = useNavigate()

  const [tab, setTab] = useState<Tab>('write')
  const [stage, setStage] = useState<WriteStage>('compose')
  const [text, setText] = useState('')
  const [category, setCategory] = useState<BambooCategory>('encouragement')
  const [showGuidelines, setShowGuidelines] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [sending, setSending] = useState(false)
  const [inbox, setInbox] = useState<BambooMessage[]>([])
  const [inboxLoading, setInboxLoading] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const remaining = MAX_CHARS - text.length
  const canPreview = text.trim().length >= 10

  // Load inbox when tab switches
  useEffect(() => {
    if (tab !== 'inbox') return
    setInboxLoading(true)
    anonymousShareService
      .getInbox()
      .then((res) => setInbox(res.messages))
      .catch(() => undefined)
      .finally(() => setInboxLoading(false))
  }, [tab])

  const handleSend = async () => {
    if (!canPreview) return
    setSending(true)
    try {
      await anonymousShareService.send({ content: text.trim(), category })
      setShowConfirm(false)
      setStage('done')
    } catch {
      toast.error('Không thể gửi lúc này. Vui lòng thử lại.')
    } finally {
      setSending(false)
    }
  }

  const handleBurn = () => {
    setShowConfirm(false)
    setStage('burn' as WriteStage)
  }

  const handleReset = () => {
    setText('')
    setStage('compose')
    setCategory('encouragement')
    setTimeout(() => textareaRef.current?.focus(), 100)
  }

  const catStyle = CATEGORY_COLORS[category]

  return (
    <>
      {/* ── Modals (portalled above everything) ── */}
      <AnimatePresence>
        {showGuidelines && <GuidelinesModal onClose={() => setShowGuidelines(false)} />}
      </AnimatePresence>

      <AnimatePresence>
        {showConfirm && stage === 'compose' && (
          <ConfirmModal
            message={text.trim()}
            category={category}
            onSend={handleSend}
            onBurn={handleBurn}
            onBack={() => setShowConfirm(false)}
            sending={sending}
          />
        )}
      </AnimatePresence>

      {/* ── Page wrapper — bamboo forest aesthetic ── */}
      <div
        className="relative -m-5 min-h-[calc(100vh-5rem)] overflow-hidden sm:-m-8 lg:-m-12"
        style={{ background: 'linear-gradient(160deg, #1a3328 0%, #243d2f 40%, #1e3b32 100%)' }}
      >
        {/* Decorative bamboo stalks (pure CSS) */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden opacity-15">
          {[6, 18, 74, 88].map((left) => (
            <div
              key={left}
              className="absolute bottom-0 top-0 w-1 rounded-full"
              style={{
                left: `${left}%`,
                background: 'linear-gradient(180deg, #6aad7a 0%, #3d7a50 60%, transparent 100%)',
              }}
            />
          ))}
        </div>

        <div className="relative px-5 py-8 sm:px-8">
          {/* Header */}
          <header className="mb-6 flex items-center gap-4">
            <button
              type="button"
              onClick={() => navigate(ROUTE_PATHS.home)}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-white/15 text-white/80 backdrop-blur-md transition hover:bg-white/25"
              aria-label="Quay lại"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>

            <div className="flex-1">
              <h1 className="font-display text-3xl text-white/95">Rừng Trúc</h1>
              <p className="text-xs text-white/55">Chia sẻ ẩn danh · Không ai biết bạn là ai</p>
            </div>

            <button
              type="button"
              onClick={() => setShowGuidelines(true)}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-white/15 text-white/70 backdrop-blur-md transition hover:bg-white/25"
              aria-label="Nguyên tắc cộng đồng"
            >
              <Info className="h-5 w-5" />
            </button>
          </header>

          {/* Tabs */}
          <div className="mb-6 flex rounded-2xl bg-white/10 p-1 backdrop-blur-md">
            {(['write', 'inbox'] as Tab[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold transition-all ${
                  tab === t
                    ? 'bg-white text-[#1c4a3d] shadow-sm'
                    : 'text-white/60 hover:text-white/80'
                }`}
              >
                {t === 'write' ? (
                  <>
                    <Sparkles className="h-3.5 w-3.5" />
                    Viết thông điệp
                  </>
                ) : (
                  <>
                    <Wind className="h-3.5 w-3.5" />
                    Nhận được
                    {inbox.length > 0 && (
                      <span className="flex h-4 w-4 items-center justify-center rounded-full bg-serene-primary text-[10px] font-bold text-white">
                        {inbox.length}
                      </span>
                    )}
                  </>
                )}
              </button>
            ))}
          </div>

          {/* ── Write tab ── */}
          <AnimatePresence mode="wait">
            {tab === 'write' && (
              <motion.div
                key="write"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                {stage === 'compose' && (
                  <div className="space-y-4">
                    {/* Category selector */}
                    <div className="grid grid-cols-3 gap-2">
                      {CATEGORIES.map((cat) => (
                        <button
                          key={cat.id}
                          type="button"
                          onClick={() => setCategory(cat.id)}
                          className={`flex flex-col items-center gap-1.5 rounded-2xl border p-3 transition-all ${
                            category === cat.id
                              ? 'border-white/50 bg-white/20 shadow-sm'
                              : 'border-white/15 bg-white/8 hover:bg-white/15'
                          }`}
                        >
                          <span className="text-xl">{cat.icon}</span>
                          <span className={`text-center text-[11px] font-semibold leading-tight ${category === cat.id ? 'text-white' : 'text-white/65'}`}>
                            {cat.label}
                          </span>
                        </button>
                      ))}
                    </div>

                    {/* Textarea */}
                    <div
                      className="overflow-hidden rounded-3xl border shadow-[0_8px_32px_rgba(0,0,0,0.25)]"
                      style={{ borderColor: catStyle.border + '80', backgroundColor: 'rgba(255,255,255,0.92)' }}
                    >
                      <div className="px-5 pt-4">
                        <span
                          className="text-[10px] font-semibold uppercase tracking-widest"
                          style={{ color: catStyle.text }}
                        >
                          {CATEGORIES.find((c) => c.id === category)?.desc}
                        </span>
                      </div>
                      <textarea
                        ref={textareaRef}
                        value={text}
                        onChange={(e) => setText(e.target.value.slice(0, MAX_CHARS))}
                        rows={6}
                        placeholder="Viết điều bạn muốn gửi đến một người lạ đang cần nghe điều này..."
                        autoFocus
                        className="w-full resize-none bg-transparent px-5 pb-3 pt-3 text-[15px] leading-relaxed text-[#2f342e] placeholder-[#8a9e94]/70 outline-none"
                      />
                      <div className="flex items-center justify-between border-t border-[#e4ece7]/60 px-5 py-3">
                        <span className={`text-xs font-medium ${remaining < 30 ? 'text-orange-500' : 'text-[#8a9e94]'}`}>
                          {remaining} ký tự còn lại
                        </span>
                        <div className="flex gap-2">
                          {[10, 20, 30].map((pct) => (
                            <span
                              key={pct}
                              className="h-1.5 w-5 rounded-full"
                              style={{
                                backgroundColor:
                                  text.length / MAX_CHARS >= pct / 30
                                    ? catStyle.text
                                    : '#e4ece7',
                              }}
                            />
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Info */}
                    <div className="flex items-start gap-2.5 rounded-2xl bg-white/10 p-3.5 backdrop-blur-sm">
                      <Leaf className="mt-0.5 h-4 w-4 flex-shrink-0 text-white/60" />
                      <p className="text-xs leading-relaxed text-white/60">
                        Thông điệp được gửi ẩn danh tới một người dùng ngẫu nhiên. Serene không lưu tên hay thông tin nhận dạng của bạn.
                      </p>
                    </div>

                    {/* Preview button */}
                    <button
                      type="button"
                      onClick={() => setShowConfirm(true)}
                      disabled={!canPreview}
                      className="flex w-full items-center justify-center gap-2 rounded-full bg-white py-4 font-semibold text-[#1c4a3d] shadow-lg shadow-black/20 transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-40 active:scale-[0.97]"
                    >
                      <Send className="h-4 w-4" />
                      Xem trước & Xác nhận
                    </button>
                  </div>
                )}

                {stage === 'done' && <DoneSplash onReset={handleReset} />}
                {(stage as string) === 'burn' && <BurnSplash onReset={handleReset} />}
              </motion.div>
            )}

            {/* ── Inbox tab ── */}
            {tab === 'inbox' && (
              <motion.div
                key="inbox"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-white/80">
                    Thông điệp từ người lạ
                  </p>
                  <span className="text-xs text-white/50">Cập nhật mỗi lần mở</span>
                </div>

                {inboxLoading ? (
                  <div className="flex items-center justify-center py-16">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
                      className="h-8 w-8 rounded-full border-2 border-white/20 border-t-white/80"
                    />
                  </div>
                ) : inbox.length === 0 ? (
                  <div className="py-16 text-center">
                    <p className="text-4xl">🌿</p>
                    <p className="mt-3 text-sm text-white/50">Chưa có thông điệp nào. Hộp thư sẽ đầy dần theo thời gian.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {inbox.map((msg, i) => (
                      <motion.div
                        key={msg.id}
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.06 }}
                      >
                        <InboxCard msg={msg} />
                      </motion.div>
                    ))}
                  </div>
                )}

                <div className="rounded-2xl bg-white/8 p-4 text-center">
                  <p className="text-xs text-white/45 leading-relaxed">
                    Những thông điệp này đến từ người dùng ẩn danh. Serene không tiết lộ danh tính người gửi.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </>
  )
}
