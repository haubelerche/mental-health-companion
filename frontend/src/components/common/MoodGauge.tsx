import { motion } from 'framer-motion'

type Props = {
  value: number        // 1–10
  onChange?: (v: number) => void
  size?: number
  readOnly?: boolean
}

const MOOD_LABELS: Record<number, { label: string; color: string }> = {
  1: { label: 'Rất tệ', color: '#c0392b' },
  2: { label: 'Tệ', color: '#e74c3c' },
  3: { label: 'Khá tệ', color: '#e67e22' },
  4: { label: 'Không tốt', color: '#f39c12' },
  5: { label: 'Bình thường', color: '#f1c40f' },
  6: { label: 'Khá ổn', color: '#a8c940' },
  7: { label: 'Tốt', color: '#5cb85c' },
  8: { label: 'Khá tốt', color: '#27ae60' },
  9: { label: 'Rất tốt', color: '#1abc9c' },
  10: { label: 'Xuất sắc!', color: '#16a085' },
}

function getColor(value: number): string {
  return MOOD_LABELS[value]?.color ?? '#4d6359'
}

function getLabel(value: number): string {
  return MOOD_LABELS[value]?.label ?? ''
}

export function MoodGauge({ value, onChange, size = 200, readOnly = false }: Props) {
  // Semicircle geometry
  const cx = size / 2
  const cy = size * 0.62
  const r = size * 0.38
  const strokeWidth = size * 0.065

  // Arc path helper — draw semicircle from left to right
  const toRad = (deg: number) => (deg * Math.PI) / 180
  const arcPath = (startDeg: number, endDeg: number, radius: number) => {
    const start = {
      x: cx + radius * Math.cos(toRad(startDeg)),
      y: cy + radius * Math.sin(toRad(startDeg)),
    }
    const end = {
      x: cx + radius * Math.cos(toRad(endDeg)),
      y: cy + radius * Math.sin(toRad(endDeg)),
    }
    const largeArc = endDeg - startDeg > 180 ? 1 : 0
    return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`
  }

  // Range: 180° (left) to 0° (right), mapped to value 1–10
  const startAngle = 180
  const endAngle = 0
  const totalAngle = 180 // absolute
  const needleDeg = startAngle - ((value - 1) / 9) * totalAngle
  const fillDeg = ((value - 1) / 9) * totalAngle // degrees filled from left

  // Needle tip coordinates
  const needleLen = r - strokeWidth * 0.5
  const needleX = cx + needleLen * Math.cos(toRad(needleDeg))
  const needleY = cy + needleLen * Math.sin(toRad(needleDeg))

  const color = getColor(value)
  const label = getLabel(value)

  // Tap zone: 10 invisible arc segments
  const handleClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (readOnly || !onChange) return
    const svg = e.currentTarget
    const rect = svg.getBoundingClientRect()
    const x = e.clientX - rect.left - cx
    const y = e.clientY - rect.top - cy
    const angle = (Math.atan2(y, x) * 180) / Math.PI
    // Normalize angle: 180° = left (value 1), 0° = right (value 10)
    let deg = angle
    if (deg > 0) deg = 180 - deg // upper semicircle clicks
    else deg = -deg
    deg = Math.max(0, Math.min(180, deg + (angle <= 0 ? 0 : 0)))
    // Actually: map angle from 180→0 to value 1→10
    const normalized = (180 - Math.max(0, Math.min(180, angle <= 0 ? -angle : 180 - angle))) / 180
    const newValue = Math.round(1 + normalized * 9)
    onChange(Math.max(1, Math.min(10, newValue)))
  }

  // Gradient ID unique per instance
  const gradId = 'mood-gauge-grad'

  return (
    <div className="flex flex-col items-center gap-2">
      <svg
        width={size}
        height={size * 0.72}
        viewBox={`0 0 ${size} ${size * 0.72}`}
        onClick={handleClick}
        className={readOnly ? '' : 'cursor-pointer select-none'}
        role={readOnly ? 'img' : 'slider'}
        aria-valuemin={1}
        aria-valuemax={10}
        aria-valuenow={value}
        aria-label={`Tâm trạng: ${label}`}
      >
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#c0392b" />
            <stop offset="25%" stopColor="#e67e22" />
            <stop offset="50%" stopColor="#f1c40f" />
            <stop offset="75%" stopColor="#5cb85c" />
            <stop offset="100%" stopColor="#16a085" />
          </linearGradient>
        </defs>

        {/* Background track */}
        <path
          d={arcPath(180, 0, r)}
          fill="none"
          stroke="var(--color-serene-border)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />

        {/* Filled arc */}
        {value > 1 && (
          <motion.path
            d={arcPath(180, 180 - fillDeg, r)}
            fill="none"
            stroke={`url(#${gradId})`}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        )}

        {/* Tick marks */}
        {Array.from({ length: 9 }, (_, i) => i + 1).map((i) => {
          const tickDeg = 180 - (i / 10) * 180
          const tickR1 = r + strokeWidth * 0.65
          const tickR2 = r + strokeWidth * 1.2
          return (
            <line
              key={i}
              x1={cx + tickR1 * Math.cos(toRad(tickDeg))}
              y1={cy + tickR1 * Math.sin(toRad(tickDeg))}
              x2={cx + tickR2 * Math.cos(toRad(tickDeg))}
              y2={cy + tickR2 * Math.sin(toRad(tickDeg))}
              stroke="var(--color-serene-border)"
              strokeWidth={1.5}
              strokeLinecap="round"
            />
          )
        })}

        {/* Needle */}
        <motion.line
          x1={cx}
          y1={cy}
          x2={needleX}
          y2={needleY}
          stroke={color}
          strokeWidth={strokeWidth * 0.35}
          strokeLinecap="round"
          animate={{ x2: needleX, y2: needleY }}
          transition={{ type: 'spring', stiffness: 260, damping: 22 }}
        />

        {/* Center dot */}
        <circle cx={cx} cy={cy} r={strokeWidth * 0.55} fill={color} />

        {/* Value label in center */}
        <text
          x={cx}
          y={cy + strokeWidth * 2.5}
          textAnchor="middle"
          fontSize={size * 0.13}
          fontWeight="700"
          fill={color}
          fontFamily="var(--font-display), serif"
        >
          {value}
        </text>
      </svg>

      {/* Mood label below gauge */}
      <motion.p
        key={value}
        initial={{ opacity: 0, scale: 0.85 }}
        animate={{ opacity: 1, scale: 1 }}
        className="font-display text-xl"
        style={{ color }}
      >
        {label}
      </motion.p>

      {/* Stepper buttons */}
      {!readOnly && onChange && (
        <div className="mt-2 flex items-center gap-4">
          <button
            type="button"
            onClick={() => onChange(Math.max(1, value - 1))}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-serene-border bg-white text-xl text-serene-muted transition hover:border-serene-primary hover:text-serene-primary active:scale-95"
            aria-label="Giảm"
          >
            −
          </button>
          <span className="w-16 text-center text-sm text-serene-muted">
            {value} / 10
          </span>
          <button
            type="button"
            onClick={() => onChange(Math.min(10, value + 1))}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-serene-border bg-white text-xl text-serene-muted transition hover:border-serene-primary hover:text-serene-primary active:scale-95"
            aria-label="Tăng"
          >
            +
          </button>
        </div>
      )}
    </div>
  )
}
