import { ArrowLeft, Leaf, LayoutGrid, Sparkles } from 'lucide-react'
import { useThemeContext } from '../../../contexts/ThemeContext'

interface ExerciseHeroProps {
  onBack: () => void
  title: string
  subtitle: string
}

export default function ExerciseHero({ onBack, title, subtitle }: ExerciseHeroProps) {
  const { effectiveTheme } = useThemeContext()
  const isDark = effectiveTheme === 'dark'

  return (
    <section className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
      <div className={`rounded-[28px] border p-6 shadow-[0_18px_40px_rgba(16,35,31,0.10)] backdrop-blur-sm sm:p-8 ${isDark ? 'border-white/15 bg-[#10231F]/78' : 'border-white/35 bg-[#F8F1DC]/88'}`}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-3">
            <p className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-medium uppercase tracking-[0.24em] ${isDark ? 'border-white/10 bg-white/5 text-[#F4E8C8]' : 'border-white/40 bg-white/30 text-[#5F7F68]'}`}>
              <Sparkles className="h-3.5 w-3.5" />
              Góc thư thái
            </p>
            <h1 className={`max-w-xl text-3xl font-semibold tracking-tight sm:text-4xl lg:text-5xl ${isDark ? 'text-[#F4E8C8]' : 'text-[#24352D]'}`}>
              {title}
            </h1>
            <p className={`max-w-2xl text-sm leading-6 sm:text-base ${isDark ? 'text-[#F4E8C8]/82' : 'text-[#24352D]/80'}`}>
              {subtitle}
            </p>
          </div>

          <button
            type="button"
            onClick={onBack}
            className={`inline-flex h-11 items-center gap-2 rounded-full border px-4 text-sm font-medium transition-colors motion-reduce:transition-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5F7F68] focus-visible:ring-offset-2 ${isDark ? 'border-white/10 bg-white/5 text-[#F4E8C8] hover:bg-white/10' : 'border-white/40 bg-white/25 text-[#24352D] hover:bg-white/40'}`}
            aria-label="Quay lại"
          >
            <ArrowLeft className="h-4 w-4" />
            Quay lại
          </button>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          {[
            { label: 'Dễ bắt đầu', value: '1 chạm', icon: LayoutGrid },
            { label: 'Nhẹ nhàng', value: 'Mềm, ít chữ', icon: Leaf },
            { label: 'An tâm', value: 'Khung rõ ràng', icon: Sparkles },
          ].map((item) => {
            const Icon = item.icon
            return (
              <div
                key={item.label}
                className={`rounded-[20px] border p-4 ${isDark ? 'border-white/10 bg-white/5 text-[#F4E8C8]' : 'border-white/30 bg-white/25 text-[#24352D]'}`}
              >
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.22em] opacity-70">
                  <Icon className="h-3.5 w-3.5" />
                  {item.label}
                </div>
                <p className="mt-2 text-lg font-semibold">{item.value}</p>
              </div>
            )
          })}
        </div>
      </div>

      <aside className={`rounded-[28px] border p-6 shadow-[0_18px_40px_rgba(16,35,31,0.10)] backdrop-blur-sm sm:p-8 ${isDark ? 'border-white/15 bg-[#10231F]/78' : 'border-white/35 bg-[#F8F1DC]/88'}`}>
        <div className="flex items-start gap-4">
          <div className={`flex h-14 w-14 items-center justify-center rounded-2xl ${isDark ? 'bg-white/10 text-[#F4E8C8]' : 'bg-[#5F7F68]/15 text-[#5F7F68]'}`}>
            <Sparkles className="h-6 w-6" />
          </div>
          <div className="min-w-0 flex-1">
            <p className={`text-[11px] font-medium uppercase tracking-[0.22em] ${isDark ? 'text-[#F4D28A]' : 'text-[#5F7F68]'}`}>
              Chọn một bài ngắn
            </p>
            <h2 className={`mt-1 text-xl font-semibold ${isDark ? 'text-[#F4E8C8]' : 'text-[#24352D]'}`}>
              {title}
            </h2>
            <p className={`mt-2 text-sm leading-6 ${isDark ? 'text-[#F4E8C8]/78' : 'text-[#24352D]/78'}`}>
              {subtitle}
            </p>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          {[
            { label: 'Chim chóc', icon: Sparkles },
            { label: 'Lá cây', icon: Leaf },
            { label: 'Không gian', icon: LayoutGrid },
          ].map((item) => {
            const Icon = item.icon
            return (
              <div
                key={item.label}
                className={`rounded-[18px] border px-3 py-3 text-center text-sm ${isDark ? 'border-white/10 bg-white/5 text-[#F4E8C8]' : 'border-white/30 bg-white/30 text-[#24352D]'}`}
              >
                <Icon className="mx-auto h-4 w-4 opacity-80" />
                <p className="mt-2">{item.label}</p>
              </div>
            )
          })}
        </div>
      </aside>
    </section>
  )
}

