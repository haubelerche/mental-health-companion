import { useEffect, useMemo, useRef, useState } from 'react'
import type { ComponentProps } from 'react'
import {
    Heart,
    History,
    Leaf,
    MapPin,
    MoreVertical,
    Music,
    Paperclip,
    Play,
    Plus,
    Send,
    Sprout,
    Wind,
} from 'lucide-react'
import { TypingIndicator } from './TypingIndicator'
import { DateDivider } from './DateDivider'
import { useNavigate, useLocation } from 'react-router-dom'
import { toast } from 'react-toastify'
import { resolveMediaUrl } from '../../../api/httpClient'
import { ApiRequestError } from '../../../api/types'
import { useAuth } from '../../../hooks/useAuth'
import { ROUTE_PATHS } from '../../../routes/paths'
import { chatService } from '../../../services/chatService'
import { personasService } from '../../../services/personasService'
import { HotlineBar } from '../../crisis/HotlineBar'
import { BreathingTimer } from '../../crisis/BreathingTimer'
import { CrisisStepper } from '../../crisis/CrisisStepper'
import type { CrisisAction } from '../../crisis/CrisisActionCard'
import { DatLeSosPopup, type DistressSupportPopup } from '../../crisis/DatLeSosPopup'
import { useDistressPopupCooldown } from '../../crisis/useDistressPopupCooldown'
import { ChatHistoryModal } from './ChatHistoryModal'
import UserMemoriesTab from './UserMemoriesTab'
import PersonaSelector from './PersonaSelector'
import VoiceStatusBadge, { TTS_TERMINAL_STATUSES } from './VoiceStatusBadge'
import type { TtsStatus } from './VoiceStatusBadge'
import Loading from '../../ui/Loading'
import chatSceneBg from '../../../assets/motion/page-serene-chat.gif'
import { DEFAULT_PERSONA_ID, PERSONA_DISPLAY_NAME, isPersonaId } from '../../../constants/personas'

//  API response types 

type HotlineCard = { label: string; phone: string }
type MicroAction = { type: string; label: string }
type GroundingAction = { id: string }
type ReferralOption = { type: string }
type AssistantStrategy = {
    keep_engaged: boolean
    encourage_external_help: boolean
    avoid_hard_stop: boolean
}
type ResourceSuggestion = {
    type: string
    id: string
    title: string
    description?: string | null
    duration_sec?: number
    action?: string
    route?: string
    thumbnail?: string | null
}
type TtsJob = { tts_job_id?: string | number | null; status?: string | null; audio_url?: string | null }
type MemeSuggestion = { id: string; image_path: string; alt?: string; trigger_reason?: string }

type ChatApiData = {
    session_id: string
    message_id?: string | null
    persona_id?: string | null
    reply?: string | null
    assistant_text?: string | null
    sos_triggered?: boolean
    route_tier?: 'fast' | 'service_only' | 'advisor_assisted'
    used_advisor_ids?: string[]
    resource_suggestions?: ResourceSuggestion[]
    nutrition_suggestion?: Record<string, unknown> | null
    optional_support?: Record<string, unknown> | null
    tts_job?: TtsJob | null
    latency_trace?: Record<string, unknown>
    risk_level?: number
    assistant_strategy?: AssistantStrategy
    micro_actions?: MicroAction[]
    hotline_cards?: HotlineCard[]
    grounding_actions?: GroundingAction[]
    referral_options?: ReferralOption[]
    meme_suggestion?: MemeSuggestion | null
    followup_priority?: boolean
    // Crisis plan fields (from serene_sos_voice_intervention_plan.md)
    crisis_plan?: CrisisPlan | null
    distress_ui?: DistressConversationUi | null
}

type DistressConversationUi = {
    mode?: 'none' | 'distress_soft_support' | 'sos_soft_popup'
    suppress_inline_crisis_cards?: boolean
    support_popup?: DistressSupportPopup | null
    allow_quick_replies?: boolean
    preferred_input_focus?: boolean
}

type CrisisActionCard = {
    id: string
    type:
        | 'voice_grounding'
        | 'breathing_timer'
        | 'trusted_contact'
        | 'hotline'
        | 'clinic_map'
        | 'video_grounding'
        | 'continue_chat'
    title: string
    description: string
    action: string
    route?: string | null
    priority: number
}

type CrisisPlan = {
    visible_text: string
    voice_script?: string
    additional_voice_scripts?: string[]
    follow_up_texts?: string[]
    action_cards: CrisisActionCard[]
    follow_up_question?: string
    safety_reason_codes?: string[]
    should_enqueue_voice?: boolean
    source?: 'llm' | 'fallback_template'
}

type UiMessage = {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp?: number
    apiData?: ChatApiData
    isPending?: boolean
    voice?: {
        ttsJobId: string
        status: string
        audioUrl?: string | null
        errorMessage?: string | null
    }
}

const EMOTION_MEME_URLS = import.meta.glob('../../../assets/emotions/*.{jpg,jpeg,png,gif}', {
    eager: true,
    query: '?url',
    import: 'default',
}) as Record<string, string>

function resolveEmotionMemeUrl(imagePath?: string | null): string | null {
    const token = String(imagePath || '').trim()
    if (!token) return null
    const key = Object.keys(EMOTION_MEME_URLS).find((candidate) => candidate.endsWith(`/${token}`))
    if (!key) return null
    return EMOTION_MEME_URLS[key]
}

//  Sub-components 

function VoiceMessageBubble({
    voice,
    onPlay,
}: {
    voice: NonNullable<UiMessage['voice']>
    onPlay: (audioUrl: string) => void
}) {
    const playable = voice.status === 'ready' || voice.status === 'cache_hit' || voice.status === 'skipped_duplicate'
    const failed = voice.status === 'failed'
    const bars = [14, 22, 30, 18, 36, 44, 28, 40, 24, 34, 46, 26, 38, 30, 20, 28]
    return (
        <article className="flex w-[260px] max-w-full items-center gap-3 border border-[#8a6a3f]/50 bg-[#fff4dc]/96 px-3 py-2.5 text-[#1a1008] shadow-[3px_3px_0_rgba(0,0,0,0.38)]">
            <button
                type="button"
                disabled={!playable || !voice.audioUrl}
                onClick={() => voice.audioUrl && onPlay(voice.audioUrl)}
                className="flex h-10 w-10 shrink-0 items-center justify-center border border-[#1a1008]/25 bg-[#1a1008] text-[#fff4dc] transition enabled:hover:bg-[#2c1a0d] disabled:cursor-not-allowed disabled:opacity-35"
                aria-label={playable ? 'Phát tin nhắn thoại' : 'Tin nhắn thoại chưa sẵn sàng'}
                title={playable ? 'Phát tin nhắn thoại' : 'Tin nhắn thoại chưa sẵn sàng'}
            >
                <Play className="h-5 w-5 translate-x-0.5" aria-hidden />
            </button>
            <div className="min-w-0 flex-1">
                <div className="flex h-10 items-center gap-1" aria-hidden="true">
                    {bars.map((height, idx) => (
                        <span
                            key={idx}
                            className={[
                                'w-1.5 bg-[#1a1008] transition-opacity',
                                playable ? 'opacity-90' : failed ? 'opacity-25' : 'animate-pulse opacity-55',
                            ].join(' ')}
                            style={{ height: `${height}px` }}
                        />
                    ))}
                </div>
                <p className="mt-1 truncate text-[10px] font-semibold uppercase tracking-wide text-[#1a1008]/55">
                    {failed ? (voice.errorMessage || 'Voice chưa tạo được') : playable ? 'Tin nhắn thoại' : 'Đang tạo giọng đọc...'}
                </p>
            </div>
        </article>
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

const ATTACHMENT_META: Record<string, { badge: string; action: string }> = {
    breathing_exercise: { badge: 'BÀI TẬP ĐỀ XUẤT', action: 'Bắt đầu' },
    grounding_exercise: { badge: 'BÀI TẬP ĐỀ XUẤT', action: 'Bắt đầu' },
    body_scan: { badge: 'BÀI TẬP ĐỀ XUẤT', action: 'Bắt đầu' },
    meditation: { badge: 'BÀI TẬP ĐỀ XUẤT', action: 'Bắt đầu' },
    music: { badge: 'NHẠC ĐỀ XUẤT', action: 'Mở' },
    recipe: { badge: 'CÔNG THỨC GỢI Ý', action: 'Xem' },
    nutrition: { badge: 'CÔNG THỨC GỢI Ý', action: 'Xem' },
    resource: { badge: 'NỘI DUNG ĐỀ XUẤT', action: 'Mở' },
    clinic_map: { badge: 'HỖ TRỢ GẦN BẠN', action: 'Xem' },
}

function AttachmentCard({ item, onOpen }: { item: ResourceSuggestion; onOpen: (item: ResourceSuggestion) => void }) {
    const IconCmp = ATTACHMENT_ICONS[item.type] ?? Paperclip
    const meta = ATTACHMENT_META[item.type] ?? ATTACHMENT_META.resource
    const duration = item.duration_sec ? `${Math.max(1, Math.round(item.duration_sec / 60))} phút` : item.type.replace(/_/g, ' ')
    const title = item.title?.trim() ? item.title.trim() : 'Gợi ý cho bạn'
    const subtitle = item.description?.trim() ? item.description.trim() : duration
    return (
        <button
            type="button"
            onClick={() => onOpen(item)}
            className="mt-2 grid w-full max-w-xl grid-cols-[48px_1fr_auto] items-center gap-3 border border-[#6e5437]/45 bg-[#17130e]/88 px-3 py-2.5 text-left text-[#fff4dc] shadow-[4px_4px_0_rgba(0,0,0,0.24)] transition hover:bg-[#211a13]/92"
        >
            <span className="flex h-10 w-10 items-center justify-center border border-[#fff4dc]/20 bg-[#0f1b17] text-[#6fc7df]">
                <IconCmp className="h-5 w-5" aria-hidden />
            </span>
            <div className="min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[#fff4dc]/60">{meta.badge}</p>
                <p className="truncate text-sm font-bold leading-tight text-[#fff4dc]">{title}</p>
                <p className="mt-0.5 line-clamp-1 text-[11px] leading-relaxed text-[#fff4dc]/60">
                    {subtitle}
                </p>
            </div>
            <span className="border border-[#6e8a53]/70 bg-[#4f633d] px-3 py-1.5 text-[11px] font-semibold uppercase text-[#dbe7c9]">
                {meta.action}
            </span>
        </button>
    )
}

function MemeCard({ item }: { item: MemeSuggestion }) {
    const imageUrl = resolveEmotionMemeUrl(item.image_path)
    if (!imageUrl) return null
    return (
        <article className="mt-2 inline-flex max-w-[260px] overflow-hidden border border-[#8a6a3f]/50 bg-[#17130e]/88 shadow-[4px_4px_0_rgba(0,0,0,0.24)] sm:max-w-[320px]">
            <img
                src={imageUrl}
                alt={item.alt || 'Emotion meme'}
                className="max-h-[220px] w-auto max-w-full object-contain"
                loading="lazy"
            />
        </article>
    )
}

const LEGACY_CHAT_SESSION_KEY = 'serene_chat_session_id'

function chatSessionStorageKey(personaId: string) {
    return `serene_chat_session_id:${isPersonaId(personaId) ? personaId : DEFAULT_PERSONA_ID}`
}

function readStoredChatSession(personaId: string) {
    const key = chatSessionStorageKey(personaId)
    const stored = localStorage.getItem(key)
    if (stored) return stored
    return personaId === DEFAULT_PERSONA_ID ? localStorage.getItem(LEGACY_CHAT_SESSION_KEY) : null
}

export default function Chat() {
    type FormSubmitHandler = NonNullable<ComponentProps<'form'>['onSubmit']>
    const FALLBACK_GUEST_CHAT_DURATION_SECONDS = 120

    const [sessionId, setSessionId] = useState<string | null>(() => readStoredChatSession(DEFAULT_PERSONA_ID))
    const [messages, setMessages] = useState<UiMessage[]>([])
    const [input, setInput] = useState('')
    const [sending, setSending] = useState(false)
    const [voiceStatus, setVoiceStatus] = useState('')
    const [pendingAudioUrl, setPendingAudioUrl] = useState<string | null>(null)
    const [lastFailedText, setLastFailedText] = useState<string | null>(null)
    const [showOptions, setShowOptions] = useState(false)
    const [showHistory, setShowHistory] = useState(false)
    const [activePersonaId, setActivePersonaId] = useState<string>(DEFAULT_PERSONA_ID)
    const [heartedMessageIds, setHeartedMessageIds] = useState<Set<string>>(() => new Set())
    const [historyLoading, setHistoryLoading] = useState(false)
    const [sessions, setSessions] = useState<Array<{ session_id: string; preview: string | null; last_message_at: string }>>([])
    const [guestSecondsLeft, setGuestSecondsLeft] = useState<number>(FALLBACK_GUEST_CHAT_DURATION_SECONDS)
    const [guestSessionLoading, setGuestSessionLoading] = useState(false)
    const [activeTab, setActiveTab] = useState<'chat' | 'memory'>('chat')
    const [memoryRefreshKey, setMemoryRefreshKey] = useState(0)
    const [endingSession, setEndingSession] = useState(false)
    const pollRef = useRef<number | null>(null)
    const bottomRef = useRef<HTMLDivElement | null>(null)
    const optionsRef = useRef<HTMLDivElement | null>(null)
    const activePersonaRef = useRef<string>(DEFAULT_PERSONA_ID)
    const activeSessionRef = useRef<string | null>(sessionId)
    const activeRequestIdRef = useRef(0)
    const sendingRef = useRef(false)
    const guestDeadlineRef = useRef<number | null>(null)
    const guestExpiredNotifiedRef = useRef(false)
    const playedVoiceJobsRef = useRef<Set<string>>(new Set())
    const [hotlineSheetOpen, setHotlineSheetOpen] = useState(false)
    const [breathingOpen, setBreathingOpen] = useState(false)
    const [activeDistressPopup, setActiveDistressPopup] = useState<DistressSupportPopup | null>(null)
    const { isDismissed: isDistressPopupDismissed, dismiss: dismissDistressPopup } = useDistressPopupCooldown()
    const { user } = useAuth()
    const navigate = useNavigate()
    const location = useLocation()
    const isGuestMode = !user
    const personaLabel = PERSONA_DISPLAY_NAME[activePersonaId] ?? PERSONA_DISPLAY_NAME[DEFAULT_PERSONA_ID]

    useEffect(() => {
        activePersonaRef.current = activePersonaId
    }, [activePersonaId])

    useEffect(() => {
        activeSessionRef.current = sessionId
    }, [sessionId])

    useEffect(() => {
        if (isGuestMode) return
        if (sessionId) {
            localStorage.setItem(chatSessionStorageKey(activePersonaRef.current), sessionId)
            localStorage.removeItem(LEGACY_CHAT_SESSION_KEY)
        } else {
            localStorage.removeItem(chatSessionStorageKey(activePersonaRef.current))
        }
    }, [isGuestMode, sessionId])

    useEffect(() => {
        if (isGuestMode) return
        activeRequestIdRef.current += 1
        sendingRef.current = false
        setSending(false)
        setSessionId(readStoredChatSession(activePersonaId))
        setMessages([])
        setPendingAudioUrl(null)
        setVoiceStatus('')
        playedVoiceJobsRef.current.clear()
    }, [activePersonaId, isGuestMode])
    useEffect(() => {
        const state = location.state as { crisisMode?: boolean } | null
        if (state?.crisisMode) setHotlineSheetOpen(false)
    }, [location.state])

    useEffect(() => {
        if (isGuestMode || !user) {
            setActivePersonaId(DEFAULT_PERSONA_ID)
            return
        }

        let cancelled = false
        void personasService.getMe()
            .then((me) => {
                if (!cancelled) setActivePersonaId(isPersonaId(me.persona_id) ? me.persona_id : DEFAULT_PERSONA_ID)
            })
            .catch(() => {
                if (!cancelled) setActivePersonaId(DEFAULT_PERSONA_ID)
            })

        return () => {
            cancelled = true
        }
    }, [isGuestMode, user])

    // Show Serene's greeting on fresh session (no messages loaded yet).
    useEffect(() => {
        if (!user || isGuestMode || sessionId) return
        let cancelled = false
        chatService.getGreeting(activePersonaId).then((res) => {
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
    }, [user, isGuestMode, sessionId, activePersonaId])

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
        const latestPopup = [...messages]
            .reverse()
            .map((message) => message.apiData?.distress_ui?.support_popup)
            .find((popup): popup is DistressSupportPopup => Boolean(popup?.show && popup.popup_id))
        if (!latestPopup || isDistressPopupDismissed(latestPopup.popup_id)) {
            setActiveDistressPopup(null)
            return
        }
        setActiveDistressPopup(latestPopup)
    }, [isDistressPopupDismissed, messages])

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
        // Data/blob URLs play directly without a network request.
        if (audioUrl.startsWith('data:') || audioUrl.startsWith('blob:')) {
            const audio = new Audio(audioUrl)
            if (audioUrl.startsWith('blob:')) {
                audio.onended = () => URL.revokeObjectURL(audioUrl)
                audio.onerror = () => URL.revokeObjectURL(audioUrl)
            }
            void audio.play().then(() => {
                setVoiceStatus('')
                setPendingAudioUrl(null)
            }).catch(() => {
                setPendingAudioUrl(audioUrl)
                setVoiceStatus('')
            })
            return
        }
        // For HTTP URLs, fetch with credentials so the auth cookie is sent before playback.
        void fetch(resolveMediaUrl(audioUrl), { credentials: 'include' })
            .then(async (res) => {
                if (!res.ok) throw new Error(`${res.status}`)
                const blob = await res.blob()
                const objectUrl = URL.createObjectURL(blob)
                const audio = new Audio(objectUrl)
                audio.onended = () => URL.revokeObjectURL(objectUrl)
                audio.onerror = () => URL.revokeObjectURL(objectUrl)
                return audio.play().then(() => {
                    setVoiceStatus('')
                    setPendingAudioUrl(null)
                }).catch(() => {
                    // Browser autoplay blocked: keep the authenticated blob for manual play.
                    setPendingAudioUrl(objectUrl)
                    setVoiceStatus('')
                })
            })
            .catch(() => {
                setPendingAudioUrl(null)
                setVoiceStatus('failed')
            })
    }

    const updateVoiceMessage = (messageId: string, patch: Partial<NonNullable<UiMessage['voice']>>) => {
        setMessages((prev) =>
            prev.map((m) =>
                m.id === messageId && m.voice
                    ? { ...m, voice: { ...m.voice, ...patch } }
                    : m,
            ),
        )
    }

    const pollVoiceJob = async (ttsJobId: string, attempts = 0, voiceMessageId?: string): Promise<void> => {
        if (attempts > 20) {
            if (voiceMessageId) {
                updateVoiceMessage(voiceMessageId, { status: 'failed', errorMessage: 'Voice job mất quá lâu.' })
            } else {
                setVoiceStatus('failed')
            }
            return
        }
        try {
            const job = await chatService.getVoiceJob(ttsJobId)
            if (voiceMessageId) {
                updateVoiceMessage(voiceMessageId, { status: job.status })
            } else {
                setVoiceStatus(job.status)
            }
            // Stop polling on any terminal status
            if (TTS_TERMINAL_STATUSES.has(job.status as TtsStatus)) {
                const playableAudio = job.audio_data_uri || job.audio_url
                if (
                    (job.status === 'ready' || job.status === 'cache_hit' || job.status === 'skipped_duplicate') &&
                    playableAudio
                ) {
                    if (voiceMessageId) {
                        updateVoiceMessage(voiceMessageId, { status: 'ready', audioUrl: playableAudio, errorMessage: null })
                    } else {
                        playAudioUrl(playableAudio)
                    }
                } else if (job.status === 'failed' && playableAudio) {
                    if (voiceMessageId) {
                        updateVoiceMessage(voiceMessageId, { status: 'ready', audioUrl: playableAudio, errorMessage: null })
                    } else {
                        playAudioUrl(playableAudio)
                    }
                } else if (job.status === 'failed') {
                    if (voiceMessageId) {
                        updateVoiceMessage(voiceMessageId, { status: 'failed', errorMessage: job.error_message || null })
                    } else {
                        setVoiceStatus(job.error_message ? `failed:${job.error_message}` : 'failed')
                    }
                }
                // All other terminal statuses (cache_hit, skipped_duplicate, provider_disabled,
                // cancelled, expired) are surfaced via VoiceStatusBadge; no extra text bubble.
                return
            }
        } catch {
            if (voiceMessageId) {
                updateVoiceMessage(voiceMessageId, { status: 'failed', errorMessage: 'Không tải được tin nhắn thoại.' })
            } else {
                setVoiceStatus('failed')
            }
            return
        }
        const delay = attempts < 3 ? 400 : attempts < 6 ? 800 : 1500
        await new Promise<void>((resolve) => {
            pollRef.current = window.setTimeout(resolve, delay)
        })
        return pollVoiceJob(ttsJobId, attempts + 1, voiceMessageId)
    }

    const applyTtsJob = (data: ChatApiData) => {
        const ttsJob = data.tts_job
        const jobId = ttsJob?.tts_job_id ? String(ttsJob.tts_job_id) : ''
        if (!jobId || playedVoiceJobsRef.current.has(jobId)) return
        playedVoiceJobsRef.current.add(jobId)

        const status = String(ttsJob?.status || 'queued')
        const audioUrl = typeof ttsJob?.audio_url === 'string' ? ttsJob.audio_url : null
        const voiceMessage: UiMessage = {
            id: `voice_${jobId}_${Date.now()}`,
            role: 'assistant',
            content: '',
            timestamp: Date.now(),
            voice: {
                ttsJobId: jobId,
                status: audioUrl ? 'ready' : status,
                audioUrl,
                errorMessage: null,
            },
        }
        setMessages((prev) => [...prev, voiceMessage])
        setVoiceStatus('')
        if (!audioUrl && !TTS_TERMINAL_STATUSES.has(status as TtsStatus)) {
            void pollVoiceJob(jobId, 0, voiceMessage.id)
        } else if (!audioUrl && status !== 'cooldown') {
            setVoiceStatus(status)
        }
    }

    const isActiveChatRequest = (requestId: number, requestSessionId: string | null, requestPersonaId: string) => {
        if (activeRequestIdRef.current !== requestId) return false
        if (activePersonaRef.current !== requestPersonaId) return false
        if (requestSessionId && activeSessionRef.current !== requestSessionId) return false
        return true
    }

    const consumeChatSse = async (
        response: Response,
        pendingId: string,
        requestId: number,
        requestSessionId: string | null,
        requestPersonaId: string,
    ) => {
        if (!response.ok) {
            throw new Error('Streaming chat thất bại')
        }
        const reader = response.body?.getReader()
        if (!reader) {
            throw new Error('Không có stream phản hồi')
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
                        if (!isActiveChatRequest(requestId, requestSessionId, requestPersonaId)) continue
                        streamedText += String(payload.text ?? '')
                        setMessages((prev) =>
                            prev.map((m) => (m.id === pendingId ? { ...m, content: streamedText || '...', isPending: false } : m)),
                        )
                    } else if (currentEvent === 'heartbeat') {
                        if (!isActiveChatRequest(requestId, requestSessionId, requestPersonaId)) continue
                        const stage = String(payload.stage ?? 'pre_llm')
                        const elapsedMs = Number(payload.elapsed_ms ?? 0)
                        setVoiceStatus(`Đang xử lý (${stage}) - ${elapsedMs}ms`)
                    } else if (currentEvent === 'status') {
                        if (!isActiveChatRequest(requestId, requestSessionId, requestPersonaId)) continue
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

        if (!isActiveChatRequest(requestId, requestSessionId, requestPersonaId)) return
        if (!finalData) {
            throw new Error(
                'Không nhận được dữ liệu cuối từ stream. Kết nối có thể bị ngắt, thử gửi lại; nếu đang chạy backend --reload, tránh sửa file khi đang stream.',
            )
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
                    ? { ...m, id: `a_${Date.now()}`, content: assistantText, apiData: finalData ?? undefined, isPending: false }
                    : m,
            ),
        )
        applyTtsJob(finalData)
    }

    const handleNewChat = async () => {
        if (endingSession) return
        activeRequestIdRef.current += 1
        sendingRef.current = false
        setSending(false)
        const currentSessionId = sessionId
        let openedMemoryTab = false
        if (user && !isGuestMode && currentSessionId && !currentSessionId.startsWith('gst_')) {
            setEndingSession(true)
            try {
                await chatService.endSession(currentSessionId)
                setMemoryRefreshKey((value) => value + 1)
                setActiveTab('memory')
                openedMemoryTab = true
            } catch (err) {
                toast.error(err instanceof Error ? err.message : 'Không chốt được phiên trò chuyện')
                return
            } finally {
                setEndingSession(false)
            }
        }
        setSessionId(null)
        setMessages([])
        if (!openedMemoryTab) setActiveTab('chat')
        playedVoiceJobsRef.current.clear()
        setPendingAudioUrl(null)
        setVoiceStatus('')
        localStorage.removeItem(chatSessionStorageKey(activePersonaId))
        localStorage.removeItem(LEGACY_CHAT_SESSION_KEY)
        if (user && !isGuestMode) {
            chatService.getGreeting(activePersonaId).then((res) => {
                setMessages([{
                    id: 'greeting-0',
                    role: 'assistant' as const,
                    content: res.text,
                    timestamp: Date.now(),
                }])
            }).catch(() => undefined)
        }
    }

    const doSend = async (text: string) => {
        if (sendingRef.current || endingSession) return
        if (isGuestMode && guestSecondsLeft <= 0) {
            toast.info('Phin chat th  ht. Mi bn ng k ti khon  tip tc.')
            navigate(ROUTE_PATHS.register)
            return
        }
        const now = Date.now()
        const requestId = now
        const requestSessionId = sessionId
        const requestPersonaId = activePersonaId
        const pendingId = `p_${now}`
        activeRequestIdRef.current = requestId
        sendingRef.current = true
        setInput('')
        setLastFailedText(null)
        setMessages((prev) => [
            ...prev,
            { id: `u_${now}`, role: 'user', content: text, timestamp: now },
            { id: pendingId, role: 'assistant', content: '', timestamp: now, isPending: true },
        ])
        setSending(true)

        try {
            if (!isGuestMode) {
                try {
                    const streamResponse = await chatService.sendMessageStream({ message: text, session_id: requestSessionId, persona_id: requestPersonaId })
                    await consumeChatSse(streamResponse, pendingId, requestId, requestSessionId, requestPersonaId)
                } catch (err) {
                    if (!isActiveChatRequest(requestId, requestSessionId, requestPersonaId)) return
                    const status = err instanceof ApiRequestError ? (err.status ?? 0) : 0
                    if (!(err instanceof ApiRequestError) || (status !== 0 && status < 500)) throw err
                    const rawData = await chatService.sendMessage({ message: text, session_id: requestSessionId, persona_id: requestPersonaId })
                    if (!isActiveChatRequest(requestId, requestSessionId, requestPersonaId)) return
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
                                ? { ...m, id: `a_${Date.now()}`, content: assistantText, apiData: data, isPending: false }
                                : m,
                        ),
                    )
                    applyTtsJob(data)
                    toast.info('Đường truyền stream đang lỗi, mình đã chuyển sang chế độ chat thường.')
                }
            } else {
                const rawData = await chatService.sendGuestMessage({ message: text, guest_session_id: requestSessionId })
                if (!isActiveChatRequest(requestId, requestSessionId, requestPersonaId)) return
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
                            ? { ...m, id: `a_${Date.now()}`, content: assistantText, apiData: data, isPending: false }
                            : m,
                    ),
                )
                applyTtsJob(data)
            }
        } catch (err) {
            if (!isActiveChatRequest(requestId, requestSessionId, requestPersonaId)) return
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
            if (activeRequestIdRef.current === requestId) {
                sendingRef.current = false
                setSending(false)
            }
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
        activeRequestIdRef.current += 1
        sendingRef.current = false
        setSending(false)
        setHotlineSheetOpen(false)
        try {
            const data = await chatService.getSessionMessages(targetSessionId, 100, 0)
            setSessionId(targetSessionId)
            setMessages(
                data.messages.map((msg) => ({
                    id: msg.message_id,
                    role: msg.role,
                    content: msg.content,
                    timestamp: msg.created_at ? new Date(msg.created_at).getTime() : undefined,
                })),
            )
            setShowHistory(false)
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Không tải được lịch sử hội thoại')
        }
    }

    useEffect(() => {
        if (sessionId && messages.length === 0 && !isGuestMode) {
            void loadSessionMessages(sessionId)
        }
    }, [sessionId, isGuestMode, messages.length])

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

    const toggleHeart = (messageId: string) => {
        setHeartedMessageIds((prev) => {
            const next = new Set(prev)
            if (next.has(messageId)) next.delete(messageId)
            else next.add(messageId)
            return next
        })
    }

    const openAttachment = (item: ResourceSuggestion) => {
        if (item.route) { navigate(item.route); return }
        if (item.action === 'open_connect_map' || item.type === 'clinic_map') { navigate(ROUTE_PATHS.support); return }
        if (item.action === 'open_resource' || item.type === 'resource') { navigate(ROUTE_PATHS.resources); return }
        if (item.type.includes('exercise') || item.type === 'body_scan') {
            navigate(`${ROUTE_PATHS.exercises}?exercise=${encodeURIComponent(item.id)}`)
            return
        }
        navigate(ROUTE_PATHS.resources)
    }

    const handleCrisisAction = (card: CrisisAction, data?: ChatApiData) => {
        switch (card.action) {
            case 'play_voice_grounding': {
                const audioUrl = data?.tts_job?.audio_url
                if (audioUrl) {
                    playAudioUrl(audioUrl)
                } else {
                    toast.info('Hướng dẫn thoại đang được chuẩn bị.')
                }
                return
            }
            case 'start_breathing_timer':
                setBreathingOpen(true)
                return
            case 'open_hotline_sheet':
                setHotlineSheetOpen(false)
                window.setTimeout(() => setHotlineSheetOpen(true), 0)
                return
            case 'open_clinic_map':
                navigate(ROUTE_PATHS.support)
                return
            case 'open_grounding_video':
                navigate(ROUTE_PATHS.exercises)
                return
            case 'continue_chat':
                setInput('')
                return
            default:
                return
        }
    }

    //  Render 
    return (
        <div className="w-full">
            <div className="relative flex h-[100dvh] min-h-[600px] flex-col overflow-hidden" style={{ background: '#070f0a' }}>

                {/*  Scene panel: pixel art background  */}
                <div
                    className="relative shrink-0 overflow-hidden resize-y"
                    style={{ height: '22vh', minHeight: '132px', maxHeight: '400px' }}
                >
                    <img
                        src={chatSceneBg}
                        alt=""
                        aria-hidden="true"
                        className="absolute inset-0 h-full w-full object-cover"
                        style={{ objectPosition: 'center 78%' }}
                    />
                    {/* Top shadow for header legibility */}
                    <div
                        aria-hidden="true"
                        className="pointer-events-none absolute inset-x-0 top-0"
                        style={{ height: '45%', background: 'linear-gradient(to bottom, rgba(4,10,6,0.55), transparent)' }}
                    />
                    {/* Bottom vignette: thin fade into dialogue panel */}
                    <div
                        aria-hidden="true"
                        className="pointer-events-none absolute inset-x-0 bottom-0"
                        style={{ height: '20%', background: 'linear-gradient(to bottom, transparent 0%, rgba(7,15,10,0.35) 45%, rgba(7,15,10,0.82) 88%, #070f0a 100%)' }}
                    />

                    {/*  Header HUD  */}
                    <div className="relative z-10 flex items-center justify-between px-4 py-2 sm:px-6">
                        <div className="flex items-center gap-2">
                            <div
                                className="flex h-10 w-10 shrink-0 items-center justify-center font-display text-xl font-bold text-[#f8c96b]"
                                style={{
                                    border: '2px solid rgba(248,201,107,0.55)',
                                    background: 'rgba(4,10,6,0.82)',
                                    backdropFilter: 'blur(6px)',
                                    boxShadow: '2px 2px 0 rgba(0,0,0,0.55)',
                                }}
                            >
                                S
                            </div>
                            <div>
                                {!isGuestMode && (
                                    <p
                                        className="mb-0.5 text-sm font-semibold uppercase tracking-[0.2em] text-[#f8c96b]/70"
                                        style={{ textShadow: '0 1px 6px rgba(0,0,0,0.9)' }}
                                    >
                                        {personaLabel}
                                    </p>
                                )}
                              
                                <p
                                    className="hidden text-sm font-medium font-sans tracking-[0.05em] text-[#fff4dc]/55 sm:block"
                                    style={{ textShadow: '0 1px 6px rgba(0,0,0,0.9)' }}
                                >
                                    Đang trò chuyện
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center gap-1.5" ref={optionsRef}>
                            {pendingAudioUrl ? (
                                <button
                                    type="button"
                                    onClick={() => {
                                        const url = pendingAudioUrl
                                        setPendingAudioUrl(null)
                                        playAudioUrl(url)
                                    }}
                                    className="flex cursor-pointer items-center gap-1 border border-[#f8c96b]/50 bg-[#040a06]/80 px-2 py-0.5 text-[10px] text-[#f8c96b] backdrop-blur-sm transition-colors hover:border-[#f8c96b]/80 hover:bg-[#1a1000]/90 active:scale-95"
                                    aria-label="Phát giọng đọc"
                                    title="Nhấn để nghe"
                                >
                                    <Play className="h-3 w-3 shrink-0" aria-hidden />
                                    <span>Nhấn để nghe</span>
                                </button>
                            ) : voiceStatus && (
                                <VoiceStatusBadge
                                    status={voiceStatus}
                                    className="border border-[#f8c96b]/30 bg-[#040a06]/80 px-2 py-0.5 text-[10px] text-[#f8c96b] backdrop-blur-sm"
                                />
                            )}
                            {isGuestMode && (
                                <span
                                    className="border border-[#f8c96b]/45 px-2 py-0.5 text-[10px] font-bold tracking-wide text-[#f8c96b]"
                                    style={{ background: 'rgba(4,10,6,0.78)', backdropFilter: 'blur(4px)' }}
                                >
                                    {guestCountdownLabel}
                                </span>
                            )}
                            <>
                                <button
                                    type="button"
                                    onClick={() => void handleNewChat()}
                                    disabled={endingSession}
                                    className="flex h-7 cursor-pointer items-center gap-1 px-2 text-[#fff4dc]/75 transition hover:text-[#fff4dc] disabled:cursor-wait disabled:opacity-60"
                                    style={{ background: 'rgba(4,10,6,0.65)', border: '1px solid rgba(255,244,220,0.14)', backdropFilter: 'blur(4px)' }}
                                    aria-label="Cuộc trò chuyện mới"
                                    title="Cuộc trò chuyện mới"
                                >
                                    <Plus className="h-3.5 w-3.5" />
                                    <span className="hidden text-[9px] font-semibold uppercase tracking-wide sm:inline">{endingSession ? 'Saving' : 'New'}</span>
                                </button>
                            </>
                            <button
                                type="button"
                                onClick={() => void openHistory()}
                                className="flex h-8 cursor-pointer items-center gap-1 px-2 text-[#fff4dc] transition"
                                style={{ background: 'rgba(4,10,6,0.65)', border: '1px solid rgba(255,244,220,0.14)', backdropFilter: 'blur(4px)' }}
                                aria-label="Lịch sử chat"
                            >
                                <History className="h-3.5 w-3.5" />
                                <span className="hidden text-xs font-semibold uppercase tracking-wide sm:inline">History</span>
                            </button>
                            <div className="relative">
                                <button
                                    type="button"
                                    onClick={() => setShowOptions((prev) => !prev)}
                                    data-tour-id="chat-persona-options"
                                    className="flex h-8 w-8 cursor-pointer items-center justify-center text-[#fff4dc] transition"
                                    style={{ background: 'rgba(4,10,6,0.65)', border: '1px solid rgba(255,244,220,0.14)', backdropFilter: 'blur(4px)' }}
                                    aria-label="Tùy chọn"
                                >
                                    <MoreVertical className="h-3.5 w-3.5" />
                                </button>
                                {showOptions && (
                                    <div
                                        className="absolute right-0 top-10 z-50 w-80 border border-[#3a6040]/55 p-3 shadow-2xl"
                                        style={{ background: 'rgba(6,14,9,0.97)', backdropFilter: 'blur(12px)' }}
                                    >
                                        <p className="mb-3 text-xs uppercase tracking-[0.28em] text-[#fff4dc]/75">Tùy chọn</p>
                                        <div className="space-y-2">
                                            {!isGuestMode && (
                                                <div className="border border-[#3a6040]/30 bg-white/[0.04] px-3 py-2.5">
                                                    <p className="mb-2 text-sm font-semibold text-[#fff4dc]">Chọn nhân vật</p>
                                                    <PersonaSelector
                                                        onSelect={(personaId) => {
                                                            const switchPersona = async () => {
                                                                activeRequestIdRef.current += 1
                                                                sendingRef.current = false
                                                                setSending(false)
                                                                const currentSessionId = sessionId
                                                                if (user && !isGuestMode && currentSessionId && !currentSessionId.startsWith('gst_')) {
                                                                    setEndingSession(true)
                                                                    try {
                                                                        await chatService.endSession(currentSessionId)
                                                                        setMemoryRefreshKey((value) => value + 1)
                                                                    } catch (err) {
                                                                        toast.error(err instanceof Error ? err.message : 'Không chốt được phiên trò chuyện')
                                                                        return
                                                                    } finally {
                                                                        setEndingSession(false)
                                                                    }
                                                                }
                                                                setActivePersonaId(personaId)
                                                                setSessionId(null)
                                                                setMessages([])
                                                                localStorage.removeItem(chatSessionStorageKey(activePersonaId))
                                                                localStorage.removeItem(LEGACY_CHAT_SESSION_KEY)
                                                                setShowOptions(false)
                                                            }
                                                            void switchPersona()
                                                        }}
                                                    />
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
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

                {/*  Dialogue panel  */}
                <div
                    className="relative flex min-h-0 flex-1 flex-col"
                    style={{ background: '#070f0a' }}
                >
                    {/* Gradient top border line */}
                    <div
                        aria-hidden="true"
                        className="pointer-events-none absolute inset-x-0 top-0 h-px"
                        style={{ background: 'linear-gradient(90deg, transparent 0%, #4a7a50 20%, #6aaa70 50%, #4a7a50 80%, transparent 100%)' }}
                    />
                    {/* Gold corner brackets */}
                    <div aria-hidden="true" className="pointer-events-none absolute left-5 top-0 h-3.5 w-3.5 border-l-2 border-t-2 border-[#f8c96b]/35" />
                    <div aria-hidden="true" className="pointer-events-none absolute right-5 top-0 h-3.5 w-3.5 border-r-2 border-t-2 border-[#f8c96b]/35" />

                    {/*  Tab bar  */}
                    {!isGuestMode && (
                        <div
                            className="flex shrink-0 gap-0 px-5 pt-2 sm:px-7"
                            style={{ borderBottom: '1px solid rgba(58,96,64,0.35)' }}
                        >
                            {(['chat', 'memory'] as const).map((tab) => (
                                <button
                                    key={tab}
                                    type="button"
                                    onClick={() => {
                                        setActiveTab(tab)
                                        if (tab === 'memory') setMemoryRefreshKey((value) => value + 1)
                                    }}
                                    data-tour-id={tab === 'memory' ? 'chat-memory-tab' : undefined}
                                    className={[
                                        'px-4 py-2 text-[10px] font-bold tracking-[0.22em] uppercase transition-colors',
                                        activeTab === tab
                                            ? 'border-b-2 border-[#f8c96b] text-[#f8c96b]'
                                            : 'text-[#fff4dc]/30/60',
                                    ].join(' ')}
                                >
                                    {tab === 'chat' ? 'Chat' : 'Ký ức'}
                                </button>
                            ))}
                        </div>
                    )}

                    {/*  Tab content  */}
                    {activeTab === 'memory' ? (
                        <div className="m-4 flex-1 overflow-y-auto border border-[#3a6040]/50 bg-[#fff4dc]/88 p-4 sm:m-5">
                            <UserMemoriesTab refreshKey={memoryRefreshKey} />
                        </div>
                    ) : (
                        <div className="flex-1 overflow-y-auto px-5 py-4 sm:px-7">
                            <div className="flex flex-col gap-5">
                                {messages.length === 0 ? (
                                    guestSessionLoading ? (
                                        <Loading />
                                    ) : (
                                        <div className="mx-auto mt-2 flex max-w-sm flex-col items-center border border-[#3a6040]/50 bg-[#0b1810]/80 px-6 py-7 text-center">
                                            <div className="mb-3 flex h-9 w-9 items-center justify-center border border-[#f8c96b]/35 bg-[#040a06] text-[#f8c96b]">
                                                <Leaf className="h-4 w-4" aria-hidden />
                                            </div>
                                            <h2 className="font-display text-xl font-semibold text-[#fff4dc]">
                                                {isGuestMode ? 'Serene đang lắng nghe' : `${personaLabel} đang lắng nghe`}
                                            </h2>
                                            <p className="mt-2 text-sm leading-relaxed text-[#fff4dc]/50">
                                                Bạn có thể bắt đầu bằng một câu ngắn về cảm giác hiện tại.
                                            </p>
                                        </div>
                                    )
                                ) : (
                                    messages.map((m, idx) => {
                                        const isAI = m.role === 'assistant'
                                        const suppressInlineCrisisCards = m.apiData?.distress_ui?.suppress_inline_crisis_cards === true
                                        const prev = messages[idx - 1]
                                        const showDivider =
                                            m.timestamp != null &&
                                            !isNaN(m.timestamp) &&
                                            (prev == null ||
                                                prev.timestamp == null ||
                                                isNaN(prev.timestamp) ||
                                                new Date(prev.timestamp).toDateString() !== new Date(m.timestamp).toDateString())
                                        return (
                                            <div key={m.id}>
                                                {showDivider && m.timestamp != null && <DateDivider timestamp={m.timestamp} />}
                                                <div className={`flex flex-col gap-1.5 ${isAI ? 'items-start' : 'items-end'}`}>
                                                    {/* Character nameplate */}
                                                    <span
                                                        className={`text-[9px] font-bold tracking-[0.28em] uppercase ${
                                                            isAI ? 'text-[#f8c96b]/70' : 'text-[#6fc7df]/70'
                                                        }`}
                                                    >
                                                        {isAI ? ` ${isGuestMode ? 'SERENE' : personaLabel}` : 'BẠN '}
                                                    </span>
                                                    {/* Message container */}
                                                    <div className="flex max-w-[78%] flex-col gap-2 sm:max-w-[68%]">
                                                        {isAI && m.isPending ? (
                                                            <TypingIndicator visible />
                                                        ) : m.voice ? (
                                                            <VoiceMessageBubble voice={m.voice} onPlay={playAudioUrl} />
                                                        ) : (
                                                            <article
                                                                className={[
                                                                    'whitespace-pre-line px-4 py-3 text-sm leading-relaxed',
                                                                    isAI
                                                                        ? m.apiData?.sos_triggered
                                                                            ? 'border border-red-400/55 bg-[#fff0ec]/96 text-red-900 shadow-[3px_3px_0_rgba(0,0,0,0.38)]'
                                                                            : 'border border-[#8a6a3f]/50 bg-[#fff4dc]/96 text-[#1a1008] shadow-[3px_3px_0_rgba(0,0,0,0.38)]'
                                                                        : 'border border-[#3a6040]/60 bg-[#0b1e14]/90 text-[#b8dfc8] shadow-[3px_3px_0_rgba(0,0,0,0.38)]',
                                                                ].join(' ')}
                                                            >
                                                                {m.content}
                                                            </article>
                                                        )}
                                                        <button
                                                            type="button"
                                                            onClick={() => toggleHeart(m.id)}
                                                            className={`inline-flex w-fit items-center justify-center rounded-md border p-1.5 transition ${
                                                                heartedMessageIds.has(m.id)
                                                                    ? 'border-[#f08a93]/60 bg-[#3a1e26]/70 text-[#ffc3c9]'
                                                                    : 'border-[#fff4dc]/20 bg-[#070f0a]/55 text-[#fff4dc]/60'
                                                            }`}
                                                            aria-label={heartedMessageIds.has(m.id) ? 'Bỏ tim tin nhắn' : 'Thả tim tin nhắn'}
                                                        >
                                                            <Heart
                                                                className="h-3.5 w-3.5"
                                                                fill={heartedMessageIds.has(m.id) ? 'currentColor' : 'none'}
                                                            />
                                                        </button>
                                                        {m.apiData?.sos_triggered &&
                                                            !suppressInlineCrisisCards &&
                                                            m.apiData.crisis_plan && (
                                                                <CrisisStepper
                                                                    crisisPlan={m.apiData.crisis_plan}
                                                                    onAction={(card) => handleCrisisAction(card, m.apiData)}
                                                                />
                                                            )}
                                                        {m.apiData?.sos_triggered &&
                                                            !suppressInlineCrisisCards &&
                                                            (m.apiData.crisis_plan?.follow_up_texts ?? []).map((msg, i) => (
                                                                <div
                                                                    key={`followup-${i}`}
                                                                    className="border border-[#8a6a3f]/50 bg-[#fff4dc]/96 px-4 py-3 text-sm leading-relaxed text-[#1a1008] shadow-[3px_3px_0_rgba(0,0,0,0.38)]"
                                                                >
                                                                    {msg}
                                                                </div>
                                                            ))}
                                                        {m.apiData?.resource_suggestions?.map((item, i) => (
                                                            <AttachmentCard key={`${item.type}-${item.id}-${i}`} item={item} onOpen={openAttachment} />
                                                        ))}
                                                        {m.apiData?.meme_suggestion ? <MemeCard item={m.apiData.meme_suggestion} /> : null}
                                                    </div>
                                                </div>
                                            </div>
                                        )
                                    })
                                )}
                                <div ref={bottomRef} />
                            </div>
                        </div>
                    )}

                    {/*  Retry notice  */}
                    {lastFailedText && (
                        <div
                            className="flex shrink-0 items-center gap-3 border-t border-red-900/40 px-5 py-2 text-sm text-red-400 sm:px-7"
                            style={{ background: 'rgba(16,4,4,0.96)' }}
                        >
                            <span>Tin nhắn trước gửi lỗi.</span>
                            <button
                                type="button"
                                onClick={handleRetry}
                                className="font-medium underline underline-offset-4 transition hover:text-red-300"
                            >
                                Thử lại
                            </button>
                        </div>
                    )}

                    {/*  Input bar  */}
                    <form
                        onSubmit={handleSend}
                        className="shrink-0 px-5 py-3 sm:px-7"
                        style={{ borderTop: '1px solid rgba(58,96,64,0.42)', background: 'rgba(3,7,5,0.98)' }}
                    >
                        <div className="flex items-center gap-3">
                            <span className="hidden font-mono text-sm text-[#3a6040]/65 sm:inline" aria-hidden="true">
                                &gt;&gt;
                            </span>
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                disabled={isGuestMode && guestSecondsLeft <= 0}
                                data-tour-id="chat-input"
                                placeholder="Chia sẻ điều bạn đang cảm thấy..."
                                className="flex-1 border-0 bg-transparent px-2 py-1.5 text-sm text-[#b8dfc8] placeholder:text-[#fff4dc]/20 focus:outline-none"
                            />
                            <button
                                type="submit"
                                disabled={!canSend}
                                className="flex h-8 shrink-0 items-center justify-center px-5 text-[11px] font-bold uppercase tracking-[0.1em] text-[#c8f0d8] transition disabled:cursor-not-allowed disabled:opacity-30"
                                style={{
                                    background: '#2d5535',
                                    border: '2px solid rgba(106,170,112,0.42)',
                                    boxShadow: '2px 2px 0 rgba(0,0,0,0.5)',
                                }}
                                aria-label="Gửi tin nhắn"
                            >
                                <span className="hidden sm:inline">SEND</span>
                                <Send className="h-4 w-4 sm:hidden" />
                            </button>
                        </div>
                    </form>
                </div>
            </div>
            {activeDistressPopup && (
                <DatLeSosPopup
                    popup={activeDistressPopup}
                    onNavigate={(route) => {
                        if (route.startsWith('/serene/')) navigate(route)
                    }}
                    onDismiss={(popupId) => {
                        dismissDistressPopup(popupId)
                        setActiveDistressPopup(null)
                    }}
                />
            )}
            <BreathingTimer open={breathingOpen} onClose={() => setBreathingOpen(false)} />
            <HotlineBar visible={hotlineSheetOpen} />
        </div>
    )
}
