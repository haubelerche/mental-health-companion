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
    <div className="mb-3 flex items-center gap-3 py-1">
      <div className="h-px flex-1 bg-[#d7d9b8]/30" />
      <span className="border border-[#6e5437]/45 bg-[#fff4dc]/90 px-3 py-1 text-[11px] font-medium text-[#5b4b35] shadow-[2px_2px_0_rgba(0,0,0,0.18)] backdrop-blur-sm">
        {formatDateLabel(timestamp)}
      </span>
      <div className="h-px flex-1 bg-[#d7d9b8]/30" />
    </div>
  )
}
