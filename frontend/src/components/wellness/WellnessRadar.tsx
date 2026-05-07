import {
    PolarAngleAxis,
    PolarGrid,
    Radar,
    RadarChart,
    ResponsiveContainer,
} from 'recharts'

export type WellnessScores = {
    emotional: number    // 0-100
    sleep: number
    mindfulness: number
    social: number
    physical: number
    growth: number
}

type Props = {
    scores: WellnessScores
    mini?: boolean
    className?: string
}

const AXES: Array<{ key: keyof WellnessScores; label: string }> = [
    { key: 'emotional', label: 'Cảm xúc' },
    { key: 'sleep', label: 'Giấc ngủ' },
    { key: 'mindfulness', label: 'Tỉnh thức' },
    { key: 'social', label: 'Kết nối' },
    { key: 'physical', label: 'Thể chất' },
    { key: 'growth', label: 'Phát triển' },
]

const DOT_STYLE = {
    r: 5,
    fill: 'var(--color-serene-primary)',
    stroke: 'white',
    strokeWidth: 2,
}

export function WellnessRadar({ scores, mini = false, className }: Props) {
    const data = AXES.map((axis) => ({
        subject: axis.label,
        value: Math.round(Math.max(0, Math.min(100, scores[axis.key]))),
    }))

    const height = mini ? 156 : 320
    const outerRadius = mini ? '62%' : '60%'
    const tickFill = mini ? 'transparent' : 'var(--color-theme-primary)'

    return (
        <div className={className}>
            <ResponsiveContainer width="100%" height={height}>
                <RadarChart cx="50%" cy="50%" outerRadius={outerRadius} data={data}>
                    <defs>
                        <radialGradient id="radarFill" cx="50%" cy="50%" r="50%">
                            <stop offset="0%" stopColor="var(--color-serene-primary)" stopOpacity={0.45} />
                            <stop offset="100%" stopColor="var(--color-serene-accent)" stopOpacity={0.12} />
                        </radialGradient>
                    </defs>
                    <PolarGrid
                        stroke="currentColor"
                        className="text-theme-border/30 dark:text-white/10"
                        gridType="polygon"
                        strokeDasharray="3 4"
                    />
                    <PolarAngleAxis
                        dataKey="subject"
                        tick={{
                            fill: 'currentColor',
                            className: 'text-theme-text-secondary dark:text-theme-text-tertiary',
                            fontSize: 11,
                            fontWeight: 500,
                            fontFamily: 'var(--font-body)',
                        }}
                    />
                    <Radar
                        name="Wellness"
                        dataKey="value"
                        stroke="var(--color-theme-accent)"
                        fill="url(#radarFill)"
                        strokeWidth={2}
                        dot={mini ? false : { ...DOT_STYLE, fill: 'var(--color-theme-accent)' }}
                        animationBegin={0}
                        animationDuration={900}
                        animationEasing="ease-out"
                    />
                </RadarChart>
            </ResponsiveContainer>
        </div>
    )
}
