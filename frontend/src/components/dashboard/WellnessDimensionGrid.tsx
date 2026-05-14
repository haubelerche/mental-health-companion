import type { ReflectWellnessDimension } from '../../services/dashboardService'
import { WellnessDimensionCard } from './WellnessDimensionCard'

type Props = {
    dimensions: ReflectWellnessDimension[]
}

export function WellnessDimensionGrid({ dimensions }: Props) {
    return (
        <section>
            <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
                <div>
                    <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-theme-text-tertiary">
                        6 chiều sức khỏe
                    </p>
                    <h2 className="mt-1 font-display text-2xl text-theme-text-primary">Bức tranh chi tiết hơn</h2>
                </div>
                <p className="max-w-md text-sm leading-relaxed text-theme-text-secondary">
                    Mỗi chiều là một lát cắt tự quan sát, không phải bảng điểm y tế hay kết luận chẩn đoán.
                </p>
            </div>
            <div className="-mx-4 flex snap-x snap-mandatory gap-4 overflow-x-auto px-4 pb-2 md:mx-0 md:grid md:grid-cols-2 md:overflow-visible md:px-0 lg:grid-cols-3">
                {dimensions.map((dimension) => (
                    <div key={dimension.dimension} className="w-[min(21rem,calc(100vw-2rem))] shrink-0 snap-start md:w-auto">
                        <WellnessDimensionCard dimension={dimension} />
                    </div>
                ))}
            </div>
        </section>
    )
}
