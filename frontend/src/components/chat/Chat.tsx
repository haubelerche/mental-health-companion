import { useEffect, useMemo, useRef, useState } from 'react'
import type { ComponentProps } from 'react'
import {
    Eye,
    History,
    Leaf,
    MapPin,
    MoreVertical,
    Music,
    Paperclip,
    Play,
    Sprout,
    UserRound,
    Wind,
} from 'lucide-react'
import { TypingIndicator } from './TypingIndicator'
import { DateDivider } from './DateDivider'
import { useNavigate, useLocation } from 'react-router-dom'
import { toast } from 'react-toastify'
import { resolveMediaUrl } from '../../api/httpClient'
import { ApiRequestError } from '../../api/types'
import { useAuth } from '../../hooks/useAuth'
import { ROUTE_PATHS } from '../../routes/paths'
import { chatService } from '../../services/chatService'
import { policyService } from '../../services/policyService'
import { Switch } from '../ui/switch'
import { HotlineBar } from '../crisis/HotlineBar'
import { ChatHistoryModal } from './ChatHistoryModal'
import { useThemeContext } from '../../contexts/ThemeContext'
import MemoryCardsTab from './MemoryCardsTab'
import PersonaSelector from './PersonaSelector'
import ChatEntryCheckIn from './ChatEntryCheckIn'
import VoiceStatusBadge, { TTS_TERMINAL_STATUSES } from './VoiceStatusBadge'
import type { TtsStatus } from './VoiceStatusBadge'

// ─── API response types ────────────────────────────────────────────────────────

type HotlineCard = { label: string; phone: string }
type MicroAction = { type: string; label: string }
type GroundingAction = { id: string }
type ReferralOption = { type: string }
type AssistantStrategy = {
    keep_engaged: boolean
    encourage_external_help: boolean
    avoid_hard_stop: boolean
}
type TheDinhKem = {
    type: string
    id: string
    title: string
    description?: string | null
    duration_sec?: number
    action?: string
    route?: string
    thumbnail?: string | null
}
type ProactiveVoiceIntervention = {
    type: string
    trigger_reason?: string
    cooldown?: { active: boolean; seconds_remaining: number }
    voice?: { status?: string; tts_job_id?: string | null; audio_url?: string | null }
    voice_script?: string
    copy_ngan?: string
    crisis_footer?: { show_once: boolean; text: string; hotline_cta: { label: string; action: string } }
    next_actions?: Array<{ id: string; label: string; action?: string }>
}

type ChatApiData = {
    session_id: string
    conversation_mode?: 'normal' | 'supportive' | 'de_escalation'
    distress_score?: number
    safety_tier?: 'normal' | 'elevated' | 'voice_recommended' | 'critical'
    voice_session_offered?: boolean
    suggest_voice?: boolean
    voice_hint?: string | null
    emergency_actions?: Record<string, boolean> | null
    reply?: string | null
    assistant_text?: string | null
    tone_cam_xuc?: string | null
    goi_y_nhanh?: QuickReply[]
    the_dinh_kem?: TheDinhKem[]
    sos_triggered?: boolean
    risk_level?: number
    agent_display_name?: string
    assistant_strategy?: AssistantStrategy
    micro_actions?: MicroAction[]
    hotline_cards?: HotlineCard[]
    grounding_actions?: GroundingAction[]
    referral_options?: ReferralOption[]
    followup_priority?: boolean
    routing_history?: string[]
    intervention?: ProactiveVoiceIntervention | null
}

type QuickReply = string | { label?: string; message?: string; reason?: string; type?: string }

type UiMessage = {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp?: number
    apiData?: ChatApiData
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function SafetyBadge({ tier }: { tier?: string }) {
    if (!tier || tier === 'normal') return null
    const cfg: Record<string, { label: string; cls: string }> = {
        elevated: { label: 'Dấu hiệu', cls: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
        voice_recommended: { label: 'Gợi thoại', cls: 'bg-orange-100 text-orange-800 border-orange-300' },
        critical: { label: 'Khủng hoảng', cls: 'bg-red-100 text-red-800 border-red-300' },
    }
    const c = cfg[tier]
    if (!c) return null
    return (
        <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${c.cls}`}>
            {c.label}
        </span>
    )
}

function RoutingBadge({ history }: { history?: string[] }) {
    if (!history?.length) return null
    const nodeColors: Record<string, string> = {
        supervisor: 'bg-violet-100 text-violet-700',
        analyst: 'bg-blue-100 text-blue-700',
        friend: 'bg-green-100 text-green-700',
        sos_handler: 'bg-red-100 text-red-700',
    }
    return (
        <div className="mt-1.5 flex flex-wrap items-center gap-1">
            <span className="text-[10px] font-medium text-theme-text-secondary/60">Luồng:</span>
            {history.map((node, i) => (
                <span key={i} className="flex items-center gap-0.5">
                    <span className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-medium capitalize ${nodeColors[node] ?? 'bg-theme-bg-secondary text-theme-text-secondary'}`}>
                        {node}
                    </span>
                    {i < history.length - 1 && <span className="text-[10px] text-theme-text-secondary/30">/</span>}
                </span>
            ))}
        </div>
    )
}

function DistressBar({ score }: { score?: number }) {
    if (score === undefined || score === null) return null
    const pct = Math.round(score * 100)
    const color = pct < 35 ? 'bg-emerald-400' : pct < 55 ? 'bg-yellow-400' : pct < 80 ? 'bg-orange-400' : 'bg-red-500'
    return (
        <div className="mt-1 flex items-center gap-2">
            <span className="text-[10px] text-theme-text-secondary/60">Distress</span>
            <div className="h-1.5 w-20 overflow-hidden rounded-full bg-theme-border/30">
                <div className={`h-full transition-all ${color}`} style={{ width: `${pct}%` }} />
            </div>
            <span className="font-mono text-[10px] text-theme-text-secondary/60">{score.toFixed(2)}</span>
        </div>
    )
}

function quickReplyText(reply: QuickReply): string {
    if (typeof reply === 'string') return reply.trim()
    return String(reply.message || reply.label || reply.reason || reply.type || '').trim()
}

function QuickReplies({ replies, onSelect }: { replies?: QuickReply[]; onSelect: (text: string) => void }) {
    const normalizedReplies = (replies ?? []).map(quickReplyText).filter(Boolean)
    if (!normalizedReplies.length) return null
    return (
        <div className="mt-2 flex flex-wrap gap-2">
            {normalizedReplies.map((q, i) => (
                <button
                    key={i}
                    type="button"
                    onClick={() => onSelect(q)}
                    className="rounded-full border border-theme-border/40 bg-theme-surface/60 px-3 py-1.5 text-xs text-theme-text-primary transition hover:bg-theme-accent/20 active:scale-95"
                >
                    {q}
                </button>
            ))}
        </div>
    )
}

const ATTACHMENT_ICONS: Record<string, typeof Wind> = {
    breathing_exercise: Wind,
    grounding_exercise: Sprout,
    body_scan: Leaf,
    meditation: Leaf,
    music: Music,
    resource: Play,
    clinic_map: MapPin,
}

function AttachmentCard({ item, onOpen }: { item: TheDinhKem; onOpen: (item: TheDinhKem) => void }) {
    const IconCmp = ATTACHMENT_ICONS[item.type] ?? Paperclip
    const duration = item.duration_sec ? `${Math.max(1, Math.round(item.duration_sec / 60))} phút` : item.type.replace(/_/g, ' ')
    return (
        <button
            type="button"
            onClick={() => onOpen(item)}
            className="mt-2 grid max-w-sm grid-cols-[40px_1fr_auto] items-center gap-3 rounded-2xl border border-theme-border/30 bg-theme-surface/60 px-3 py-2.5 text-left transition hover:bg-theme-accent/20"
        >
            <span className="flex h-10 w-10 items-center justify-center text-theme-accent">
                <IconCmp className="h-5 w-5" aria-hidden />
            </span>
            <div>
                <p className="text-xs font-semibold text-theme-text-primary">{item.title}</p>
                <p className="mt-0.5 line-clamp-2 text-[10px] leading-relaxed text-theme-text-secondary">
                    {item.description || duration}
                </p>
            </div>
            <span className="rounded-full bg-theme-accent/10 px-2 py-1 text-[10px] font-medium text-theme-accent">
                Mở
            </span>
        </button>
    )
}

function CrisisPanel({ data }: { data: ChatApiData }) {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'
    if (!data.sos_triggered) return null
    return (
        <div className={`mt-3 space-y-2.5 rounded-2xl border-2 ${isDark ? 'border-red-500/30 bg-red-500/10' : 'border-red-300 bg-red-50/90'} p-4`}>
            <div className="flex items-center gap-2">
                <span className={`text-xs font-black uppercase tracking-tighter ${isDark ? 'text-red-400' : 'text-red-600'}`} aria-hidden>
                    SOS
                </span>
                <div>
                    <p className={`text-xs font-semibold ${isDark ? 'text-red-400' : 'text-red-700'}`}>CHẾ ĐỘ HỖ TRỢ KHỦNG HOẢNG</p>
                    <p className={`text-[10px] ${isDark ? 'text-red-400/70' : 'text-red-500/70'}`}>
                        risk_level: {data.risk_level ?? '—'} · tier: {data.safety_tier}
                    </p>
                </div>
            </div>
            {data.assistant_strategy && (
                <div className="flex flex-wrap gap-1.5">
                    {data.assistant_strategy.keep_engaged && (
                        <span className={`rounded-full border ${isDark ? 'border-green-500/30 bg-green-500/10 text-green-400' : 'border-green-300 bg-green-50 text-green-700'} px-2 py-0.5 text-[10px]`}>
                            Đã chọn · Giữ kết nối
                        </span>
                    )}
                    {data.assistant_strategy.encourage_external_help && (
                        <span className={`rounded-full border ${isDark ? 'border-blue-500/30 bg-blue-500/10 text-blue-400' : 'border-blue-300 bg-blue-50 text-blue-700'} px-2 py-0.5 text-[10px]`}>
                            Đã chọn · Gợi hỗ trợ ngoài
                        </span>
                    )}
                </div>
            )}
            {data.micro_actions?.length ? (
                <div className="space-y-1.5">
                    {data.micro_actions.map((a, i) => (
                        <div key={i} className={`flex items-start gap-2 rounded-xl border ${isDark ? 'border-red-500/20 bg-theme-surface/40' : 'border-red-200 bg-white/60'} px-3 py-2`}>
                            <span className="flex h-8 w-8 shrink-0 items-center justify-center text-theme-accent">
                                {a.type === 'breathing' ? <Wind className="h-4 w-4" aria-hidden /> : <Eye className="h-4 w-4" aria-hidden />}
                            </span>
                            <span className={`text-xs ${isDark ? 'text-red-400' : 'text-red-700'}`}>{a.label}</span>
                        </div>
                    ))}
                </div>
            ) : null}
            {data.hotline_cards?.length ? (
                <div className="space-y-1.5">
                    {data.hotline_cards.map((h, i) => (
                        <a
                            key={i}
                            href={`tel:${h.phone.replace(/\s/g, '')}`}
                            className={`flex items-center justify-between rounded-xl border ${isDark ? 'border-red-500/30 bg-red-500/5 hover:bg-red-500/10' : 'border-red-200 bg-white/70 hover:bg-red-50'} px-3 py-2 transition`}
                        >
                            <span className={`text-xs ${isDark ? 'text-red-400' : 'text-red-700'}`}>{h.label}</span>
                            <span className={`font-bold ${isDark ? 'text-red-400' : 'text-red-600'}`}>{h.phone}</span>
                        </a>
                    ))}
                </div>
            ) : null}
        </div>
    )
}

// ─── Main component ────────────────────────────────────────────────────────────

export default function Chat() {
    type FormSubmitHandler = NonNullable<ComponentProps<'form'>['onSubmit']>
    const FALLBACK_GUEST_CHAT_DURATION_SECONDS = 120

    const [sessionId, setSessionId] = useState<string | null>(null)
    const [messages, setMessages] = useState<UiMessage[]>([])
    const [input, setInput] = useState('')
    const [sending, setSending] = useState(false)
    const [voiceConsent, setVoiceConsent] = useState(false)
    const [voiceStatus, setVoiceStatus] = useState('')
    const [lastFailedText, setLastFailedText] = useState<string | null>(null)
    const [showDebug, setShowDebug] = useState(false)
    const [showOptions, setShowOptions] = useState(false)
    const [showHistory, setShowHistory] = useState(false)
    const [historyLoading, setHistoryLoading] = useState(false)
    const [sessions, setSessions] = useState<Array<{ session_id: string; preview: string | null; last_message_at: string }>>([])
    const [guestSecondsLeft, setGuestSecondsLeft] = useState<number>(FALLBACK_GUEST_CHAT_DURATION_SECONDS)
    const [guestSessionLoading, setGuestSessionLoading] = useState(false)
    const [activeTab, setActiveTab] = useState<'chat' | 'memory'>('chat')
    const [checkInDone, setCheckInDone] = useState(false)
    const pollRef = useRef<number | null>(null)
    const bottomRef = useRef<HTMLDivElement | null>(null)
    const optionsRef = useRef<HTMLDivElement | null>(null)
    const guestDeadlineRef = useRef<number | null>(null)
    const guestExpiredNotifiedRef = useRef(false)
    const [sosActive, setSosActive] = useState(false)
    const { effectiveTheme } = useThemeContext()
    const { user } = useAuth()
    const navigate = useNavigate()
    const location = useLocation()
    const isGuestMode = !user
    const isDark = effectiveTheme === 'dark'

    useEffect(() => {
        if (!user) {
            setVoiceConsent(false)
            return
        }
        policyService
            .getVoiceConsent()
            .then((res) => setVoiceConsent(Boolean(res.voice_consent)))
            .catch(() => undefined)
    }, [user])

    useEffect(() => {
        const state = location.state as { crisisMode?: boolean } | null
        if (state?.crisisMode) setSosActive(true)
    }, [location.state])

    // Show Serene's greeting on fresh session (no messages loaded yet).
    useEffect(() => {
        if (!user || isGuestMode) return
        let cancelled = false
        chatService.getGreeting().then((res) => {
            if (cancelled) return
            setMessages((prev) => {
                if (prev.length > 0) return prev
                return [{
                    id: 'greeting-0',
                    role: 'assistant' as const,
                    content: res.text,
                    timestamp: Date.now(),
                }]
            })
        }).catch(() => undefined)
        return () => { cancelled = true }
    }, [user, isGuestMode])

    useEffect(() => {
        let cancelled = false
        if (!isGuestMode) {
            setGuestSecondsLeft(FALLBACK_GUEST_CHAT_DURATION_SECONDS)
            guestDeadlineRef.current = null
            guestExpiredNotifiedRef.current = false
            setGuestSessionLoading(false)
            return
        }
        if (sessionId && !sessionId.startsWith('gst_')) {
            setSessionId(null)
            guestDeadlineRef.current = null
            setGuestSecondsLeft(FALLBACK_GUEST_CHAT_DURATION_SECONDS)
            return
        }
        if (!sessionId) {
            setGuestSessionLoading(true)
            void chatService
                .startGuestSession()
                .then((data) => {
                    if (cancelled) return
                    const duration = Number(data.max_duration_sec) > 0 ? Number(data.max_duration_sec) : FALLBACK_GUEST_CHAT_DURATION_SECONDS
                    setSessionId(data.guest_session_id)
                    setGuestSecondsLeft(duration)
                    guestDeadlineRef.current = Date.now() + duration * 1000
                    guestExpiredNotifiedRef.current = false
                })
                .catch(() => {
                    if (cancelled) return
                    setGuestSecondsLeft(FALLBACK_GUEST_CHAT_DURATION_SECONDS)
                    guestDeadlineRef.current = Date.now() + FALLBACK_GUEST_CHAT_DURATION_SECONDS * 1000
                    guestExpiredNotifiedRef.current = false
                })
                .finally(() => {
                    if (!cancelled) setGuestSessionLoading(false)
                })
            return () => {
                cancelled = true
            }
        }

        const tick = () => {
            const deadline = guestDeadlineRef.current ?? Date.now()
            const next = Math.max(0, Math.ceil((deadline - Date.now()) / 1000))
            setGuestSecondsLeft(next)
            if (next <= 0 && !guestExpiredNotifiedRef.current) {
                guestExpiredNotifiedRef.current = true
                toast.info('Bạn đã dùng hết 2 phút chat thử. Đăng ký để tiếp tục nhé.')
                navigate(ROUTE_PATHS.register, { replace: true })
            }
        }
        tick()
        const timer = window.setInterval(tick, 1000)
        return () => window.clearInterval(timer)
    }, [FALLBACK_GUEST_CHAT_DURATION_SECONDS, isGuestMode, navigate, sessionId])

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    useEffect(() => {
        return () => {
            if (pollRef.current) window.clearTimeout(pollRef.current)
        }
    }, [])

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (optionsRef.current && !optionsRef.current.contains(event.target as Node)) {
                setShowOptions(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const canSend = useMemo(() => {
        if (sending) return false
        if (input.trim().length <= 0) return false
        if (isGuestMode && (guestSessionLoading || guestSecondsLeft <= 0)) return false
        return true
    }, [sending, input, isGuestMode, guestSecondsLeft, guestSessionLoading])

    const guestCountdownLabel = useMemo(() => {
        const mins = Math.floor(guestSecondsLeft / 60)
        const secs = guestSecondsLeft % 60
        return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
    }, [guestSecondsLeft])

    const playAudioUrl = (audioUrl: string) => {
        const audio = new Audio(resolveMediaUrl(audioUrl))
        void audio.play().catch(() => {
            toast.info('Trình duyệt chặn tự phát audio, hãy bấm play thủ công.')
        })
    }

    const pollVoiceJob = async (ttsJobId: string, fallbackScript?: string, attempts = 0) => {
        if (attempts > 10) {
            setVoiceStatus('Voice phản hồi chậm, đang dùng bản text trước.')
            if (fallbackScript) {
                setMessages((prev) => [...prev, { id: `vs_to_${Date.now()}`, role: 'assistant', content: fallbackScript }])
            }
            return
        }
        try {
            const job = await chatService.getVoiceJob(ttsJobId)
            setVoiceStatus(job.status)
            // Dừng poll khi gặp bất kỳ terminal status nào
            if (TTS_TERMINAL_STATUSES.has(job.status as TtsStatus)) {
                if (job.status === 'ready' && job.audio_url) {
                    playAudioUrl(job.audio_url)
                    setVoiceStatus('')
                } else if (job.status === 'failed') {
                    setVoiceStatus(job.error_message ? `failed:${job.error_message}` : 'failed')
                    if (fallbackScript) {
                        setMessages((prev) => [
                            ...prev,
                            { id: `vs_fail_${Date.now()}`, role: 'assistant', content: fallbackScript },
                        ])
                    }
                } else {
                    // cache_hit, skipped_duplicate, provider_disabled, cancelled, expired
                    if (fallbackScript && (job.status === 'provider_disabled' || job.status === 'expired' || job.status === 'cancelled')) {
                        setMessages((prev) => [
                            ...prev,
                            { id: `vs_term_${Date.now()}`, role: 'assistant', content: fallbackScript },
                        ])
                    }
                }
                return
            }
        } catch {
            if (fallbackScript) {
                setMessages((prev) => [...prev, { id: `vs_err_${Date.now()}`, role: 'assistant', content: fallbackScript }])
            }
            return
        }
        const delay = attempts < 3 ? 400 : attempts < 6 ? 800 : 1500
        pollRef.current = window.setTimeout(() => {
            void pollVoiceJob(ttsJobId, fallbackScript, attempts + 1)
        }, delay)
    }

    const applyIntervention = (data: ChatApiData) => {
        const intervention = data.intervention
        if (intervention?.type !== 'proactive_voice') return
        if (intervention.copy_ngan) {
            setMessages((prev) => [...prev, { id: `i_${Date.now()}`, role: 'assistant', content: intervention.copy_ngan ?? '' }])
        }
        const ttsJobId = intervention.voice?.tts_job_id
        const audioUrl = intervention.voice?.audio_url
        if (audioUrl) {
            playAudioUrl(audioUrl)
        } else if (ttsJobId) {
            setVoiceStatus('Đang tạo voice...')
            void pollVoiceJob(ttsJobId, intervention.voice_script)
        } else if (intervention.voice_script) {
            setMessages((prev) => [...prev, { id: `vs_${Date.now()}`, role: 'assistant', content: intervention.voice_script ?? '' }])
        }
    }

    const consumeChatSse = async (response: Response, pendingId: string) => {
        if (!response.ok) {
            throw new Error('Streaming chat thất bại')
        }
        const reader = response.body?.getReader()
        if (!reader) {
            throw new Error('Không đọc được stream phản hồi')
        }
        const decoder = new TextDecoder('utf-8')
        let buffer = ''
        let currentEvent = ''
        let streamedText = ''
        let finalData: ChatApiData | null = null

        while (true) {
            const { done, value } = await reader.read()
            if (done) break
            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() || ''

            for (const line of lines) {
                if (line.startsWith('event:')) {
                    currentEvent = line.slice(6).trim()
                    continue
                }
                if (!line.startsWith('data:')) continue
                const raw = line.slice(5).trim()
                if (!raw) continue
                try {
                    const payload = JSON.parse(raw) as Record<string, unknown>
                    if (currentEvent === 'delta') {
                        streamedText += String(payload.text ?? '')
                        setMessages((prev) =>
                            prev.map((m) => (m.id === pendingId ? { ...m, content: streamedText || '...' } : m)),
                        )
                    } else if (currentEvent === 'heartbeat') {
                        const stage = String(payload.stage ?? 'pre_llm')
                        const elapsedMs = Number(payload.elapsed_ms ?? 0)
                        setVoiceStatus(`Đang xử lý (${stage}) · ${elapsedMs}ms`)
                    } else if (currentEvent === 'status') {
                        if (payload.stage === 'ready' && typeof payload.latency_ms === 'number') {
                            setVoiceStatus(`Latency backend: ${payload.latency_ms}ms`)
                        }
                    } else if (currentEvent === 'final') {
                        finalData = payload as unknown as ChatApiData
                    }
                } catch {
                    // ignore malformed line
                }
            }
        }

        if (!finalData) {
            throw new Error('Không nhận được dữ liệu cuối từ stream')
        }
        const sid = typeof finalData.session_id === 'string' ? finalData.session_id : null
        if (sid) setSessionId(sid)
        const assistantText =
            typeof finalData.reply === 'string' && finalData.reply
                ? finalData.reply
                : typeof finalData.assistant_text === 'string' && finalData.assistant_text
                    ? finalData.assistant_text
                    : streamedText || 'Mình vẫn đang ở đây cùng bạn.'
        setMessages((prev) =>
            prev.map((m) =>
                m.id === pendingId
                    ? { id: `a_${Date.now()}`, role: 'assistant', content: assistantText, apiData: finalData ?? undefined }
                    : m,
            ),
        )
        if (finalData.sos_triggered) setSosActive(true)
        applyIntervention(finalData)
    }

    const doSend = async (text: string) => {
        if (isGuestMode && guestSecondsLeft <= 0) {
            toast.info('Phiên chat thử đã hết. Mời bạn đăng ký tài khoản để tiếp tục.')
            navigate(ROUTE_PATHS.register)
            return
        }
        const now = Date.now()
        const pendingId = `p_${now}`
        setInput('')
        setLastFailedText(null)
        setMessages((prev) => [
            ...prev,
            { id: `u_${now}`, role: 'user', content: text, timestamp: now },
            { id: pendingId, role: 'assistant', content: 'Mây đang lắng nghe và viết lại thật cẩn thận cho bạn...', timestamp: now },
        ])
        setSending(true)

        try {
            if (!isGuestMode) {
                try {
                    const streamResponse = await chatService.sendMessageStream({ message: text, session_id: sessionId })
                    await consumeChatSse(streamResponse, pendingId)
                } catch (err) {
                    const status = err instanceof ApiRequestError ? (err.status ?? 0) : 0
                    if (!(err instanceof ApiRequestError) || status < 500) throw err
                    const rawData = await chatService.sendMessage({ message: text, session_id: sessionId })
                    const data = rawData as ChatApiData
                    const sid = typeof data.session_id === 'string' ? data.session_id : null
                    if (sid) setSessionId(sid)
                    const assistantText =
                        typeof data.reply === 'string' && data.reply
                            ? data.reply
                            : typeof data.assistant_text === 'string' && data.assistant_text
                                ? data.assistant_text
                                : 'Mình vẫn đang ở đây cùng bạn.'
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === pendingId
                                ? { id: `a_${Date.now()}`, role: 'assistant', content: assistantText, apiData: data }
                                : m,
                        ),
                    )
                    if (data.sos_triggered) setSosActive(true)
                    applyIntervention(data)
                    toast.info('Đường truyền stream đang lỗi, mình đã chuyển sang chế độ chat thường.')
                }
            } else {
                const rawData = await chatService.sendGuestMessage({ message: text, guest_session_id: sessionId })
                const data = rawData as ChatApiData
                const sid = typeof data.session_id === 'string' ? data.session_id : null
                if (sid) setSessionId(sid)
                if (sid && !guestDeadlineRef.current) {
                    guestDeadlineRef.current = Date.now() + FALLBACK_GUEST_CHAT_DURATION_SECONDS * 1000
                }
                const assistantText =
                    typeof data.reply === 'string' && data.reply
                        ? data.reply
                        : typeof data.assistant_text === 'string' && data.assistant_text
                            ? data.assistant_text
                            : 'Mình vẫn đang ở đây cùng bạn.'
                setMessages((prev) =>
                    prev.map((m) =>
                        m.id === pendingId
                            ? { id: `a_${Date.now()}`, role: 'assistant', content: assistantText, apiData: data }
                            : m,
                    ),
                )
                if (data.sos_triggered) setSosActive(true)
                applyIntervention(data)
            }
        } catch (err) {
            if (err instanceof ApiRequestError && err.code === 'GUEST_TRIAL_EXPIRED') {
                setGuestSecondsLeft(0)
                guestExpiredNotifiedRef.current = true
                toast.info('Bạn đã dùng hết 2 phút chat thử. Mời bạn đăng ký để tiếp tục.')
                navigate(ROUTE_PATHS.register)
                return
            }
            const errorMessage = err instanceof Error ? err.message : 'Gửi tin nhắn thất bại'
            toast.error(errorMessage)
            setLastFailedText(text)
            setMessages((prev) =>
                prev.map((m) =>
                    m.id === pendingId
                        ? { id: `e_${Date.now()}`, role: 'assistant', content: 'Mình bị gián đoạn một chút, bạn thử lại giúp mình nhé.' }
                        : m,
                ),
            )
        } finally {
            setSending(false)
        }
    }

    const loadHistory = async () => {
        setHistoryLoading(true)
        try {
            const data = await chatService.getSessions()
            setSessions(data.sessions)
        } catch {
            setSessions([])
        } finally {
            setHistoryLoading(false)
        }
    }

    const openHistory = async () => {
        if (showHistory) {
            setShowHistory(false)
            return
        }
        setShowHistory(true)
        await loadHistory()
    }

    const loadSessionMessages = async (targetSessionId: string) => {
        setSosActive(false)
        try {
            const data = await chatService.getSessionMessages(targetSessionId, 100, 0)
            setSessionId(targetSessionId)
            setMessages(data.messages.map((msg) => ({ id: msg.message_id, role: msg.role, content: msg.content })))
            setShowHistory(false)
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Không tải được lịch sử hội thoại')
        }
    }

    const handleSend: FormSubmitHandler = async (event) => {
        event.preventDefault()
        if (!canSend) return
        await doSend(input.trim())
    }

    const handleRetry = () => {
        if (!lastFailedText || sending) return
        setInput(lastFailedText)
        setLastFailedText(null)
    }

    const handleToggleVoiceConsent = async () => {
        const next = !voiceConsent
        try {
            const res = await policyService.setVoiceConsent(next)
            setVoiceConsent(Boolean(res.voice_consent))
            toast.success(next ? 'Đã bật hỗ trợ voice chủ động' : 'Đã tắt hỗ trợ voice chủ động')
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Không cập nhật được cài đặt voice')
        }
    }

    const openAttachment = (item: TheDinhKem) => {
        if (item.route) { navigate(item.route); return }
        if (item.action === 'open_connect_map' || item.type === 'clinic_map') { navigate(ROUTE_PATHS.support); return }
        if (item.action === 'open_resource' || item.type === 'resource') { navigate(ROUTE_PATHS.resources); return }
        if (item.type.includes('exercise') || item.type === 'body_scan') {
            navigate(`${ROUTE_PATHS.exercises}?exercise=${encodeURIComponent(item.id)}`)
            return
        }
        navigate(ROUTE_PATHS.resources)
    }

    // Derived display values
    const lastData = [...messages].reverse().find((m) => m.role === 'assistant' && m.apiData)?.apiData
    const modeLabel =
        lastData?.conversation_mode === 'de_escalation'
            ? { text: 'Khủng hoảng', cls: 'text-red-700 border-red-300 bg-red-50' }
            : lastData?.conversation_mode === 'supportive'
                ? { text: 'Hỗ trợ', cls: 'text-amber-700 border-amber-300 bg-amber-50' }
                : null

    // ─── Render ────────────────────────────────────────────────────────────────
    return (
        <div>
            <div className="h-[92dvh] flex flex-col bg-theme-surface/80 backdrop-blur-3xl rounded-[2.5rem] p-4 shadow-xl border border-theme-border/50">

                {/* ── Header ───────────────────────────────────────────── */}
                <div className="flex shrink-0 items-center justify-between mb-3 border-b border-theme-border/50 px-5 py-3">
                    <div className="flex items-center gap-3">
                        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-theme-accent/20 text-theme-accent">
                            <Leaf className="h-7 w-7" aria-hidden />
                        </div>
                        <div>
                            <p className="text-2xl font-display font-semibold text-theme-text-primary">Serene</p>
                            <p className="text-sm text-theme-text-secondary">Luôn ở đây cùng bạn</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2" ref={optionsRef}>
                        {voiceStatus && (
                            <VoiceStatusBadge
                                status={voiceStatus}
                                className="rounded-full bg-theme-bg-secondary px-2.5 py-1"
                            />
                        )}
                        {isGuestMode && (
                            <span className="rounded-full border border-amber-300/30 bg-amber-500/10 px-2.5 py-1 text-[10px] font-medium text-amber-500">
                                {guestCountdownLabel}
                            </span>
                        )}
                        {modeLabel && (
                            <span className={`rounded-full border px-2.5 py-1 text-[10px] font-medium ${isDark ? 'border-amber-500/30 bg-amber-500/10 text-amber-500' : modeLabel.cls}`}>
                                {modeLabel.text}
                            </span>
                        )}
                        <button
                            type="button"
                            onClick={() => void openHistory()}
                            className="flex items-center justify-center rounded-full text-theme-text-secondary transition hover:text-theme-text-primary"
                            aria-label="Lịch sử chat"
                        >
                            <History className="h-6 w-6" />
                        </button>
                        <div className="relative">
                            <button
                                type="button"
                                onClick={() => setShowOptions((prev) => !prev)}
                                className="flex items-center justify-center rounded-full text-theme-text-secondary transition hover:text-theme-text-primary"
                                aria-label="Tùy chọn"
                            >
                                <MoreVertical className="h-6 w-6" />
                            </button>
                            {showOptions && (
                                <div className="absolute right-0 top-10 z-50 w-80 rounded-2xl border border-theme-border/50 bg-theme-surface p-3 shadow-xl backdrop-blur-xl">
                                    <p className="mb-3 text-[10px] uppercase tracking-[0.22em] text-theme-text-secondary">Tùy chọn</p>
                                    <div className="space-y-2">
                                        <div className="flex items-center justify-between rounded-xl border border-theme-border/20 bg-theme-bg-secondary/50 px-3 py-2.5">
                                            <div>
                                                <p className="text-sm font-semibold text-theme-text-primary">Voice hỗ trợ</p>
                                                <p className="mt-0.5 text-[11px] text-theme-text-secondary">Gợi ý giọng nói chủ động khi cần</p>
                                            </div>
                                            <Switch
                                                checked={voiceConsent}
                                                onCheckedChange={() => void handleToggleVoiceConsent()}
                                                disabled={isGuestMode}
                                                aria-label="Voice hỗ trợ"
                                            />
                                        </div>
                                        <div className="flex items-center justify-between rounded-xl border border-theme-border/20 bg-theme-bg-secondary/50 px-3 py-2.5">
                                            <div>
                                                <p className="text-sm font-semibold text-theme-text-primary">Debug info</p>
                                                <p className="mt-0.5 text-[11px] text-theme-text-secondary">Distress · routing · safety</p>
                                            </div>
                                            <Switch checked={showDebug} onCheckedChange={setShowDebug} aria-label="Debug" />
                                        </div>
                                        {!isGuestMode && (
                                            <div className="rounded-xl border border-theme-border/20 bg-theme-bg-secondary/50 px-3 py-2.5">
                                                <p className="mb-2 text-sm font-semibold text-theme-text-primary">Chọn nhân vật</p>
                                                <PersonaSelector onSelect={() => setShowOptions(false)} />
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <ChatHistoryModal
                    open={showHistory}
                    loading={historyLoading}
                    sessions={sessions}
                    onClose={() => setShowHistory(false)}
                    onSelectSession={(sessionId) => void loadSessionMessages(sessionId)}
                />

                {/* ── Tab bar (Chat / Ký ức) — chỉ hiện khi đăng nhập ───────────────── */}
                {!isGuestMode && (
                    <div className="flex shrink-0 gap-1 border-b border-theme-border/30 px-5 pb-0">
                        {(['chat', 'memory'] as const).map((tab) => (
                            <button
                                key={tab}
                                type="button"
                                onClick={() => setActiveTab(tab)}
                                className={[
                                    'rounded-t-xl px-4 py-2 text-sm font-medium transition-colors',
                                    activeTab === tab
                                        ? 'border-b-2 border-theme-accent text-theme-accent'
                                        : 'text-theme-text-secondary hover:text-theme-text-primary',
                                ].join(' ')}
                            >
                                {tab === 'chat' ? 'Chat' : 'Ký ức'}
                            </button>
                        ))}
                    </div>
                )}

                {/* ── Tab content ───────────────────────────────────────── */}
                {activeTab === 'memory' ? (
                    <div className="flex-1 overflow-y-auto">
                        <MemoryCardsTab />
                    </div>
                ) : (
                <div className="flex-1 mb-8 overflow-y-auto p-4 sm:px-6">
                    <div className="flex min-h-full flex-col justify-end gap-3">
                        {messages.length === 0 ? (
                            <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
                                <Leaf className="h-14 w-14 text-theme-accent opacity-90" aria-hidden />
                                <p className=" text-theme-text-secondary">Chia sẻ điều bạn đang cảm thấy, mình lắng nghe.</p>
                                {!isGuestMode && !checkInDone && (
                                    <div className="mt-2 w-full max-w-sm">
                                        <ChatEntryCheckIn onComplete={() => setCheckInDone(true)} />
                                    </div>
                                )}
                            </div>
                        ) : (
                            messages.map((m, idx) => {
                                const isAI = m.role === 'assistant'
                                const prev = messages[idx - 1]
                                const showDivider =
                                    m.timestamp != null &&
                                    (prev == null ||
                                        prev.timestamp == null ||
                                        new Date(prev.timestamp).toDateString() !== new Date(m.timestamp).toDateString())
                                return (
                                    <div key={m.id}>
                                        {showDivider && m.timestamp != null && <DateDivider timestamp={m.timestamp} />}
                                        <div className={`flex gap-3 ${isAI ? '' : 'flex-row-reverse'}`}>
                                            <div className="mt-1 flex h-9 w-9 shrink-0 select-none items-center justify-center rounded-full bg-theme-accent/15 text-theme-accent" aria-hidden="true">
                                                {isAI ? <Leaf className="h-5 w-5" /> : <UserRound className="h-5 w-5" />}
                                            </div>
                                            <div className={`flex max-w-[70%] flex-col gap-2 ${isAI ? 'items-start' : 'items-end'}`}>
                                                <article
                                                    className={[
                                                        'rounded-2xl px-4 py-3 leading-relaxed whitespace-pre-line border',
                                                        isAI
                                                            ? m.apiData?.sos_triggered
                                                                ? 'bg-red-50 text-red-800 border-red-200'
                                                                : 'bg-theme-surface/80 text-theme-text-primary border-theme-border/30 shadow-sm'
                                                            : 'bg-theme-accent text-white border-transparent',
                                                    ].join(' ')}
                                                >
                                                    {m.content}
                                                </article>
                                                {m.apiData && <CrisisPanel data={m.apiData} />}
                                                {m.apiData?.the_dinh_kem?.map((item, i) => (
                                                    <AttachmentCard key={`${item.type}-${item.id}-${i}`} item={item} onOpen={openAttachment} />
                                                ))}
                                                {m.apiData &&
                                                    !m.apiData.sos_triggered &&
                                                    m.apiData.conversation_mode !== 'normal' && (
                                                        <QuickReplies
                                                            replies={m.apiData.goi_y_nhanh}
                                                            onSelect={(text) => void doSend(text)}
                                                        />
                                                    )}
                                                {showDebug && m.apiData && (
                                                    <div className="mt-1 space-y-0.5">
                                                        <RoutingBadge history={m.apiData.routing_history} />
                                                        <DistressBar score={m.apiData.distress_score} />
                                                        {m.apiData.safety_tier && m.apiData.safety_tier !== 'normal' && (
                                                            <SafetyBadge tier={m.apiData.safety_tier} />
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )
                            })
                        )}
                        <TypingIndicator visible={sending} />
                        <div ref={bottomRef} />
                    </div>
                </div>
                )}

                {/* ── Retry notice ──────────────────────────────────────── */}
                {lastFailedText && (
                    <div className="flex shrink-0 items-center gap-3 border-t border-red-200 bg-red-50/80 px-5 py-2 text-sm text-red-700">
                        <span>Tin nhắn trước gửi lỗi.</span>
                        <button
                            type="button"
                            onClick={handleRetry}
                            className="font-medium underline underline-offset-4 transition hover:text-red-800"
                        >
                            Thử lại
                        </button>
                    </div>
                )}
                {/* ── Input bar ─────────────────────────────────────────── */}
                <form
                    onSubmit={handleSend}
                    className="sticky bottom-15 rounded-full bg-theme-surface px-4 py-3 backdrop-blur-sm border border-theme-border/50 shadow-2xl"
                >
                    {/* overlay */}

                    <div className="flex items-center gap-3">
                        <input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            disabled={isGuestMode && guestSecondsLeft <= 0}
                            placeholder="Chia sẻ điều bạn đang cảm thấy..."
                            className="flex-1 rounded-full bg-transparent px-4 py-3 text-md text-theme-text-primary focus:outline-none"
                        />
                        <button
                            type="submit"
                            disabled={!canSend}
                            className="shrink-0 rounded-full bg-theme-accent px-5 py-2.5 font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                            {sending ? '···' : 'Gửi'}
                        </button>
                    </div>
                </form>
            </div>
            <HotlineBar visible={sosActive} />
        </div>
    )
}
