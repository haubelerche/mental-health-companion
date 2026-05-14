import { ReflectMetricCard } from './ReflectMetricCard'
import type { ReflectDashboardSummary } from '../../services/dashboardService'

type Props = {
    summary: ReflectDashboardSummary
}

function countList(items: Array<{ label: string; count: number }>): string {
    if (!items.length) return 'Chưa ghi'
    return items.map((item) => `${item.label} (${item.count})`).join(', ')
}

export function ReflectMetricsRow({ summary }: Props) {
    const coverage = [
        `sáng ${summary.period_coverage.morning}`,
        `chiều ${summary.period_coverage.afternoon}`,
        `tối ${summary.period_coverage.evening}`,
    ].join(' · ')
    const moodValue =
        typeof summary.mood_average === 'number' ? `${summary.mood_average}/10` : 'Chưa ghi'
    const moodRange =
        typeof summary.mood_min === 'number' && typeof summary.mood_max === 'number'
            ? `Khoảng dao động: ${summary.mood_min}-${summary.mood_max}/10`
            : 'Chưa có điểm mood'

    return (
        <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <ReflectMetricCard label="Check-in" value={summary.checkin_count} detail={coverage} />
            <ReflectMetricCard label="Mood trung bình" value={moodValue} detail={moodRange} />
            <ReflectMetricCard label="Trigger đã ghi nhận" value={countList(summary.top_triggers)} />
            <ReflectMetricCard label="Cảm xúc nổi bật" value={countList(summary.top_emotions)} />
            <ReflectMetricCard
                label="Dữ liệu còn thiếu"
                value={summary.missing_data.length ? `${summary.missing_data.length} mục` : 'Không thiếu mục chính'}
                detail={summary.missing_data.length ? summary.missing_data.join(', ') : 'Coverage chính đã có trong khoảng này'}
            />
        </section>
    )
}
