import { LifeBuoy, Wind, X } from 'lucide-react'
import datLeShockSos from '../../assets/assistants/dat-le-shock-sos.png'

export type DistressMessageSegment =
    | { type: 'text'; text?: string | null }
    | { type: 'line_break' }
    | { type: 'route_link'; text?: string | null; route?: string | null }

export type DistressSupportPopup = {
    show: boolean
    popup_id?: string | null
    character_id: 'dat_le'
    character_label: string
    asset_path: string
    title: string
    message_html?: string | null
    message_segments?: DistressMessageSegment[]
    support_route: string
    breathing_exercise_route: string
    cooldown_seconds: number
    reason?: string | null
}

type Props = {
    popup: DistressSupportPopup
    onNavigate: (route: string) => void
    onDismiss: (popupId?: string | null) => void
}

function renderSegments(
    popup: DistressSupportPopup,
    onNavigate: (route: string) => void,
) {
    const segments = Array.isArray(popup.message_segments) ? popup.message_segments : []
    if (segments.length === 0) {
        return (
            <>
                Bình tĩnh nào bạn ơi, cái gì cũng có cách giải quyết của nó mà. Nếu cần hỗ trợ của một người có chuyên môn thật sự, bạn hãy mở trang "Hỗ trợ" ngay hoặc thử{' '}
                <button
                    type="button"
                    className="font-bold text-[#174c63] underline underline-offset-2"
                    onClick={() => onNavigate(popup.breathing_exercise_route)}
                >
                    bài tập thở khi lo âu
                </button>{' '}
                này ngay nhé!
                <br />
                Nhớ rằng chúng mình luôn ở đây khi bạn cần và hãy cho bản thân phép bản thân dám hy vọng, dám đương đầu với khó khăn. Vì không bóng tối nào là mãi mãi...
            </>
        )
    }

    return segments.map((segment, index) => {
        if (segment.type === 'line_break') return <br key={`br-${index}`} />
        if (segment.type === 'route_link') {
            const route = typeof segment.route === 'string' && segment.route.startsWith('/serene/')
                ? segment.route
                : popup.breathing_exercise_route
            return (
                <button
                    key={`link-${index}`}
                    type="button"
                    className="font-bold text-[#174c63] underline underline-offset-2"
                    onClick={() => onNavigate(route)}
                >
                    {segment.text || 'bài tập thở khi lo âu'}
                </button>
            )
        }
        return <span key={`text-${index}`}>{segment.text || ''}</span>
    })
}

export function DatLeSosPopup({ popup, onNavigate, onDismiss }: Props) {
    if (!popup.show) return null

    return (
        <aside
            className="pointer-events-none fixed bottom-[82px] right-4 z-40 w-[min(420px,calc(100vw-32px))]"
            aria-live="polite"
        >
            <div className="pointer-events-auto border border-[#8a6a3f]/60 bg-[#fff4dc]/98 p-3 text-[#1a1008] shadow-[5px_5px_0_rgba(0,0,0,0.42)]">
                <div className="grid grid-cols-[72px_1fr_auto] gap-3">
                    <img
                        src={datLeShockSos}
                        alt=""
                        className="h-[72px] w-[72px] border border-[#1a1008]/15 bg-[#ffe9c2] object-contain"
                    />
                    <div className="min-w-0">
                        <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#8a442d]">
                            {popup.character_label || 'Đạt'}
                        </p>
                        <h2 className="mt-0.5 text-base font-black leading-tight text-[#1a1008]">
                            {popup.title || 'Đạt đang ở đây'}
                        </h2>
                        <p className="mt-2 text-sm leading-relaxed text-[#2b1a0c]">
                            {renderSegments(popup, onNavigate)}
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={() => onDismiss(popup.popup_id)}
                        className="flex h-8 w-8 items-center justify-center border border-[#1a1008]/20 bg-[#1a1008] text-[#fff4dc] transition hover:bg-[#3b2411]"
                        aria-label="Đóng thông báo"
                        title="Đóng"
                    >
                        <X className="h-4 w-4" aria-hidden />
                    </button>
                </div>
                <div className="mt-3 flex flex-wrap justify-end gap-2">
                    <button
                        type="button"
                        onClick={() => onNavigate(popup.support_route)}
                        className="inline-flex items-center gap-2 border border-[#244b34]/40 bg-[#2d5535] px-3 py-2 text-xs font-bold uppercase tracking-wide text-[#e9f6dd] shadow-[2px_2px_0_rgba(0,0,0,0.28)]"
                    >
                        <LifeBuoy className="h-4 w-4" aria-hidden />
                        Mở Hỗ trợ
                    </button>
                    <button
                        type="button"
                        onClick={() => onNavigate(popup.breathing_exercise_route)}
                        className="inline-flex items-center gap-2 border border-[#174c63]/35 bg-[#dff3ff] px-3 py-2 text-xs font-bold uppercase tracking-wide text-[#174c63] shadow-[2px_2px_0_rgba(0,0,0,0.18)]"
                    >
                        <Wind className="h-4 w-4" aria-hidden />
                        Bài tập thở khi lo âu
                    </button>
                </div>
            </div>
        </aside>
    )
}
