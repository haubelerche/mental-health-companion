import { useEffect, useMemo, useRef, useState } from 'react'
import type { ComponentProps } from 'react'
import { toast } from 'react-toastify'
import { api } from '../../lib/api'

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
  cooldown?: {
    active?: boolean
    seconds_remaining?: number
  }
}

export default function Chat() {
  type FormSubmitHandler = NonNullable<ComponentProps<'form'>['onSubmit']>
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<UiMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [voiceConsent, setVoiceConsent] = useState<boolean>(false)
  const [voiceStatus, setVoiceStatus] = useState<string>('')
  const pollRef = useRef<number | null>(null)

  useEffect(() => {
    api.getVoiceConsent()
      .then((res) => setVoiceConsent(Boolean(res.voice_consent)))
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearTimeout(pollRef.current)
    }
  }, [])

  const canSend = useMemo(() => !sending && input.trim().length > 0, [sending, input])

  const pollVoiceJob = async (ttsJobId: string, attempts = 0) => {
    if (attempts > 8) return
    try {
      const job = await api.getVoiceJob(ttsJobId)
      setVoiceStatus(`Voice job: ${job.status}`)
      if (job.status === 'ready' && job.audio_url) {
        const audio = new Audio(`${(import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://127.0.0.1:8000'}${job.audio_url}`)
        void audio.play().catch(() => {
          toast.info('Trình duyệt chặn autoplay, hãy bấm play thủ công.')
        })
        return
      }
      if (job.status === 'failed') return
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
    setMessages((prev) => [...prev, { id: `u_${Date.now()}`, role: 'user', content: text }])
    setSending(true)

    try {
      const data = await api.sendMessage({ message: text, session_id: sessionId })
      const sid = typeof data.session_id === 'string' ? data.session_id : null
      if (sid) setSessionId(sid)

      const assistantText = typeof data.reply === 'string' && data.reply
        ? data.reply
        : (typeof data.assistant_text === 'string' ? data.assistant_text : 'Mình vẫn đang ở đây cùng cậu.')
      setMessages((prev) => [...prev, { id: `a_${Date.now()}`, role: 'assistant', content: assistantText }])

      const intervention = data.intervention as ProactiveVoice | null | undefined
      if (intervention?.type === 'proactive_voice') {
        const short = intervention.copy_ngan ?? 'Mình gửi một lời nhắn thoại ngắn cho cậu.'
        setMessages((prev) => [...prev, { id: `i_${Date.now()}`, role: 'assistant', content: short }])

        const audioUrl = intervention.voice?.audio_url
        const ttsJobId = intervention.voice?.tts_job_id
        if (audioUrl) {
          const audio = new Audio(`${(import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://127.0.0.1:8000'}${audioUrl}`)
          void audio.play().catch(() => toast.info('Trình duyệt chặn autoplay, hãy bấm play thủ công.'))
        } else if (ttsJobId) {
          setVoiceStatus('Voice đang được tạo...')
          void pollVoiceJob(ttsJobId)
        } else {
          const voiceScript = intervention.voice_script ?? ''
          if (voiceScript) {
            setMessages((prev) => [...prev, { id: `f_${Date.now()}`, role: 'assistant', content: voiceScript }])
          }
        }
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Gửi tin nhắn thất bại')
      setMessages((prev) => [...prev, { id: `e_${Date.now()}`, role: 'assistant', content: 'Mình bị gián đoạn một chút, cậu thử gửi lại giúp mình nhé.' }])
    } finally {
      setSending(false)
    }
  }

  const handleToggleVoiceConsent = async () => {
    const next = !voiceConsent
    try {
      const res = await api.setVoiceConsent(next)
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
            Voice hỗ trợ: {voiceConsent ? 'ON' : 'OFF'}
          </button>
        </div>
        {voiceStatus ? <p className="mt-2 text-xs text-serene-muted">{voiceStatus}</p> : null}
      </div>

      <div className="h-[420px] overflow-y-auto rounded-3xl border border-white/35 bg-white/65 p-4 backdrop-blur-xl">
        {messages.length === 0 ? (
          <p className="text-serene-muted">Hãy bắt đầu cuộc trò chuyện. Mình đang lắng nghe cậu.</p>
        ) : (
          <div className="space-y-3">
            {messages.map((m) => (
              <article
                key={m.id}
                className={[
                  'max-w-[85%] rounded-2xl px-4 py-3 text-sm',
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
          placeholder="Chia sẻ điều cậu đang cảm thấy..."
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
    </section>
  )
}