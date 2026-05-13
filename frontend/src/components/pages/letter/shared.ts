import { parseTime } from '@/utils/parseTime'
import type { LetterInboxItem, ReportCategory } from '../../../services/anonymousShareService'

export type Letter = {
    id: string
    from: string
    time: string
    body: string
    direction?: 'sent' | 'received'
    status?: string
    letter_type?: string
    can_reply?: boolean
}

export type TabId = 'beach' | 'community'

export function getUi(dark: boolean) {
    return {
        textPrimary: dark ? 'text-white' : 'text-slate-900',
        textSubtle: dark ? 'text-white/90' : 'text-slate-800',
        textSubtler: dark ? 'text-white/50' : 'text-slate-900/60',
        glassLight: dark ? 'bg-black/40 border-white/10' : 'bg-white/86 border-stone-950/18',
        glassBorder: dark ? 'border-white/10' : 'border-stone-950/18',
        overlay: dark ? 'bg-black/75' : 'bg-slate-900/26',
    }
}

export function toLetter(message: LetterInboxItem): Letter {
    return {
        id: message.id,
        from: message.anonymous_name || 'Một người vô danh',
        time: parseTime(message.received_at),
        body: message.content,
        direction: 'received',
        status: message.status ?? (message.reply ? 'replied' : 'approved'),
        letter_type: message.letter_type,
        can_reply: message.can_reply,
    }
}

export function pickRandomLetter(messages: LetterInboxItem[]): Letter | null {
    if (!messages.length) return null
    const index = Math.floor(Math.random() * messages.length)
    return toLetter(messages[index])
}

export const REPORT_CATEGORY_OPTIONS: Array<{ value: ReportCategory; label: string; description: string }> = [
    { value: 'spam', label: 'Spam', description: 'Quảng cáo, lặp lại, gây phiền' },
    { value: 'abuse', label: 'Abuse / Harassment', description: 'Lăng mạ, quấy rối, công kích' },
    { value: 'inappropriate', label: 'Inappropriate', description: 'Nội dung không phù hợp' },
    { value: 'self_harm', label: 'Self-harm', description: 'Nội dung liên quan tự hại' },
    { value: 'other', label: 'Khác', description: 'Tự nhập lý do chi tiết' },
]
