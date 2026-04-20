import { useEffect, useMemo, useRef, useState } from 'react'
import type { ComponentProps } from 'react'
import { toast } from 'react-toastify'
import { resolveMediaUrl } from '../../api/httpClient'
import { chatService } from '../../services/chatService'
import { policyService } from '../../services/policyService'

type UiMessage = {
    id: string
    role: 'user' | 'assistant'
    content: string
}

type ProactiveVoice = {
    type: string
    voice?: {
        status?: string
        tts_job_id?: string | null
        audio_url?: string | null
    }
    voice_script?: string
    copy_ngan?: string
    next_actions?: Array<{ id: string; label: string }>
}

export default function Chat() {
    type FormSubmitHandler = NonNullable<ComponentProps<'form'>['onSubmit']>

    const [sessionId, setSessionId] = useState<string | null>(null)
    const [messages, setMessages] = useState<UiMessage[]>([])
    const [input, setInput] = useState('')
    const [sending, setSending] = useState(false)
    const [voiceConsent, setVoiceConsent] = useState(false)
    const [voiceStatus, setVoiceStatus] = useState('')
    const [lastFailedText, setLastFailedText] = useState<string | null>(null)
    const pollRef = useRef<number | null>(null)

    useEffect(() => {
        policyService
            .getVoiceConsent()
            .then((res) => setVoiceConsent(Boolean(res.voice_consent)))
            .catch(() => undefined)
    }, [])

    useEffect(() => {
        return () => {
            if (pollRef.current) window.clearTimeout(pollRef.current)
        }
    }, [])

    const canSend = useMemo(() => !sending && input.trim().length > 0, [sending, input])

    const playAudioUrl = (audioUrl: string) => {
        const audio = new Audio(resolveMediaUrl(audioUrl))
        void audio.play().catch(() => {
            toast.info('Trình duyệt chặn tự phát audio, hãy bấm play thủ công.')
        })
    }

    const pollVoiceJob = async (ttsJobId: string, attempts = 0) => {
        if (attempts > 10) return
        try {
            const job = await chatService.getVoiceJob(ttsJobId)
            setVoiceStatus(`Voice: ${job.status}`)
            if (job.status === 'ready' && job.audio_url) {
                playAudioUrl(job.audio_url)
                return
            }
            if (job.status === 'failed') {
                setVoiceStatus('Voice lỗi, chuyển về text.')
                return
            }
        } catch {
            return
        }
        pollRef.current = window.setTimeout(() => {
            void pollVoiceJob(ttsJobId, attempts + 1)
        }, 2000)
    }

    const handleSend: FormSubmitHandler = async (event) => {
        event.preventDefault()
        if (!canSend) return

        const text = input.trim()
        setInput('')
        setLastFailedText(null)
        setMessages((prev) => [...prev, { id: `u_${Date.now()}`, role: 'user', content: text }])
        setSending(true)

        try {
            const data = await chatService.sendMessage({ message: text, session_id: sessionId })
            const sid = typeof data.session_id === 'string' ? data.session_id : null
            if (sid) setSessionId(sid)

            const assistantText =
                typeof data.reply === 'string' && data.reply
                    ? data.reply
                    : typeof data.assistant_text === 'string'
                      ? data.assistant_text
                      : 'Mình vẫn đang ở đây cùng bạn.'

            setMessages((prev) => [...prev, { id: `a_${Date.now()}`, role: 'assistant', content: assistantText }])

            const intervention = data.intervention as ProactiveVoice | null | undefined
            if (intervention?.type === 'proactive_voice') {
                if (intervention.copy_ngan) {
                    setMessages((prev) => [...prev, { id: `i_${Date.now()}`, role: 'assistant', content: intervention.copy_ngan || '' }])
                }
                if (Array.isArray(intervention.next_actions) && intervention.next_actions.length > 0) {
                    const labels = intervention.next_actions.map((a) => `• ${a.label}`).join('\n')
                    setMessages((prev) => [
                        ...prev,
                        { id: `na_${Date.now()}`, role: 'assistant', content: `Gợi ý tiếp theo:\n${labels}` },
                    ])
                }
                const ttsJobId = intervention.voice?.tts_job_id
                const audioUrl = intervention.voice?.audio_url
                if (audioUrl) {
                    playAudioUrl(audioUrl)
                } else if (ttsJobId) {
                    setVoiceStatus('Đang tạo voice...')
                    void pollVoiceJob(ttsJobId)
                } else if (intervention.voice_script) {
                    setMessages((prev) => [...prev, { id: `vs_${Date.now()}`, role: 'assistant', content: intervention.voice_script || '' }])
                }
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Gửi tin nhắn thất bại'
            toast.error(errorMessage)
            setLastFailedText(text)
            setMessages((prev) => [
                ...prev,
                { id: `e_${Date.now()}`, role: 'assistant', content: 'Mình bị gián đoạn một chút, bạn thử lại giúp mình nhé.' },
            ])
        } finally {
            setSending(false)
        }
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

    return (
        <section className="space-y-4">
            <div className="rounded-3xl border border-white/35 bg-white/60 p-5 backdrop-blur-xl">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 className="font-display text-4xl text-serene-ink">Trò chuyện</h2>
                    <button
                        type="button"
                        onClick={handleToggleVoiceConsent}
                        className="rounded-full bg-serene-primary px-4 py-2 text-sm text-white"
                    >
                        Voice hỗ trợ: {voiceConsent ? 'BẬT' : 'TẮT'}
                    </button>
                </div>
                {voiceStatus ? <p className="mt-2 text-xs text-serene-muted">{voiceStatus}</p> : null}
            </div>

            <div className="h-[420px] overflow-y-auto rounded-3xl border border-white/35 bg-white/65 p-4 backdrop-blur-xl">
                {messages.length === 0 ? (
                    <p className="text-serene-muted">Hãy bắt đầu cuộc trò chuyện. Mình đang lắng nghe bạn.</p>
                ) : (
                    <div className="space-y-3">
                        {messages.map((m) => (
                            <article
                                key={m.id}
                                className={[
                                    'max-w-[85%] rounded-2xl px-4 py-3 text-sm whitespace-pre-line',
                                    m.role === 'user' ? 'ml-auto bg-serene-primary text-white' : 'bg-white text-serene-ink',
                                ].join(' ')}
                            >
                                {m.content}
                            </article>
                        ))}
                    </div>
                )}
            </div>

            <form onSubmit={handleSend} className="flex gap-3 rounded-3xl border border-white/35 bg-white/70 p-3 backdrop-blur-xl">
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
