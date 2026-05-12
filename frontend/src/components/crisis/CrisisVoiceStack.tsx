import { useEffect, useMemo, useState } from 'react'
import { Play } from 'lucide-react'
import { chatService } from '../../services/chatService'
import VoiceStatusBadge, { TTS_TERMINAL_STATUSES, type TtsStatus } from '../pages/chat/VoiceStatusBadge'

export type CrisisVoiceMessage = {
    id: string
    intent: string
    title: string
    status: TtsStatus | string
    tts_job_id?: string | null
    audio_url?: string | null
    error_code?: string | null
}

type Props = {
    voiceMessages?: CrisisVoiceMessage[]
    onPlay: (audioUrl: string) => void
}

export function CrisisVoiceStack({ voiceMessages, onPlay }: Props) {
    const [patches, setPatches] = useState<Record<string, Partial<CrisisVoiceMessage>>>({})
    const cards = useMemo(
        () => (voiceMessages ?? []).map((card) => ({ ...card, ...(patches[card.id] ?? {}) })),
        [patches, voiceMessages],
    )

    useEffect(() => {
        const timers: number[] = []
        let cancelled = false

        const patchCard = (id: string, patch: Partial<CrisisVoiceMessage>) => {
            if (cancelled) return
            setPatches((prev) => ({ ...prev, [id]: { ...(prev[id] ?? {}), ...patch } }))
        }

        const poll = async (card: CrisisVoiceMessage, attempt = 0): Promise<void> => {
            if (!card.tts_job_id || TTS_TERMINAL_STATUSES.has(card.status as TtsStatus) || attempt > 20) return
            try {
                const job = await chatService.getVoiceJob(card.tts_job_id)
                const nextAudio = job.audio_data_uri || job.audio_url || card.audio_url || null
                patchCard(card.id, {
                    status: job.status,
                    audio_url: nextAudio,
                    error_code: job.error_code || null,
                })
                if (TTS_TERMINAL_STATUSES.has(job.status as TtsStatus)) return
            } catch {
                patchCard(card.id, { status: 'failed', error_code: 'voice_poll_failed' })
                return
            }
            const delay = attempt < 3 ? 500 : attempt < 6 ? 900 : 1500
            await new Promise<void>((resolve) => {
                timers.push(window.setTimeout(resolve, delay))
            })
            return poll({ ...card, status: 'processing' }, attempt + 1)
        }

        for (const card of voiceMessages ?? []) {
            if (card.tts_job_id && !TTS_TERMINAL_STATUSES.has(card.status as TtsStatus)) {
                void poll(card)
            }
        }

        return () => {
            cancelled = true
            timers.forEach((timer) => window.clearTimeout(timer))
        }
    }, [voiceMessages])

    if (!cards.length) return null

    const bars = [14, 22, 30, 18, 36, 28, 40, 24, 34, 26]

    return (
        <section className="mt-2 flex w-full max-w-[360px] flex-col gap-2" aria-label="Tin nhan thoai Serene">
            {cards.map((card, index) => {
                const playable = (card.status === 'ready' || card.status === 'cache_hit' || card.status === 'skipped_duplicate') && Boolean(card.audio_url)
                const failed = card.status === 'failed' || card.status === 'provider_disabled' || card.status === 'cancelled'
                return (
                    <article
                        key={card.id}
                        className="grid grid-cols-[40px_1fr] gap-3 border border-[#8a6a3f]/50 bg-[#fff4dc]/96 px-3 py-2.5 text-[#1a1008] shadow-[3px_3px_0_rgba(0,0,0,0.38)]"
                    >
                        <button
                            type="button"
                            disabled={!playable || !card.audio_url}
                            onClick={() => card.audio_url && onPlay(card.audio_url)}
                            className="flex h-10 w-10 shrink-0 items-center justify-center border border-[#1a1008]/25 bg-[#1a1008] text-[#fff4dc] transition enabled:hover:bg-[#2c1a0d] disabled:cursor-not-allowed disabled:opacity-35"
                            aria-label={playable ? 'Phat tin nhan thoai' : 'Tin nhan thoai chua san sang'}
                            title={playable ? 'Phat tin nhan thoai' : 'Tin nhan thoai chua san sang'}
                        >
                            <Play className="h-5 w-5 translate-x-0.5" aria-hidden />
                        </button>
                        <div className="min-w-0">
                            <div className="flex items-center justify-between gap-2">
                                <p className="truncate text-xs font-bold uppercase tracking-wide text-[#1a1008]/70">
                                    {index + 1}. {card.title || 'Tin nhan thoai'}
                                </p>
                                <VoiceStatusBadge status={card.status} className="shrink-0" />
                            </div>
                            <div className="mt-1 flex h-8 items-center gap-1" aria-hidden="true">
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
                        </div>
                    </article>
                )
            })}
        </section>
    )
}
