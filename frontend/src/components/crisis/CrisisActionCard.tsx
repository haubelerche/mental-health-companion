import { Headphones, LifeBuoy, MessageCircle, Navigation, Play, Timer, Video } from 'lucide-react'

export type CrisisAction = {
    id: string
    type: 'voice_grounding' | 'breathing_timer' | 'trusted_contact' | 'hotline' | 'clinic_map' | 'video_grounding' | 'continue_chat'
    title: string
    description: string
    action: string
    route?: string | null
    priority: number
}

const ICONS: Record<CrisisAction['type'], typeof Play> = {
    voice_grounding: Headphones,
    breathing_timer: Timer,
    trusted_contact: LifeBuoy,
    hotline: LifeBuoy,
    clinic_map: Navigation,
    video_grounding: Video,
    continue_chat: MessageCircle,
}

export function CrisisActionCard({ card, onAction }: { card: CrisisAction; onAction: (card: CrisisAction) => void }) {
    const Icon = ICONS[card.type] ?? LifeBuoy
    return (
        <button
            type="button"
            onClick={() => onAction(card)}
            className="flex min-h-[72px] w-full items-start gap-3 border border-[#8a6a3f]/45 bg-[#fff4dc]/92 px-3 py-3 text-left text-[#1a1008] transition hover:bg-[#fff8e8] focus:outline-none focus:ring-2 focus:ring-[#f8c96b]/70"
        >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center border border-[#1a1008]/20 bg-[#1a1008] text-[#fff4dc]">
                <Icon className="h-4 w-4" aria-hidden />
            </span>
            <span className="min-w-0">
                <span className="block text-sm font-semibold leading-snug">{card.title}</span>
                <span className="mt-1 block text-xs leading-relaxed text-[#1a1008]/68">{card.description}</span>
            </span>
        </button>
    )
}
