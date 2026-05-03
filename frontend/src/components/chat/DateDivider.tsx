type Props = {
  timestamp: number
}

function formatDateLabel(ts: number): string {
  const date = new Date(ts)
  const today = new Date()
  const yesterday = new Date()
  yesterday.setDate(today.getDate() - 1)

  const isSameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()

  if (isSameDay(date, today)) return 'Hôm nay'
  if (isSameDay(date, yesterday)) return 'Hôm qua'

  return date.toLocaleDateString('vi-VN', {
    weekday: 'long',
    day: 'numeric',
    month: 'numeric',
    year: 'numeric',
  })
}

export function DateDivider({ timestamp }: Props) {
  return (
    <div className="flex items-center gap-3 py-1">
      <div className="h-px flex-1 bg-theme-border/60" />
      <span className="rounded-full bg-theme-surface/60 border border-theme-border/30 px-3 py-1 text-[11px] font-medium text-theme-text-secondary shadow-sm backdrop-blur-sm">
        {formatDateLabel(timestamp)}
      </span>
      <div className="h-px flex-1 bg-theme-border/60" />
    </div>
  )
}
