import { ClipboardList, ArrowRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ROUTE_PATHS } from '../../routes/paths'
import { useThemeContext } from '../../contexts/ThemeContext'
import type { ScreeningId } from '../../services/screeningService'
import {
    readStoredScreeningResults,
    SCREENING_INSTRUMENT_META,
    SCREENING_SEVERITY_COLORS,
    SCREENING_SEVERITY_LABELS,
    subscribeToScreeningResults,
    type StoredScreeningResult,
} from '../../utils/screeningResults'

function ScreeningResultCard({
    instrumentId,
    result,
}: {
    instrumentId: ScreeningId
    result: StoredScreeningResult | null
}) {
    const meta = SCREENING_INSTRUMENT_META[instrumentId]

    if (!result) {
        return (
            <div className="rounded-2xl border border-dashed border-theme-border bg-theme-bg-secondary/45 p-4">
                <div className="flex items-center justify-between gap-3">
                    <div>
                        <p className="text-xs font-bold uppercase tracking-[0.16em] text-theme-text-secondary">
                            Mô-đun: {meta.title}
                        </p>
                        <p className="mt-1 text-xs text-theme-text-tertiary">{meta.domain}</p>
                    </div>
                </div>
                <p className="mt-4 text-sm font-semibold text-theme-text-primary">Chưa có dữ liệu</p>
                <Link
                    to={ROUTE_PATHS.screening}
                    className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-theme-accent hover:underline"
                >
                    Làm test ngay
                    <ArrowRight className="h-4 w-4" aria-hidden />
                </Link>
            </div>
        )
    }

    const percent = Math.min(100, Math.max(0, (result.raw_score / meta.maxScore) * 100))
    const severityColor = SCREENING_SEVERITY_COLORS[result.severity_label]

    return (
        <div className="rounded-2xl border border-theme-border/70 bg-theme-bg-secondary/45 p-4">
            <div className="flex items-center justify-between gap-3">
                <div>
                    <p className="text-xs font-bold uppercase tracking-[0.16em] text-theme-text-secondary">
                        Mô-đun: {meta.title}
                    </p>
                    <p className="mt-1 text-xs text-theme-text-tertiary">{meta.domain}</p>
                </div>
                <Link to={ROUTE_PATHS.screening} className="text-xs font-semibold text-theme-accent hover:underline">
                    Thử làm lại
                </Link>
            </div>

            <div className="mt-4">
                <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold text-theme-accent">
                        {result.raw_score.toString().padStart(2, '0')}
                    </span>
                    <span className="text-sm text-theme-text-secondary">/{meta.maxScore}</span>
                </div>
                <p className="mt-2 text-xs font-semibold uppercase" style={{ color: severityColor }}>
                    Trạng thái: {SCREENING_SEVERITY_LABELS[result.severity_label]}
                </p>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-theme-border/25">
                    <div className="h-full rounded-full" style={{ width: `${percent}%`, backgroundColor: severityColor }} />
                </div>
            </div>
        </div>
    )
}

export function ScreeningPanel() {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'
    const [results, setResults] = useState(() => readStoredScreeningResults())
    const hasResults = Object.values(results).some((val) => val !== null)

    useEffect(() => subscribeToScreeningResults(setResults), [])

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface p-4 shadow-sm md:p-5">
            <div className="mb-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">Sàng lọc</p>
                <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Kết quả sàng lọc</h2>
                <p className="mt-1 text-sm leading-relaxed text-theme-text-secondary">
                    Kết quả bài sàng lọc giúp Serene hiểu rõ hơn về tình hình của bạn. Đây là dữ liệu sàng lọc, không phải chẩn đoán.
                </p>
            </div>

            {hasResults ? (
                <div className="grid gap-3 sm:grid-cols-2">
                    {(['phq9', 'gad7', 'dass21', 'mdq', 'pcl5'] as const).map((instrumentId) => (
                        <ScreeningResultCard key={instrumentId} instrumentId={instrumentId} result={results[instrumentId]} />
                    ))}
                </div>
            ) : (
                <div className="rounded-2xl border border-dashed border-theme-border bg-theme-bg-secondary/50 p-5 text-center">
                    <ClipboardList className="mx-auto mb-3 h-10 w-10 text-theme-text-tertiary" aria-hidden />
                    <p className="text-sm font-semibold text-theme-text-primary">Chưa có dữ liệu sàng lọc</p>
                    <p className="mt-1 max-w-sm mx-auto text-sm leading-relaxed text-theme-text-secondary">
                        Làm bài test để chúng mình có thêm dữ liệu phân tích. Bài test chỉ là sàng lọc, không phải chẩn đoán.
                    </p>
                    <div className="mt-4 flex flex-wrap justify-center gap-3">
                        <Link
                            to={ROUTE_PATHS.screening}
                            className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition ${
                                isDark
                                    ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200'
                                    : 'border-emerald-300/80 bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
                            }`}
                        >
                            Làm bài test sàng lọc
                            <ArrowRight className="h-4 w-4" aria-hidden />
                        </Link>
                    </div>
                </div>
            )}

            <p className="mt-3 text-[11px] leading-relaxed text-theme-text-tertiary">
                Bài test sàng lọc hỗ trợ nhận diện dấu hiệu, không thay thế đánh giá của chuyên gia sức khỏe tâm thần.
            </p>
        </section>
    )
}
