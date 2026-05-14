import type { ScreeningId, ScreeningResult } from '../services/screeningService'

export type StoredScreeningResult = {
    instrument_id: ScreeningId
    raw_score: number
    severity_label: ScreeningResult['severity_label']
    assessment_updated_at?: string
    timestamp?: string
}

export type StoredScreeningResults = Record<ScreeningId, StoredScreeningResult | null>

export const SCREENING_RESULTS_UPDATED_EVENT = 'serene:screening-results-updated'

export const SCREENING_INSTRUMENT_META: Record<
    ScreeningId,
    { title: string; domain: string; maxScore: number }
> = {
    phq9: { title: 'PHQ-9', domain: 'Tâm trạng', maxScore: 27 },
    gad7: { title: 'GAD-7', domain: 'Lo âu', maxScore: 21 },
}

export const SCREENING_SEVERITY_LABELS: Record<ScreeningResult['severity_label'], string> = {
    minimal: 'Rất nhẹ',
    mild: 'Nhẹ',
    moderate: 'Trung bình',
    moderately_severe: 'Khá cao',
    severe: 'Cao',
}

export const SCREENING_SEVERITY_COLORS: Record<ScreeningResult['severity_label'], string> = {
    minimal: '#4caf50',
    mild: '#8bc34a',
    moderate: '#ff9800',
    moderately_severe: '#e57373',
    severe: '#c62828',
}

const SCREENING_IDS: ScreeningId[] = ['phq9', 'gad7']
const STORAGE_KEY_PREFIX = 'serene_screening_'
const VALID_SEVERITIES = new Set<ScreeningResult['severity_label']>([
    'minimal',
    'mild',
    'moderate',
    'moderately_severe',
    'severe',
])

function storageKey(instrumentId: ScreeningId): string {
    return `${STORAGE_KEY_PREFIX}${instrumentId}`
}

function hasLocalStorage(): boolean {
    return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'
}

function parseStoredScreeningResult(
    instrumentId: ScreeningId,
    raw: string | null,
): StoredScreeningResult | null {
    if (!raw) return null

    try {
        const parsed = JSON.parse(raw) as Partial<StoredScreeningResult>
        if (
            typeof parsed.raw_score !== 'number' ||
            !VALID_SEVERITIES.has(parsed.severity_label as ScreeningResult['severity_label'])
        ) {
            return null
        }

        return {
            instrument_id: instrumentId,
            raw_score: parsed.raw_score,
            severity_label: parsed.severity_label as ScreeningResult['severity_label'],
            assessment_updated_at: parsed.assessment_updated_at,
            timestamp: parsed.timestamp,
        }
    } catch {
        return null
    }
}

export function readStoredScreeningResult(instrumentId: ScreeningId): StoredScreeningResult | null {
    if (!hasLocalStorage()) return null
    return parseStoredScreeningResult(instrumentId, window.localStorage.getItem(storageKey(instrumentId)))
}

export function readStoredScreeningResults(): StoredScreeningResults {
    return SCREENING_IDS.reduce<StoredScreeningResults>(
        (results, instrumentId) => ({
            ...results,
            [instrumentId]: readStoredScreeningResult(instrumentId),
        }),
        { phq9: null, gad7: null },
    )
}

export function saveScreeningResult(result: ScreeningResult): void {
    if (!hasLocalStorage()) return

    const stored: StoredScreeningResult = {
        instrument_id: result.instrument_id,
        raw_score: result.raw_score,
        severity_label: result.severity_label,
        assessment_updated_at: result.assessment_updated_at,
        timestamp: new Date().toISOString(),
    }

    window.localStorage.setItem(storageKey(result.instrument_id), JSON.stringify(stored))
    window.dispatchEvent(
        new CustomEvent(SCREENING_RESULTS_UPDATED_EVENT, {
            detail: { instrument_id: result.instrument_id },
        }),
    )
}

export function subscribeToScreeningResults(onChange: (results: StoredScreeningResults) => void): () => void {
    if (typeof window === 'undefined') return () => undefined

    const refresh = () => onChange(readStoredScreeningResults())
    const refreshFromStorage = (event: StorageEvent) => {
        if (event.key?.startsWith(STORAGE_KEY_PREFIX)) refresh()
    }

    window.addEventListener(SCREENING_RESULTS_UPDATED_EVENT, refresh)
    window.addEventListener('storage', refreshFromStorage)

    return () => {
        window.removeEventListener(SCREENING_RESULTS_UPDATED_EVENT, refresh)
        window.removeEventListener('storage', refreshFromStorage)
    }
}

export function getCombinedScreeningInsight(
    phq9?: ScreeningResult['severity_label'],
    gad7?: ScreeningResult['severity_label'],
): string {
    if (phq9 === 'minimal' && gad7 === 'minimal') {
        return 'Tâm trạng và mức độ lo âu của bạn đang ở trạng thái rất tốt. Hãy tiếp tục duy trì lối sống lành mạnh!'
    }
    if ((phq9 === 'moderate' || phq9 === 'severe') && (gad7 === 'moderate' || gad7 === 'severe')) {
        return 'Bạn đang có dấu hiệu căng thẳng và mệt mỏi khá cao. Hãy cân nhắc trò chuyện với Serene hoặc tìm kiếm sự hỗ trợ từ chuyên gia.'
    }
    return 'Có một vài biến động nhỏ trong tâm trạng hoặc lo âu. Hãy chú ý lắng nghe cơ thể và dành thời gian thư giãn nhiều hơn.'
}
