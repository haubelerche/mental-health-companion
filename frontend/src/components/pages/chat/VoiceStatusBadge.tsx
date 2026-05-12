/* eslint-disable react-refresh/only-export-components */
/** TTS job status display. Polling must stop on terminal statuses. */

import { Mic } from 'lucide-react'

export type TtsStatus =
    | 'queued'
    | 'processing'
    | 'ready'
    | 'failed'
    | 'skipped_duplicate'
    | 'cache_hit'
    | 'provider_disabled'
    | 'cancelled'
    | 'expired'

export const TTS_TERMINAL_STATUSES: ReadonlySet<TtsStatus> = new Set([
    'ready',
    'failed',
    'skipped_duplicate',
    'cache_hit',
    'provider_disabled',
    'cancelled',
    'expired',
])

const STATUS_LABELS: Record<TtsStatus, string> = {
    queued: 'Đang chờ xử lý',
    processing: 'Đang xử lý giọng đọc',
    ready: 'Sẵn sàng',
    failed: 'Không thể tạo giọng đọc',
    skipped_duplicate: 'Đã có sẵn',
    cache_hit: 'Dùng bản lưu',
    provider_disabled: 'Giọng đọc tạm ngưng',
    cancelled: 'Đã hủy',
    expired: 'Hết hạn',
}

type Props = {
    status: TtsStatus | string
    className?: string
}

export default function VoiceStatusBadge({ status, className = '' }: Props) {
    const isTerminal = TTS_TERMINAL_STATUSES.has(status as TtsStatus)
    const label = STATUS_LABELS[status as TtsStatus] ?? status

    const colorClass =
        status === 'ready' || status === 'cache_hit'
            ? 'text-green-600'
            : status === 'failed' || status === 'provider_disabled'
              ? 'text-red-500'
              : 'text-gray-400 animate-pulse'

    return (
        <span
            className={`inline-flex items-center gap-1 text-xs ${colorClass} ${className}`}
            aria-live={isTerminal ? 'off' : 'polite'}
        >
            <Mic className="h-3.5 w-3.5 shrink-0 opacity-80" aria-hidden />
            {label}
        </span>
    )
}
