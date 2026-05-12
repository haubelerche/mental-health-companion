import { X } from 'lucide-react'
import datLe from '../../assets/assistants/dat-le.png'

export type AppNotification = {
    id: string
    title: string
    body: string
    created_at: string
    severity?: 'info' | 'success' | 'warning'
    route?: string
}

type RealtimeNotificationAssistantProps = {
    notifications: AppNotification[]
    onOpenNotificationCenter?: () => void
    onDismiss?: (notificationId: string) => void
}

function safeText(value: string): string {
    return value.replace(/\b(phq|gad|risk_score|clinical|analyst|crisis_level)\b/gi, '').trim()
}

export default function RealtimeNotificationAssistant({
    notifications,
    onOpenNotificationCenter,
    onDismiss,
}: RealtimeNotificationAssistantProps) {
    const latest = notifications[0]
    if (!latest) return null

    const speakerLock = document.body.dataset.personaSpeakerLock
    if (speakerLock && speakerLock !== 'dat_le') return null

    return (
        <aside className="fixed bottom-8 left-5 z-[10001] w-[min(460px,calc(100vw-24px))] pt-28 text-[#3d2b1b] md:left-7">
            <img
                src={datLe}
                alt="Dat Le"
                className="pointer-events-none absolute left-4 top-0 h-36 w-36 translate-y-5 object-contain"
                style={{ imageRendering: 'pixelated' }}
            />
            <div className="relative">
                <div className="relative z-20 ml-28 inline-flex border-[4px] border-[#5c3b24] bg-[#8a6040] px-6 py-2 text-base font-black text-[#fff6d5] shadow-[4px_4px_0_rgba(55,38,20,0.28)]">
                    Dat Le
                </div>
                <div className="relative z-10 -mt-1 border-4 border-[#6b4b2a] bg-[#f8e7b8] p-5 shadow-[0_7px_0_rgba(55,38,20,0.35)]">
                    <button
                        type="button"
                        onClick={() => onDismiss?.(latest.id)}
                        className="absolute right-3 top-3 inline-flex h-9 w-9 items-center justify-center border-2 border-[#6b4b2a] bg-[#fff6d5] text-[#5c3b24] transition hover:bg-[#f2d89e]"
                        aria-label="Đóng thông báo"
                    >
                        <X className="h-4 w-4" />
                    </button>
                    <p className="pr-10 text-sm font-black leading-snug">{safeText(latest.title) || 'Thông báo mới'}</p>
                    <p className="mt-2 pr-10 text-xs font-bold leading-relaxed text-[#5f5140]">
                        {safeText(latest.body)}
                    </p>
                    <div className="mt-4 flex justify-end gap-2">
                        <button
                            type="button"
                            onClick={() => onDismiss?.(latest.id)}
                            className="border-2 border-[#7c5936] bg-[#fff6d5] px-3 py-1.5 text-xs font-black text-[#6b4b2a]"
                        >
                            Đóng
                        </button>
                        <button
                            type="button"
                            onClick={onOpenNotificationCenter}
                            className="border-2 border-[#4f3320] bg-[#8a6040] px-3 py-1.5 text-xs font-black text-[#fff6d5]"
                        >
                            Xem
                        </button>
                    </div>
                </div>
            </div>
        </aside>
    )
}
