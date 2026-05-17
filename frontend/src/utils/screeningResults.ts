import type { ScreeningId, ScreeningLatestEntry, ScreeningResult } from '../services/screeningService'
import { screeningService } from '../services/screeningService'

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
    dass21: { title: 'DASS-21', domain: 'Trầm cảm-Lo âu-Stress', maxScore: 63 },
    mdq: { title: 'MDQ', domain: 'Lưỡng cực', maxScore: 15 },
    pcl5: { title: 'PCL-5', domain: 'PTSD', maxScore: 80 },
}

export const SCREENING_SEVERITY_LABELS: Record<ScreeningResult['severity_label'], string> = {
    minimal: 'Rất nhẹ',
    mild: 'Nhẹ',
    moderate: 'Trung bình',
    moderately_severe: 'Khá cao',
    severe: 'Cao',
    assessed: 'Đã đánh giá',
    positive: 'Dương tính',
    negative: 'Âm tính',
    high_risk: 'Nguy cơ cao',
    low_risk: 'Nguy cơ thấp',
}

export const SCREENING_SEVERITY_COLORS: Record<ScreeningResult['severity_label'], string> = {
    minimal: '#4caf50',
    mild: '#8bc34a',
    moderate: '#ff9800',
    moderately_severe: '#e57373',
    severe: '#c62828',
    assessed: '#2196f3',
    positive: '#f44336',
    negative: '#4caf50',
    high_risk: '#f44336',
    low_risk: '#4caf50',
}

const SCREENING_IDS: ScreeningId[] = ['phq9', 'gad7', 'dass21', 'mdq', 'pcl5']
const STORAGE_KEY_PREFIX = 'serene_screening_'
const VALID_SEVERITIES = new Set<ScreeningResult['severity_label']>([
    'minimal',
    'mild',
    'moderate',
    'moderately_severe',
    'severe',
    'assessed',
    'positive',
    'negative',
    'high_risk',
    'low_risk',
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
        { phq9: null, gad7: null, dass21: null, mdq: null, pcl5: null },
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

/**
 * Hydrate localStorage from backend on login / mount.
 * Falls back silently if the API call fails — localStorage remains valid.
 * This makes the backend the authoritative source for cross-device persistence.
 */
export async function syncScreeningResultsFromBackend(): Promise<void> {
    if (!hasLocalStorage()) return
    try {
        const resp = await screeningService.getLatest()
        const results: Record<ScreeningId, ScreeningLatestEntry | null> = (resp as { results: Record<ScreeningId, ScreeningLatestEntry | null> })?.results ?? {}
        for (const id of SCREENING_IDS) {
            const entry = results[id]
            if (!entry) continue
            // Only overwrite localStorage if backend has a newer record
            const existing = readStoredScreeningResult(id)
            const backendAt = entry.assessment_updated_at ?? ''
            const localAt = existing?.assessment_updated_at ?? ''
            if (!existing || backendAt > localAt) {
                const stored: StoredScreeningResult = {
                    instrument_id: id,
                    raw_score: 0,            // not exposed by /latest
                    severity_label: entry.severity_label,
                    assessment_updated_at: entry.assessment_updated_at ?? undefined,
                    timestamp: new Date().toISOString(),
                }
                window.localStorage.setItem(storageKey(id), JSON.stringify(stored))
            }
        }
        window.dispatchEvent(new CustomEvent(SCREENING_RESULTS_UPDATED_EVENT))
    } catch {
        // Non-fatal — user continues with locally cached data
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
