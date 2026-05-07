import { motion } from 'framer-motion'
import { Flame, Calendar, TrendingUp, CheckSquare } from 'lucide-react'

export type ProgressData = {
  streakDays: number
  bestStreak: number
  weeklyCheckins: number       // out of 7
  totalSessions: number
  breathingSessions: number
  daysActive30d: number
}

type StatCardProps = {
  icon: React.ElementType
  value: string | number
  label: string
  sub?: string
  color: string
  delay?: number
}

function StatCard({ icon: Icon, value, label, sub, color, delay = 0 }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35, ease: 'easeOut' }}
      className="flex flex-col gap-1.5 rounded-2xl border border-serene-border/60 bg-white/40 p-3.5 shadow-xl[0_2px_8px_rgba(47,52,46,0.06)]"
    >
      <div
        className="flex h-8 w-8 items-center justify-center rounded-xl"
        style={{ backgroundColor: `${color}18` }}
      >
        <Icon className="h-4 w-4" style={{ color }} />
      </div>
      <div>
        <p className="font-display text-xl font-semibold text-theme-text-primary">{value}</p>
        <p className="text-xs font-medium text-theme-text-secondary">{label}</p>
        {sub && <p className="mt-0.5 text-[11px] text-theme-text-secondary/70">{sub}</p>}
      </div>
    </motion.div>
  )
}

type Props = {
  data: ProgressData
}

export function ProgressStats({ data }: Props) {
  const weeklyFraction = Math.min(1, data.weeklyCheckins / 7)

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          icon={Flame}
          value={data.streakDays}
          label="Ngày liên tiếp"
          sub={`Cao nhất: ${data.bestStreak} ngày`}
          color="#f97316"
          delay={0}
        />
        <StatCard
          icon={CheckSquare}
          value={`${data.weeklyCheckins}/7`}
          label="Check-in tuần này"
          sub="Mục tiêu: mỗi ngày"
          color="#4d6359"
          delay={0.06}
        />
        <StatCard
          icon={TrendingUp}
          value={data.totalSessions}
          label="Tổng phiên chat"
          sub="Tất cả thời gian"
          color="#0284c7"
          delay={0.12}
        />
        <StatCard
          icon={Calendar}
          value={data.daysActive30d}
          label="Ngày HĐ (30d)"
          sub="Trong 30 ngày qua"
          color="#e11d48"
          delay={0.18}
        />
      </div>

      {/* Weekly check-in bar */}
      <div className="rounded-2xl border border-serene-border/50 bg-theme-surface px-4 py-3">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs font-semibold text-theme-text-primary">Tuần này</p>
          <p className="text-xs text-theme-text-secondary">
            {data.weeklyCheckins} / 7 ngày check-in
          </p>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-serene-border/60">
          <motion.div
            className="h-full rounded-full bg-serene-primary"
            initial={{ width: 0 }}
            animate={{ width: `${weeklyFraction * 100}%` }}
            transition={{ duration: 0.7, ease: 'easeOut', delay: 0.2 }}
          />
        </div>
        <div className="mt-3 flex justify-between gap-1">
          {['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'].map((day, i) => {
            const filled = i < data.weeklyCheckins
            return (
              <div key={day} className="flex flex-1 flex-col items-center gap-1.5">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.25 + i * 0.05, type: 'spring', stiffness: 300 }}
                  className={`h-2 w-2 rounded-full transition-colors ${
                    filled ? 'bg-theme-primary' : 'bg-serene-border/60'
                  }`}
                />
                <span className={`text-[10px] ${filled ? 'text-serene-primary font-semibold' : 'text-serene-muted/50'}`}>
                  {day}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
