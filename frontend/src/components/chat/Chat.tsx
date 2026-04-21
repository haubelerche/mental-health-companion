import { useEffect, useMemo, useRef, useState } from 'react'
import type { ComponentProps } from 'react'
import { History, Leaf, MoreVertical } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import { resolveMediaUrl } from '../../api/httpClient'
import { ApiRequestError } from '../../api/types'
import { useAuth } from '../../hooks/useAuth'
import { ROUTE_PATHS } from '../../routes/paths'
import { chatService } from '../../services/chatService'
import { policyService } from '../../services/policyService'
import { Switch } from '../ui/switch'

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
type TheDinhKem = { type: string; id: string; title: string }
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
    goi_y_nhanh?: string[]
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

type UiMessage = {
    id: string
    role: 'user' | 'assistant'
    content: string
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
            <span className="text-[10px] font-medium text-serene-muted">Luồng:</span>
            {history.map((node, i) => (
                <span key={i} className="flex items-center gap-0.5">
                    <span
                        className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-medium capitalize ${nodeColors[node] ?? 'bg-gray-100 text-gray-600'}`}
                    >
                        {node}
                    </span>
                    {i < history.length - 1 && <span className="text-[10px] text-serene-muted/50">→</span>}
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
            <span className="text-[10px] text-serene-muted">Distress</span>
            <div className="h-1.5 w-20 overflow-hidden rounded-full bg-gray-200">
                <div className={`h-full transition-all ${color}`} style={{ width: `${pct}%` }} />
            </div>
            <span className="font-mono text-[10px] text-serene-muted">{score.toFixed(2)}</span>
        </div>
    )
}

function QuickReplies({ replies, onSelect }: { replies?: string[]; onSelect: (text: string) => void }) {
    if (!replies?.length) return null
    return (
        <div className="mt-2 flex flex-wrap gap-1.5">
            {replies.map((q, i) => (
                <button
                    key={i}
                    type="button"
                    onClick={() => onSelect(q)}
                    className="rounded-full border border-serene-primary/40 bg-white px-3 py-1 text-xs text-serene-primary transition-colors hover:bg-serene-primary hover:text-white"
                >
                    {q}
                </button>
            ))}
        </div>
    )
}

function AttachmentCard({ item }: { item: TheDinhKem }) {
    const icons: Record<string, string> = {
        breathing_exercise: '🌬️',
        meditation: '🧘',
        music: '🎵',
    }
    return (
        <div className="mt-1.5 flex items-center gap-2 rounded-xl border border-serene-primary/20 bg-serene-primary/5 px-3 py-2">
            <span className="text-base">{icons[item.type] ?? '📎'}</span>
            <div>
                <p className="text-xs font-medium text-serene-ink">{item.title}</p>
                <p className="text-[10px] text-serene-muted">{item.type.replace(/_/g, ' ')}</p>
            </div>
        </div>
    )
}

function CrisisPanel({ data }: { data: ChatApiData }) {
    if (!data.sos_triggered) return null
    return (
        <div className="mt-3 space-y-2.5 rounded-2xl border border-red-200 bg-red-50/90 p-4">
            {/* Header */}
            <div className="flex items-center gap-2">
                <span className="text-xl">🆘</span>
                <div>
                    <p className="text-sm font-semibold text-red-800">Chế độ hỗ trợ khủng hoảng</p>
                    <p className="text-[10px] text-red-500">
                        risk_level: {data.risk_level ?? '—'} · tier: {data.safety_tier}
                    </p>
                </div>
            </div>

            {/* Assistant strategy flags */}
            {data.assistant_strategy && (
                <div className="flex flex-wrap gap-1.5">
                    {data.assistant_strategy.keep_engaged && (
                        <span className="rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-medium text-green-800">
                            ✓ Giữ kết nối
                        </span>
                    )}
                    {data.assistant_strategy.encourage_external_help && (
                        <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-800">
                            ✓ Gợi hỗ trợ ngoài
                        </span>
                    )}
                    {data.assistant_strategy.avoid_hard_stop && (
                        <span className="rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-medium text-purple-800">
                            ✓ Dual-focus UI
                        </span>
                    )}
                </div>
            )}

            {/* Micro actions */}
            {data.micro_actions?.length ? (
                <div>
                    <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-red-700">
                        Hành động nhỏ ngay bây giờ
                    </p>
                    <div className="space-y-1.5">
                        {data.micro_actions.map((a, i) => (
                            <div key={i} className="flex items-start gap-2 rounded-lg bg-white/70 px-3 py-2">
                                <span className="text-sm">{a.type === 'breathing' ? '🌬️' : '👁️'}</span>
                                <span className="text-xs text-serene-ink">{a.label}</span>
                            </div>
                        ))}
                    </div>
                </div>
            ) : null}

            {/* Hotline cards */}
            {data.hotline_cards?.length ? (
                <div>
                    <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-red-700">
                        Đường dây hỗ trợ
                    </p>
                    <div className="space-y-1.5">
                        {data.hotline_cards.map((h, i) => (
                            <a
                                key={i}
                                href={`tel:${h.phone.replace(/\s/g, '')}`}
                                className="flex items-center justify-between rounded-lg bg-white/80 px-3 py-2 transition-colors hover:bg-red-50"
                            >
                                <span className="text-xs text-serene-ink">{h.label}</span>
                                <span className="font-bold text-red-600">{h.phone}</span>
                            </a>
                        ))}
                    </div>
                </div>
            ) : null}

            {/* Referral options */}
            {data.referral_options?.length ? (
                <div className="flex flex-wrap gap-1.5">
                    {data.referral_options.map((r, i) => (
                        <span
                            key={i}
                            className="rounded-full border border-red-200 bg-white/80 px-2 py-0.5 text-[10px] text-red-700"
                        >
                            {r.type === 'counselor'
                                ? '👨‍⚕️ Tư vấn viên'
                                : r.type === 'trusted_contact'
                                  ? '🤝 Người tin cậy'
                                  : r.type}
                        </span>
                    ))}
                </div>
            ) : null}

            {data.followup_priority && (
                <p className="text-[10px] font-medium text-red-600">⚑ Cần theo dõi ưu tiên</p>
            )}
        </div>
    )
}

// ─── Main component ────────────────────────────────────────────────────────────

export default function Chat() {
    type FormSubmitHandler = NonNullable<ComponentProps<'form'>['onSubmit']>
    const GUEST_CHAT_DURATION_SECONDS = 120

    const [sessionId, setSessionId] = useState<string | null>(null)
    const [messages, setMessages] = useState<UiMessage[]>([])
    const [input, setInput] = useState('')
    const [sending, setSending] = useState(false)
    const [voiceConsent, setVoiceConsent] = useState(false)
    const [voiceStatus, setVoiceStatus] = useState('')
    const [lastFailedText, setLastFailedText] = useState<string | null>(null)
    const [showDebug, setShowDebug] = useState(true)
    const [showOptions, setShowOptions] = useState(false)
    const [guestSecondsLeft, setGuestSecondsLeft] = useState<number>(GUEST_CHAT_DURATION_SECONDS)
    const pollRef = useRef<number | null>(null)
    const bottomRef = useRef<HTMLDivElement | null>(null)
    const optionsRef = useRef<HTMLDivElement | null>(null)
    const guestDeadlineRef = useRef<number | null>(null)
    const { user } = useAuth()
    const navigate = useNavigate()
    const isGuestMode = !user

    useEffect(() => {
        policyService
            .getVoiceConsent()
            .then((res) => setVoiceConsent(Boolean(res.voice_consent)))
            .catch(() => undefined)
    }, [])

    useEffect(() => {
        if (!isGuestMode) {
            setGuestSecondsLeft(GUEST_CHAT_DURATION_SECONDS)
            guestDeadlineRef.current = null
            return
        }
        if (!guestDeadlineRef.current) {
            guestDeadlineRef.current = Date.now() + GUEST_CHAT_DURATION_SECONDS * 1000
        }

        const tick = () => {
            const deadline = guestDeadlineRef.current ?? Date.now()
            const next = Math.max(0, Math.ceil((deadline - Date.now()) / 1000))
            setGuestSecondsLeft(next)
            if (next <= 0) {
                toast.info('Bạn đã dùng hết 2 phút chat thử. Đăng ký để tiếp tục nhé.')
                navigate(ROUTE_PATHS.register, { replace: true })
            }
        }
        tick()
        const timer = window.setInterval(tick, 1000)
        return () => window.clearInterval(timer)
    }, [isGuestMode, navigate])

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

    const canSend = useMemo(() => !sending && input.trim().length > 0, [sending, input])

    const playAudioUrl = (audioUrl: string) => {
        const audio = new Audio(resolveMediaUrl(audioUrl))
        void audio.play().catch(() => {
            toast.info('Trình duyệt chặn tự phát audio, hãy bấm play thủ công.')
        })
    }

    const pollVoiceJob = async (ttsJobId: string, fallbackScript?: string, attempts = 0) => {
        if (attempts > 8) {
            setVoiceStatus('Voice phản hồi chậm, đang dùng bản text trước.')
            if (fallbackScript) {
                setMessages((prev) => [...prev, { id: `vs_to_${Date.now()}`, role: 'assistant', content: fallbackScript }])
            }
            return
        }
        try {
            const job = await chatService.getVoiceJob(ttsJobId)
            setVoiceStatus(`Voice: ${job.status}`)
            if (job.status === 'ready' && job.audio_url) {
                playAudioUrl(job.audio_url)
                return
            }
            if (job.status === 'failed') {
                setVoiceStatus(job.error_message ? `Voice lỗi: ${job.error_message}` : 'Voice lỗi, chuyển về text.')
                if (fallbackScript) {
                    setMessages((prev) => [
                        ...prev,
                        { id: `vs_fail_${Date.now()}`, role: 'assistant', content: fallbackScript },
                    ])
                }
                return
            }
        } catch {
            if (fallbackScript) {
                setMessages((prev) => [...prev, { id: `vs_err_${Date.now()}`, role: 'assistant', content: fallbackScript }])
            }
            return
        }
        pollRef.current = window.setTimeout(() => {
            void pollVoiceJob(ttsJobId, fallbackScript, attempts + 1)
        }, 2000)
    }

    const applyIntervention = (data: ChatApiData) => {
        const intervention = data.intervention
        if (intervention?.type !== 'proactive_voice') return
        if (intervention.copy_ngan) {
            setMessages((prev) => [...prev, { id: `i_${Date.now()}`, role: 'assistant', content: intervention.copy_ngan ?? '' }])
        }
        if (Array.isArray(intervention.next_actions) && intervention.next_actions.length > 0) {
            const labels = intervention.next_actions.map((a) => `• ${a.label}`).join('\n')
            setMessages((prev) => [...prev, { id: `na_${Date.now()}`, role: 'assistant', content: `Gợi ý tiếp theo:\n${labels}` }])
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
                    ? {
                          id: `a_${Date.now()}`,
                          role: 'assistant',
                          content: assistantText,
                          apiData: finalData ?? undefined,
                      }
                    : m,
            ),
        )
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
            { id: `u_${now}`, role: 'user', content: text },
            { id: pendingId, role: 'assistant', content: 'Mây đang phản hồi nhanh cho bạn...' },
        ])
        setSending(true)

        try {
            if (!isGuestMode) {
                const streamResponse = await chatService.sendMessageStream({ message: text, session_id: sessionId })
                await consumeChatSse(streamResponse, pendingId)
            } else {
                const rawData = await chatService.sendGuestMessage({ message: text, guest_session_id: sessionId })
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
                            ? {
                                  id: `a_${Date.now()}`,
                                  role: 'assistant',
                                  content: assistantText,
                                  apiData: data,
                              }
                            : m,
                    ),
                )
                applyIntervention(data)
            }
        } catch (err) {
            if (err instanceof ApiRequestError && err.code === 'GUEST_TRIAL_EXPIRED') {
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
                        ? {
                              id: `e_${Date.now()}`,
                              role: 'assistant',
                              content: 'Mình bị gián đoạn một chút, bạn thử lại giúp mình nhé.',
                          }
                        : m,
                ),
            )
        } finally {
            setSending(false)
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

    // Latest assistant message data for header stats
    const lastData = [...messages].reverse().find((m) => m.role === 'assistant' && m.apiData)?.apiData

    const modeLabel =
        lastData?.conversation_mode === 'de_escalation'
            ? { text: '🆘 Khủng hoảng', cls: 'bg-red-100 text-red-700' }
            : lastData?.conversation_mode === 'supportive'
              ? { text: '🤗 Hỗ trợ', cls: 'bg-amber-100 text-amber-700' }
              : null

    return (
        <section className="space-y-4 max-w-4xl relative z-10 px-4 py-6 mx-auto">
            {/* ── Header ─────────────────────────────────────────────────── */}
            <div className="rounded-3xl border border-white/35 bg-white/60 p-5 backdrop-blur-xl">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-serene-accent/70 text-serene-primary">
                            <Leaf className="h-5 w-5" />
                        </div>
                        <div>
                            <h2 className="font-display text-3xl text-serene-ink">Serene</h2>
                            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-emerald-600">
                                ● Đang lắng nghe
                            </p>
                        </div>
                        {modeLabel && (
                            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${modeLabel.cls}`}>
                                {modeLabel.text}
                            </span>
                        )}
                    </div>
                    <div className="flex items-center gap-2" ref={optionsRef}>
                        {isGuestMode && (
                            <span className="rounded-full border border-amber-300 bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
                                Chat thử còn {guestSecondsLeft}s
                            </span>
                        )}
                        <button
                            type="button"
                            onClick={() => toast.info('Lịch sử chat sẽ sớm có mặt.')}
                            className="rounded-full p-2 text-serene-ink/70 transition hover:bg-serene-ink/10"
                            aria-label="Lịch sử chat"
                        >
                            <History className="h-5 w-5" />
                        </button>

                        <div className="relative">
                            <button
                                type="button"
                                onClick={() => setShowOptions((prev) => !prev)}
                                className="rounded-full p-2 text-serene-ink/70 transition hover:bg-serene-ink/10"
                                aria-label="Tùy chọn"
                            >
                                <MoreVertical className="h-5 w-5" />
                            </button>

                            {showOptions && (
                                <div className="absolute right-0 top-11 z-20 w-72 rounded-2xl border border-white/40 bg-white/95 p-3 shadow-xl backdrop-blur-xl">
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between rounded-xl border border-serene-outline/25 bg-white px-3 py-2.5">
                                            <div>
                                                <p className="text-sm font-semibold text-serene-ink">Voice hỗ trợ</p>
                                                <p className="text-[11px] text-serene-muted">
                                                    Gợi ý giọng nói chủ động khi cần
                                                </p>
                                            </div>
                                            <Switch
                                                checked={voiceConsent}
                                                onCheckedChange={() => void handleToggleVoiceConsent()}
                                                disabled={isGuestMode}
                                                aria-label="Voice hỗ trợ"
                                            />
                                        </div>

                                        <div className="flex items-center justify-between rounded-xl border border-serene-outline/25 bg-white px-3 py-2.5">
                                            <div>
                                                <p className="text-sm font-semibold text-serene-ink">Hiển thị debug</p>
                                                <p className="text-[11px] text-serene-muted">
                                                    Distress, routing, safety badge
                                                </p>
                                            </div>
                                            <Switch
                                                checked={showDebug}
                                                onCheckedChange={setShowDebug}
                                                aria-label="Hiển thị debug"
                                            />
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
                {voiceStatus ? <p className="mt-2 text-xs text-serene-muted">{voiceStatus}</p> : null}

                {/* Session-level debug stats */}
                {showDebug && lastData && (
                    <div className="mt-3 rounded-xl bg-serene-ink/5 px-3 py-2">
                        <DistressBar score={lastData.distress_score} />
                        <div className="mt-1.5 flex flex-wrap items-center gap-2">
                            <SafetyBadge tier={lastData.safety_tier} />
                            {lastData.tone_cam_xuc && (
                                <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700">
                                    tone: {lastData.tone_cam_xuc}
                                </span>
                            )}
                            {lastData.agent_display_name && (
                                <span className="rounded-full bg-serene-primary/10 px-2 py-0.5 text-[10px] font-medium text-serene-primary">
                                    {lastData.agent_display_name}
                                </span>
                            )}
                        </div>
                        <RoutingBadge history={lastData.routing_history} />
                    </div>
                )}
            </div>

            {/* ── Message feed ──────────────────────────────────────────── */}
            <div className="min-h-[70dvh]  overflow-y-auto rounded-3xl border border-white/35 bg-white/65 p-4 backdrop-blur-xl">
                {messages.length === 0 ? (
                    <p className="text-serene-muted">Hãy bắt đầu cuộc trò chuyện. Mình đang lắng nghe bạn.</p>
                ) : (
                    <div className="space-y-4">
                        {messages.map((m) => (
                            <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`flex max-w-[85%] flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                                    {/* Bubble */}
                                    <article
                                        className={[
                                            'rounded-2xl px-4 py-3 text-sm whitespace-pre-line',
                                            m.role === 'user'
                                                ? 'bg-serene-primary text-white'
                                                : m.apiData?.sos_triggered
                                                  ? 'border border-red-200 bg-red-50 text-serene-ink'
                                                  : m.apiData?.conversation_mode === 'supportive'
                                                    ? 'border border-amber-100 bg-amber-50 text-serene-ink'
                                                    : 'bg-white text-serene-ink',
                                        ].join(' ')}
                                    >
                                        {m.content}
                                    </article>

                                    {/* Crisis panel (SOS only) */}
                                    {m.apiData && <CrisisPanel data={m.apiData} />}

                                    {/* Attachments */}
                                    {m.apiData?.the_dinh_kem?.map((item, i) => (
                                        <AttachmentCard key={i} item={item} />
                                    ))}

                                    {/* Quick replies (non-SOS only) */}
                                    {m.apiData && !m.apiData.sos_triggered && (
                                        <QuickReplies
                                            replies={m.apiData.goi_y_nhanh}
                                            onSelect={(text) => void doSend(text)}
                                        />
                                    )}

                                    {/* Per-message debug info */}
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
                        ))}
                        <div ref={bottomRef} />
                    </div>
                )}
            </div>

            {/* ── Input ──────────────────────────────────────────────────── */}
            <form
                onSubmit={handleSend}
                className="flex gap-3 rounded-3xl border border-white/35 bg-white/70 p-3 backdrop-blur-xl"
            >
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Chia sẻ điều bạn đang cảm thấy..."
                    className="flex-1 rounded-2xl bg-white px-4 py-3 outline-none"
                />
                <button
                    type="submit"
                    disabled={!canSend}
                    className="rounded-2xl bg-serene-primary px-5 py-3 text-white disabled:cursor-not-allowed disabled:opacity-70"
                >
                    {sending ? 'Đang gửi...' : 'Gửi'}
                </button>
            </form>

            {lastFailedText ? (
                <div className="rounded-2xl border border-white/35 bg-white/60 p-3 text-sm text-serene-muted">
                    <span>Tin nhắn trước gửi lỗi.</span>{' '}
                    <button type="button" onClick={handleRetry} className="font-semibold text-serene-primary">
                        Thử lại
                    </button>
                </div>
            ) : null}
        </section>
    )
}
