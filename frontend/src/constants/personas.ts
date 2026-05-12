export const PERSONA_IDS = ['dung_luong', 'dat_le', 'hau_luong'] as const
export type PersonaId = (typeof PERSONA_IDS)[number]
export const DEFAULT_PERSONA_ID: PersonaId = 'dung_luong'

export const PERSONA_DISPLAY_NAME: Record<string, string> = {
    dung_luong: 'Dũng',
    dat_le: 'Đạt',
    hau_luong: 'Hậu',
}

export const PERSONA_SHORT_DESCRIPTION: Record<string, string> = {
    dung_luong: 'Vui vẻ, hay gửi meme đúng ngữ cảnh, sống tích cực, biết lắng nghe',
    dat_le: 'Trầm ngâm, suy ngẫm triết lý cuộc đời, hay động viên, truyền cảm hứng',
    hau_luong: 'Hướng nội hay gửi voice message vì lười nhắn, do vô tư nên chữa được lo âu và overthinking',
}

export function isPersonaId(value: string | null | undefined): value is PersonaId {
    return PERSONA_IDS.includes(value as PersonaId)
}
