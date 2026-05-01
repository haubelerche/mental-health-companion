import { useEffect, useRef, useState } from 'react'
import type { MouseEvent as ReactMouseEvent } from 'react'
import { toast } from 'react-toastify'
import paperBoatImage from '../../assets/thuyen.png'
import beachBackgroundImage from '../../assets/beach-message-bg.avif'
import {
  anonymousShareService,
  type LetterInboxItem,
  type ReplyArchiveItem,
  type SentLetterItem,
} from '../../services/anonymousShareService'
import {
  APP_SETTINGS_STORAGE_KEY,
  APP_SETTINGS_UPDATED_EVENT,
  readAppSettings,
  type AppSettings,
} from '../../utils/appSettings'
import { ApiRequestError } from '../../api/types'

type Letter = {
  id: string
  from: string
  time: string
  body: string
  direction?: 'sent' | 'received'
  status?: string
}

type TabId = 'beach' | 'community'

const FontLink = () => (
  <link
    href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400;1,500&family=Inter:wght@300;400;500&display=swap"
    rel="stylesheet"
  />
)

const ANIMATIONS_CSS = `
  @keyframes fadeUp     { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
  @keyframes fadeIn     { from{opacity:0} to{opacity:1} }
  @keyframes letterOpen { from{opacity:0;transform:translateY(10px) scale(0.98)} to{opacity:1;transform:translateY(0) scale(1)} }
  @keyframes fadeUpCard { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
  @keyframes bottleFloat {
    0%   { transform: translateY(0px)   rotate(-1.5deg); }
    25%  { transform: translateY(-8px)  rotate(1deg); }
    50%  { transform: translateY(-13px) rotate(-1deg); }
    75%  { transform: translateY(-6px)  rotate(1.5deg); }
    100% { transform: translateY(0px)   rotate(-1.5deg); }
  }
  @keyframes rippleExpand {
    0%   { transform: scale(1);   opacity: 0.7; }
    60%  { opacity: 0.3; }
    100% { transform: scale(2.4); opacity: 0; }
  }
  @keyframes bottleShadow {
    0%,100% { transform: scaleX(1);   opacity: 0.22; }
    50%     { transform: scaleX(0.78); opacity: 0.13; }
  }
`

const getUi = (dark: boolean) => ({
  textPrimary: dark ? 'text-white' : 'text-slate-900',
  textSubtle: dark ? 'text-white' : 'text-slate-800',
  textSubtler: dark ? 'text-white/50' : 'text-slate-900',
  glassLight: dark ? 'bg-slate-900/50 border-stone-50/20' : 'bg-white/86 border-stone-950/18',
  glassBorder: dark ? 'border-stone-50/20' : 'border-stone-950/18',
  overlay: dark ? 'bg-slate-950/74' : 'bg-slate-900/26',
})

function formatRelativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const diffMinutes = Math.max(1, Math.floor(diffMs / 60000))
  if (diffMinutes < 60) return `${diffMinutes} phút trước`
  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours} giờ trước`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays} ngày trước`
  return new Date(iso).toLocaleDateString('vi-VN')
}

function toLetter(message: LetterInboxItem): Letter {
  return {
    id: message.id,
    from: 'Một người vô danh',
    time: formatRelativeTime(message.received_at),
    body: message.content,
    direction: 'received',
    status: message.status ?? (message.reply ? 'replied' : 'approved'),
  }
}

function pickRandomLetter(messages: LetterInboxItem[]): Letter | null {
  if (!messages.length) return null
  const index = Math.floor(Math.random() * messages.length)
  return toLetter(messages[index])
}

function CinematicBg({ dark }: { dark: boolean }) {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <div
        className={`absolute inset-0 transition-all duration-500 ${
          dark ? 'brightness-60 saturate-95' : 'brightness-92 saturate-105'
        }`}
        style={{
          backgroundImage: `url(${beachBackgroundImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      />
      <div
        className={`absolute bottom-0 left-0 right-0 h-2/5 transition-all duration-1000 ${
          dark
            ? 'bg-linear-to-b from-transparent via-slate-900/50 to-slate-950/90'
            : 'bg-linear-to-b from-transparent via-blue-900/50 to-blue-950/75'
        }`}
      />
    </div>
  )
}

function FloatingBottle({ dark, onClick, isClicked }: { dark: boolean; onClick: () => void; isClicked: boolean }) {
  const rC = dark ? 'rgba(110,170,205,' : 'rgba(70,140,175,'
  return (
    <div onClick={onClick} className="relative flex flex-col items-center cursor-pointer select-none">
      <svg
        viewBox="0 0 340 70"
        className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-96 h-20 overflow-visible pointer-events-none z-0"
      >
        <ellipse
          cx="170"
          cy="38"
          rx="90"
          ry="12"
          fill={dark ? 'rgba(0,0,0,0.30)' : 'rgba(0,0,0,0.15)'}
          style={{ animation: 'bottleShadow 4.4s ease-in-out infinite', transformOrigin: '170px 38px' }}
        />
        {[{ rx: 82, ry: 14, d: '0s' }, { rx: 112, ry: 19, d: '0.9s' }, { rx: 144, ry: 24, d: '1.8s' }].map(
          (r, i) => (
            <ellipse
              key={i}
              cx="170"
              cy="38"
              rx={r.rx}
              ry={r.ry}
              fill="none"
              stroke={`${rC}${0.44 - i * 0.09})`}
              strokeWidth={1.4 - i * 0.15}
              style={{ animation: 'rippleExpand 3.6s ease-out infinite', animationDelay: r.d, transformOrigin: '170px 38px' }}
            />
          ),
        )}
      </svg>
      <div
        className="relative z-10 mb-7 transition-transform duration-350 ease-out"
        style={{
          animation: isClicked ? 'none' : 'bottleFloat 4.4s ease-in-out infinite',
          transform: isClicked ? 'scale(0.93) translateY(5px)' : 'scale(1) translateY(0)',
        }}
      >
        <img
          src={paperBoatImage}
          alt="Thuyền giấy"
          className={`w-72 h-auto display block ${dark ? 'drop-shadow-2xl brightness-92 sepia-5' : 'drop-shadow-2xl brightness-102'}`}
        />
      </div>
    </div>
  )
}

function LetterOverlay({
  letter,
  onClose,
  dark,
  onReply,
  onPass,
}: {
  letter: Letter
  onClose: () => void
  dark: boolean
  onReply: (content: string) => Promise<void>
  onPass: () => Promise<void>
}) {
  const ui = getUi(dark)
  const [replyOpen, setReplyOpen] = useState(false)
  const [reply, setReply] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [busyAction, setBusyAction] = useState<'pass' | 'reply' | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const areaRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    if (replyOpen) areaRef.current?.focus()
  }, [replyOpen])

  return (
    <div
      onClick={(e: ReactMouseEvent<HTMLDivElement>) => e.target === e.currentTarget && onClose()}
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 ${ui.overlay} backdrop-blur-2xl`}
      style={{ animation: 'fadeIn 0.45s ease' }}
    >
      <div
        className={`${ui.glassLight} border w-full max-w-xl rounded-2xl backdrop-blur-2xl`}
        style={{ animation: 'letterOpen 0.65s cubic-bezier(0.22,1,0.36,1) both' }}
      >
        <div className={`border-b ${ui.glassBorder} px-8 py-7 flex justify-between items-start`}>
          <div>
            <p className={`${ui.textSubtler} font-display text-xs font-bold uppercase tracking-wide mb-2`}>Lá thư từ biển khơi</p>
            <p className={`${ui.textPrimary} font-display text-lg font-semibold`}>{letter.from}</p>
          </div>
          <div className="flex items-center gap-4">
            <span className={`${ui.textSubtler} italic text-xs`}>{letter.time}</span>
            <button type="button" onClick={onClose} className={`${ui.textSubtle} bg-none border-none cursor-pointer p-1 flex hover:opacity-70 transition-opacity`}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div className="px-8 py-7">
          <p className={`${ui.textPrimary} font-display text-lg italic leading-relaxed tracking-[.5px]`}>{letter.body}</p>
        </div>

        <div className={`px-8 py-7 border-t ${ui.glassBorder}`}>
          {!sent ? (
            !replyOpen ? (
              <div className="mt-5 flex gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setActionError(null)
                    setReplyOpen(true)
                  }}
                  disabled={busy}
                  className="flex-1 bg-none border rounded-xl py-2.5 px-0 font-display tracking-wide cursor-pointer transition-all"
                  style={{
                    borderColor: dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)',
                    color: dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.7)',
                  }}
                >
                  Trả lời thư
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    if (busy) return
                    setBusy(true)
                    setBusyAction('pass')
                    setActionError(null)
                    try {
                      await onPass()
                      onClose()
                    } catch (error) {
                      if (error instanceof ApiRequestError) setActionError(error.message)
                      else setActionError('Không thể đẩy thư lúc này. Vui lòng thử lại.')
                    } finally {
                      setBusy(false)
                      setBusyAction(null)
                    }
                  }}
                  disabled={busy}
                  className="flex-1 bg-none border rounded-xl py-2.5 px-0 font-display font-semibold tracking-wide cursor-pointer transition-all"
                  style={{
                    borderColor: dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)',
                    color: dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.7)',
                  }}
                >
                  {busy && busyAction === 'pass' ? 'Đang đẩy...' : 'Đẩy thuyền trôi đi'}
                </button>
              </div>
            ) : (
              <div className="mt-5" style={{ animation: 'fadeUpCard 0.35s ease' }}>
                <textarea
                  ref={areaRef}
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  placeholder="Viết hồi âm của bạn..."
                  rows={3}
                  className="w-full rounded-xl p-4 font-display text-lg italic font-light leading-relaxed resize-none outline-none transition-colors"
                  style={{
                    backgroundColor: dark ? 'rgba(242,235,224,0.05)' : 'rgb(255,255,255)',
                    borderColor: dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)',
                    color: dark ? 'rgb(255,255,255)' : 'rgb(15,23,42)',
                    border: `1px solid ${dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)'}`,
                  }}
                />
                <div className="flex justify-between items-center mt-2.5">
                  <button type="button" onClick={() => setReplyOpen(false)} disabled={busy} className="text-xs cursor-pointer tracking-wide" style={{ background: 'none', border: 'none', color: dark ? 'rgba(242,235,224,0.55)' : 'rgba(20,26,33,0.56)' }}>
                    Huỷ
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      if (!reply.trim() || busy) return
                      setBusy(true)
                      setBusyAction('reply')
                      setActionError(null)
                      try {
                        await onReply(reply.trim())
                        setSent(true)
                        setTimeout(onClose, 1200)
                      } catch (error) {
                        if (error instanceof ApiRequestError) setActionError(error.message)
                        else setActionError('Không thể gửi hồi âm lúc này. Vui lòng thử lại.')
                      } finally {
                        setBusy(false)
                        setBusyAction(null)
                      }
                    }}
                    disabled={!reply.trim() || busy}
                    className="px-6 py-2 rounded-lg font-display text-sm italic transition-all"
                    style={{
                      background: reply.trim() ? 'linear-gradient(135deg,#5fd0be 0%,#4f9dcb 100%)' : 'none',
                      border: `1px solid ${reply.trim() ? 'rgba(111,190,214,0.68)' : dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)'}`,
                      color: reply.trim() ? '#ffffff' : dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.45)',
                    }}
                  >
                    {busy && busyAction === 'reply' ? 'Đang gửi...' : 'Thả về biển'}
                  </button>
                </div>
                {actionError && <p className="mt-2 text-xs text-rose-400">{actionError}</p>}
              </div>
            )
          ) : (
            <div className="mt-5 text-center py-3" style={{ animation: 'fadeUpCard 0.5s ease' }}>
              <p className={`${ui.textSubtle} font-display text-base italic font-light`}>Hồi âm đã trôi ra biển khơi...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function WriteOverlay({ onClose, dark }: { onClose: () => void; dark: boolean }) {
  const ui = getUi(dark)
  const [text, setText] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  return (
    <div
      onClick={(e: ReactMouseEvent<HTMLDivElement>) => e.target === e.currentTarget && onClose()}
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 ${ui.overlay} backdrop-blur-2xl`}
      style={{ animation: 'fadeIn 0.45s ease' }}
    >
      <div className={`${ui.glassLight} border w-full max-w-xl rounded-2xl backdrop-blur-2xl`} style={{ animation: 'letterOpen 0.65s cubic-bezier(0.22,1,0.36,1) both' }}>
        <div className={`border-b ${ui.glassBorder} px-8 py-7 flex justify-between items-start`}>
          <div>
            <p className={`${ui.textSubtler} text-lg font-light uppercase tracking-wider mb-2`}>Viết lá thư của bạn</p>
            <p className={`${ui.textSubtle} font-display text-base italic font-light`}>Lá thư sẽ trôi đến tay một người xa lạ</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.45)' }}
            className="p-1 flex hover:opacity-70 transition-opacity"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-8 py-7">
          {!sent ? (
            <>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Hôm nay bạn muốn chia sẻ điều gì..."
                rows={6}
                autoFocus
                className="w-full rounded-3xl p-4 font-display text-lg italic font-light leading-relaxed resize-none outline-none transition-colors"
                style={{
                  backgroundColor: dark ? 'rgba(242,235,224,0.05)' : 'rgb(255,255,255)',
                  borderColor: dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)',
                  color: dark ? 'rgb(255,255,255)' : 'rgb(15,23,42)',
                  border: `1px solid ${dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)'}`,
                }}
              />
              <div className="flex justify-end mt-3.5">
                <button
                  type="button"
                  onClick={async () => {
                    if (!text.trim() || busy) return
                    setBusy(true)
                    setSubmitError(null)
                    try {
                      await anonymousShareService.send({ content: text.trim() })
                      setSent(true)
                      setTimeout(onClose, 1800)
                    } catch (error) {
                      if (error instanceof ApiRequestError) setSubmitError(error.message)
                      else setSubmitError('Không thể gửi thư lúc này. Vui lòng thử lại.')
                    } finally {
                      setBusy(false)
                    }
                  }}
                  disabled={!text.trim() || busy}
                  className="px-8 py-2.5 rounded-3xl font-display text-base italic transition-all"
                  style={{
                    background: text.trim() ? 'linear-gradient(135deg,#5fd0be 0%,#4f9dcb 100%)' : 'none',
                    border: `1px solid ${text.trim() ? 'rgba(111,190,214,0.68)' : dark ? 'rgba(242,235,224,0.13)' : 'rgba(18,30,40,0.18)'}`,
                    color: text.trim() ? '#ffffff' : dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.45)',
                  }}
                >
                  {busy ? 'Đang thả...' : 'Thả ra biển'}
                </button>
              </div>
              {submitError && <p className="mt-2 text-xs text-rose-400">{submitError}</p>}
            </>
          ) : (
            <div className="text-center py-6" style={{ animation: 'fadeUpCard 0.6s ease' }}>
              <p className={`${ui.textSubtle} font-display text-lg italic font-light leading-relaxed`}>Lá thư đã trôi ra biển khơi...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function SentLetterDialog({
  item,
  dark,
  onClose,
  onReact,
  onReport,
}: {
  item: SentLetterItem
  dark: boolean
  onClose: () => void
  onReact: () => Promise<void>
  onReport: () => Promise<void>
}) {
  const ui = getUi(dark)
  const [busyReact, setBusyReact] = useState(false)
  const [busyReport, setBusyReport] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reacted, setReacted] = useState(Boolean(item.reply?.reaction_type))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/55 backdrop-blur-sm">
      <div
        className={`${ui.glassLight} border rounded-3xl shadow-2xl w-full max-w-3xl max-h-[86vh] overflow-hidden flex flex-col`}
        style={{ animation: 'letterOpen 0.35s cubic-bezier(0.22,1,0.36,1) both' }}
      >
        <div className={`border-b ${ui.glassBorder} px-5 py-4 flex items-center justify-between gap-3`}>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex items-center justify-center h-10 w-10 rounded-xl border"
            style={{
              borderColor: dark ? 'rgba(242,235,224,0.12)' : 'rgba(18,30,40,0.12)',
              color: dark ? 'rgba(242,235,224,0.92)' : 'rgba(20,26,33,0.92)',
            }}
            aria-label="Quay lại"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>

          <div className="min-w-0 flex-1 text-center px-2">
            <div className="flex items-center justify-center gap-2">
              <p className={`${ui.textSubtle} font-display text-lg font-semibold truncate`}>Chi tiết thư</p>
              {item.is_reported && (
                <span
                  className="text-xs font-semibold px-2 py-1 rounded-full"
                  style={{
                    backgroundColor: 'rgba(255, 120, 120, 0.15)',
                    color: 'rgba(255, 150, 150, 0.95)',
                  }}
                >
                  Đã báo cáo
                </span>
              )}
            </div>
          </div>

          <button
            type="button"
            onClick={async () => {
              if (busyReport) return
              setBusyReport(true)
              setError(null)
              try {
                await onReport()
              } catch (e) {
                if (e instanceof ApiRequestError) setError(e.message)
                else setError('Không thể report lúc này.')
              } finally {
                setBusyReport(false)
              }
            }}
            className="inline-flex items-center justify-center h-10 px-3 rounded-xl border text-xs font-semibold"
            style={{
              borderColor: dark ? 'rgba(255,120,120,0.35)' : 'rgba(190,40,40,0.35)',
              color: dark ? 'rgba(255,190,190,0.95)' : 'rgba(145,20,20,0.95)',
            }}
          >
            {busyReport ? 'Đang report...' : 'Report'}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <div className={`rounded-2xl border p-4 ${ui.glassLight}`}>
            <p className={`${ui.textSubtler} text-xs uppercase tracking-wider mb-2`}>Thư bạn gửi</p>
            <p className={`${ui.textSubtle} font-display text-base leading-relaxed whitespace-pre-wrap`}>{item.content}</p>
            <p className={`${ui.textSubtler} text-[11px] mt-2`}>{formatRelativeTime(item.sent_at)}</p>
          </div>

          <div className={`rounded-2xl border p-4 ${ui.glassLight}`}>
            <p className={`${ui.textSubtler} text-xs uppercase tracking-wider mb-2`}>Thư bạn nhận được</p>
            {item.reply ? (
              <>
                <p className={`${ui.textSubtler} text-xs mb-2`}>
                  {item.reply.anonymous_name ? `Ẩn danh: ${item.reply.anonymous_name}` : 'Người phản hồi ẩn danh'}
                  {item.reply.has_reaction ? ` · Đã được thả ${item.reply.reaction_type ?? 'cảm xúc'}` : ' · Chưa được phản hồi cảm xúc'}
                </p>
                <p className={`${ui.textSubtle} font-display text-base leading-relaxed whitespace-pre-wrap`}>{item.reply.content}</p>
                <p className={`${ui.textSubtler} text-[11px] mt-2`}>{formatRelativeTime(item.reply.received_at)}</p>
                <div className="mt-3 flex items-center justify-end">
                  <button
                    type="button"
                    disabled={reacted || busyReact}
                    onClick={async () => {
                      if (!item.reply || reacted || busyReact) return
                      setBusyReact(true)
                      setError(null)
                      try {
                        await onReact()
                        setReacted(true)
                      } catch (e) {
                        if (e instanceof ApiRequestError) setError(e.message)
                        else setError('Không thể thả tim lúc này.')
                      } finally {
                        setBusyReact(false)
                      }
                    }}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border"
                    style={{
                      borderColor: reacted ? 'rgba(245,128,160,0.7)' : dark ? 'rgba(242,235,224,0.2)' : 'rgba(18,30,40,0.18)',
                      color: reacted ? '#f06292' : dark ? 'rgba(242,235,224,0.85)' : 'rgba(20,26,33,0.8)',
                    }}
                  >
                    <span aria-hidden="true">❤</span>
                    <span className="text-sm">{reacted ? 'Đã thả tim' : busyReact ? 'Đang thả...' : 'Thả tim'}</span>
                  </button>
                </div>
              </>
            ) : (
              <p className={`${ui.textSubtler} text-sm`}>Chưa có hồi âm cho thư này.</p>
            )}
          </div>

          {error && <p className="text-sm text-rose-400">{error}</p>}
        </div>
      </div>
    </div>
  )
}

export default function BeachMessage() {
  const [dark, setDark] = useState(() => readAppSettings().mode === 'dark')
  const ui = getUi(dark)

  const [tab, setTab] = useState<TabId>('beach')
  const [pendingLetter, setPendingLetter] = useState<Letter | null>(null)
  const [ripple, setRipple] = useState(false)
  const [openLetter, setOpenLetter] = useState<Letter | null>(null)
  const [showWrite, setShowWrite] = useState(false)
  const [loadingInbox, setLoadingInbox] = useState(false)
  const [loadingSent, setLoadingSent] = useState(false)
  const [sentLetters, setSentLetters] = useState<SentLetterItem[]>([])
  const [replyLetters, setReplyLetters] = useState<ReplyArchiveItem[]>([])
  const [selectedSentLetter, setSelectedSentLetter] = useState<SentLetterItem | null>(null)
  const [refreshSeed, setRefreshSeed] = useState(0)

  useEffect(() => {
    const syncDarkMode = (settings: AppSettings) => setDark(settings.mode === 'dark')
    const onSettings = (event: Event) => {
      const customEvent = event as CustomEvent<AppSettings>
      if (customEvent.detail) syncDarkMode(customEvent.detail)
    }
    const onStorage = (event: StorageEvent) => {
      if (event.key !== APP_SETTINGS_STORAGE_KEY) return
      syncDarkMode(readAppSettings())
    }
    window.addEventListener(APP_SETTINGS_UPDATED_EVENT, onSettings as EventListener)
    window.addEventListener('storage', onStorage)
    return () => {
      window.removeEventListener(APP_SETTINGS_UPDATED_EVENT, onSettings as EventListener)
      window.removeEventListener('storage', onStorage)
    }
  }, [])

  useEffect(() => {
    let active = true
    const loadData = async () => {
      setLoadingInbox(true)
      try {
        const inboxData = await anonymousShareService.getInbox()
        if (active) setPendingLetter((current) => current ?? pickRandomLetter(inboxData.letters))
      } catch {
        if (active) setPendingLetter(null)
      } finally {
        if (active) setLoadingInbox(false)
      }

      setLoadingSent(true)
      try {
        const sentData = await anonymousShareService.getSentLetters()
        if (active) setSentLetters(sentData.letters)
        if (active) setReplyLetters(sentData.reply_letters ?? [])
      } catch {
        if (active) setSentLetters([])
        if (active) setReplyLetters([])
      } finally {
        if (active) setLoadingSent(false)
      }
    }

    void loadData()
    return () => {
      active = false
    }
  }, [refreshSeed])

  const handleBottle = () => {
    if (!pendingLetter) return
    setRipple(true)
    setTimeout(() => {
      setRipple(false)
      setOpenLetter(pendingLetter)
      setPendingLetter(null)
    }, 700)
  }

  const refreshData = () => setRefreshSeed((value) => value + 1)
  const hasBottle = Boolean(pendingLetter)

  return (
    <div className="relative min-h-screen overflow-x-hidden overflow-y-auto">
      <style>{ANIMATIONS_CSS}</style>
      <FontLink />
      <CinematicBg dark={dark} />

      <nav className={`relative z-10 flex items-center justify-center px-8 py-4.5 ${ui.glassBorder} backdrop-blur-md`}>
        <div className="flex gap-24">
          {[
            { id: 'beach', label: 'Bến thư' },
            { id: 'community', label: 'Kho thư' },
          ].map((t) => (
            <button
              type="button"
              key={t.id}
              onClick={() => setTab(t.id as TabId)}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: `2px solid ${tab === t.id ? (dark ? 'rgb(255,255,255)' : 'rgb(15,23,42)') : dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.45)'}`,
                color: tab === t.id ? (dark ? 'rgb(255,255,255)' : 'rgb(15,23,42)') : dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.45)',
                marginBottom: '-1px',
              }}
              className="py-1.5 px-4 text-lg font-display font-semibold tracking-wide cursor-pointer transition-all"
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>

      {tab === 'beach' && (
        <div className="relative z-10 flex flex-col items-center min-h-[calc(100vh-64px)] pt-20 pb-24">
          <div className="text-center mb-16" style={{ animation: 'fadeUp 1s ease 0.1s both' }}>
            <h1
              className={`${ui.textPrimary} font-display text-5xl italic font-normal leading-snug drop-shadow-xl`}
              style={{ textShadow: dark ? '0 2px 18px rgba(0,0,0,0.45)' : '0 2px 12px rgba(255,255,255,0.38)' }}
            >
              {loadingInbox ? 'Đang đón thư từ biển...' : hasBottle ? 'Có một lá thư đang chờ bạn' : 'Chưa có thư mới'}
            </h1>
          </div>

          {loadingInbox ? (
            <div className="text-center" style={{ animation: 'fadeUp 1s ease 0.3s both' }}>
              <p className={`${ui.textPrimary} font-display text-2xl italic font-normal leading-relaxed`}>Đang lắng nghe biển khơi...</p>
            </div>
          ) : hasBottle ? (
            <div className="flex flex-col items-center gap-6" style={{ animation: 'fadeUp 1s ease 0.3s both' }}>
              <FloatingBottle dark={dark} onClick={handleBottle} isClicked={ripple} />
              <p className="text-white font-display font-semibold tracking-widest uppercase mt-2 animate-pulse">Chạm để xem</p>
            </div>
          ) : (
            <div className="text-center" style={{ animation: 'fadeUp 1s ease 0.3s both' }}>
              <p className={`${ui.textPrimary} font-display text-2xl italic font-normal leading-relaxed`} style={{ opacity: dark ? 0.78 : 0.88 }}>
                Biển đang lặng, chưa có thư trôi đến.
              </p>
            </div>
          )}

          <div className="flex flex-col items-center gap-4 mt-16" style={{ animation: 'fadeUp 1s ease 0.5s both' }}>
            <button
              type="button"
              onClick={() => setShowWrite(true)}
              className={`
                border rounded-full px-10 py-3 font-display text-2xl font-semibold cursor-pointer transition-all
                ${
                  dark
                    ? 'bg-white/10 border-white/45 text-white/95 shadow-[0_10px_24px_rgba(0,0,0,0.28)]'
                    : 'bg-white/80 border-slate-900/30 text-slate-900/90 shadow-[0_8px_20px_rgba(20,40,56,0.18)]'
                }
                hover:bg-cyan-400/25 hover:border-cyan-400/85 hover:text-white hover:shadow-[0_12px_28px_rgba(66,153,180,0.42)] hover:-translate-y-px
              `}
            >
              Viết lá thư của bạn
            </button>
          </div>
        </div>
      )}

      {tab === 'community' && (
        <div className="relative z-10 max-w-2xl mx-auto px-6 py-16 pb-24" style={{ animation: 'fadeUp 0.8s ease both' }}>
          <div className="mb-10">
            <h2
              className={`${ui.textPrimary} font-display text-4xl italic font-normal`}
              style={{ textShadow: dark ? '0 2px 16px rgba(0,0,0,0.36)' : '0 2px 10px rgba(255,255,255,0.35)' }}
            >
              Kho thư cá nhân
            </h2>
          </div>

          <div className={`${ui.glassLight} border rounded-2xl p-4 mb-8`}>
            <div className="flex items-center justify-between mb-3">
              <h3 className={`${ui.textSubtle} font-display text-xl font-semibold`}>Thư bạn đã gửi</h3>
              {loadingSent && <span className={`${ui.textSubtler} text-xs uppercase tracking-wider`}>Đang tải...</span>}
            </div>

            {sentLetters.length > 0 ? (
              <div className="grid grid-cols-1 gap-3">
                {sentLetters.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setSelectedSentLetter(item)}
                    className="text-left rounded-xl border px-4 py-3 transition-all"
                    style={{ borderColor: dark ? 'rgba(242,235,224,0.2)' : 'rgba(18,30,40,0.18)' }}
                  >
                    <div className="flex items-start justify-between gap-3 mb-1">
                      <p className={`${ui.textSubtle} font-display text-base font-semibold`}>Thư của bạn</p>
                      <p className={`${ui.textSubtler} text-xs`}>{formatRelativeTime(item.sent_at)}</p>
                    </div>
                    <p className={`${ui.textSubtler} text-sm line-clamp-1 mb-1`}>{item.content}</p>
                    <p className={`${ui.textSubtler} text-xs uppercase tracking-wider`}>
                      {item.reply
                        ? `${item.reply.anonymous_name ? `Ẩn danh: ${item.reply.anonymous_name}` : 'Có hồi âm'}${
                            item.reply.has_reaction ? ` · Đã được thả ${item.reply.reaction_type ?? 'cảm xúc'}` : ' · Chưa được thả cảm xúc'
                          }`
                        : 'Đang chờ hồi âm'}
                    </p>
                  </button>
                ))}
              </div>
            ) : (
              <p className={`${ui.textSubtler} text-sm`}>Bạn chưa gửi thư nào.</p>
            )}
          </div>

          <div className={`${ui.glassLight} border rounded-2xl p-4`}>
            <div className="flex items-center justify-between mb-3">
              <h3 className={`${ui.textSubtle} font-display text-xl font-semibold`}>Thư bạn đã phản hồi</h3>
              {loadingSent && <span className={`${ui.textSubtler} text-xs uppercase tracking-wider`}>Đang tải...</span>}
            </div>

            {replyLetters.length > 0 ? (
              <div className="grid grid-cols-1 gap-3">
                {replyLetters.map((item) => (
                  <div
                    key={item.reply_id}
                    className="text-left rounded-xl border px-4 py-3"
                    style={{ borderColor: dark ? 'rgba(242,235,224,0.2)' : 'rgba(18,30,40,0.18)' }}
                  >
                    <div className="flex items-start justify-between gap-3 mb-1">
                      <p className={`${ui.textSubtle} font-display text-base font-semibold`}>Phản hồi của bạn</p>
                      <p className={`${ui.textSubtler} text-xs`}>{formatRelativeTime(item.sent_at)}</p>
                    </div>
                    <p className={`${ui.textSubtler} text-xs mb-2`}>
                      {item.anonymous_name ? `Ẩn danh: ${item.anonymous_name}` : 'Ẩn danh'}
                      {item.has_reaction ? ` · Đã được thả ${item.reaction_type ?? 'cảm xúc'}` : ' · Chưa được thả cảm xúc'}
                    </p>
                    <p className={`${ui.textSubtler} text-sm line-clamp-2 mb-2`}>{item.content}</p>
                    {item.original_content ? (
                      <p className={`${ui.textSubtler} text-xs italic line-clamp-2`}>
                        Trả lời cho: {item.original_content}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <p className={`${ui.textSubtler} text-sm`}>Bạn chưa phản hồi thư nào.</p>
            )}
          </div>
        </div>
      )}

      {selectedSentLetter && (
        <SentLetterDialog
          item={selectedSentLetter}
          dark={dark}
          onClose={() => setSelectedSentLetter(null)}
          onReact={async () => {
            if (!selectedSentLetter.reply) return
            await anonymousShareService.reactToReply(selectedSentLetter.reply.reply_id, 'heart')
            refreshData()
          }}
          onReport={async () => {
            try {
              await anonymousShareService.reportLetter(selectedSentLetter.id, 'reported from sent-letter dialog')
              toast.success('Báo cáo thành công. Cảm ơn bạn đã giúp chúng tôi cải thiện cộng đồng.')
              refreshData()
            } catch (e) {
              toast.error('Không thể gửi báo cáo. Vui lòng thử lại sau.')
            }
          }}
        />
      )}

      {openLetter && (
        <LetterOverlay
          letter={openLetter}
          onClose={() => setOpenLetter(null)}
          dark={dark}
          onReply={async (content) => {
            await anonymousShareService.reply(openLetter.id, content)
            refreshData()
          }}
          onPass={async () => {
            await anonymousShareService.passItOn(openLetter.id)
            refreshData()
          }}
        />
      )}
      {showWrite && <WriteOverlay onClose={() => setShowWrite(false)} dark={dark} />}
    </div>
  )
}
