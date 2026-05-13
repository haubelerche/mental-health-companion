export const PERSONA_IDS = ['dung_luong', 'dat_le', 'hau_luong'] as const
export type PersonaId = (typeof PERSONA_IDS)[number]
export const DEFAULT_PERSONA_ID: PersonaId = 'dung_luong'

export const PERSONA_DISPLAY_NAME: Record<string, string> = {
    dung_luong: 'Dũng',
    dat_le: 'Đạt',
    hau_luong: 'Hậu',
}

export const PERSONA_SHORT_DESCRIPTION: Record<string, string> = {
    dung_luong: 'Vui vẻ, bắt mood tốt, hay gửi meme cho vui,biết lắng nghe, tử tế, đùa nhẹ đúng lúc',
    dat_le: 'Trầm tính, có chiều sâu; giúp bạn nhìn vấn đề rõ ràng hơn, triết lý hơn',
    hau_luong: 'Hướng nội, đơn giản, ít áp lực, hay gửi voice message nhẹ để giảm overthinking',
}

export function isPersonaId(value: string | null | undefined): value is PersonaId {
    return PERSONA_IDS.includes(value as PersonaId)
}
