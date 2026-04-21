import {
  BellRing,
  Check,
  Palette,
  Shield,
  TriangleAlert,
  User,
} from 'lucide-react'
import { useState } from 'react'
import bg from '../../assets/bg.png'
import bg2 from '../../assets/bg2.png'
import bg3 from '../../assets/bg3.png'
import forest from '../../assets/forest.png'
import { useAuth } from '../../hooks/useAuth'

type ToggleRowProps = {
  title: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
  tone?: 'primary' | 'danger'
}

type ThemeCardProps = {
  label: string
  image: string
  selected: boolean
  onSelect: () => void
}

function ToggleRow({ title, description, checked, onChange, tone = 'primary' }: ToggleRowProps) {
  const activeColor = tone === 'danger' ? 'bg-red-500' : 'bg-serene-primary'

  return (
    <div className="flex items-center justify-between rounded-3xl border border-white/35 bg-white/30 p-5 transition hover:bg-white/45 sm:p-6">
      <div className="pr-4">
        <p className="text-base font-medium text-serene-ink sm:text-lg">{title}</p>
        <p className="mt-1 text-sm text-serene-muted">{description}</p>
      </div>
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={`relative h-7 w-14 rounded-full transition ${checked ? activeColor : 'bg-serene-outline/30'}`}
        aria-pressed={checked}
        aria-label={title}
      >
        <span
          className={[
            'absolute top-0.5 h-6 w-6 rounded-full bg-white shadow-sm transition-transform duration-200',
            checked ? 'translate-x-7' : 'translate-x-1',
          ].join(' ')}
        />
      </button>
    </div>
  )
}

function ThemeCard({ label, image, selected, onSelect }: ThemeCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="group text-left"
      aria-pressed={selected}
    >
      <div
        className={[
          'aspect-16/10 overflow-hidden rounded-3xl border-2 group-hover:scale-[1.02]',
          selected ? 'border-serene-primary shadow-2xl border-3' : 'border-transparent',
        ].join(' ')}
      >
        <img src={image} alt={label} className="h-full w-full object-cover" />
      </div>
      <p
        className={[
          'mt-3 text-center text-[0.7rem] font-semibold uppercase tracking-[0.28em]',
          selected ? 'text-serene-primary' : 'text-serene-muted',
        ].join(' ')}
      >
        {label}
      </p>
    </button>
  )
}

export default function Setting() {
  const { user } = useAuth()
  const [maskIdentity, setMaskIdentity] = useState(true)
  const [shareData, setShareData] = useState(false)
  const [reminder, setReminder] = useState(true)
  const [weeklySummary, setWeeklySummary] = useState(true)
  const [sosAccess, setSosAccess] = useState(false)
  const [selectedTheme, setSelectedTheme] = useState('sunset')

  const displayName = user?.displayName || 'Lê Minh Anh'
  const email = user?.email || 'minhanh.le@serenemail.com'

  return (
    <div className="relative min-h-full text-serene-ink">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center px-0 pb-10 pt-2 sm:px-3 lg:pb-14 lg:pt-4">
        <div className="w-full rounded-4xl border border-white/40 bg-white/40 px-5 py-6 shadow-[0_30px_90px_rgba(47,52,46,0.12)] backdrop-blur-2xl sm:px-8 sm:py-8 lg:px-10 lg:py-10">
          <header className="text-center">
            <h1 className="font-display text-5xl font-light leading-tight text-serene-ink sm:text-6xl lg:text-7xl">
              Cài đặt
            </h1>
            <p className="mt-3 text-[0.68rem] uppercase tracking-[0.34em] text-serene-muted/75">
              Digital Sanctuary Configuration
            </p>
          </header>

          <section className="mt-10 space-y-6">
            <div className="flex items-center gap-2 border-b border-serene-ink/5 pb-2">
              <User className="h-4 w-4 text-serene-primary" />
              <h2 className="font-display text-2xl text-serene-ink">Hồ sơ cá nhân</h2>
            </div>

            <div className="flex flex-col gap-6 rounded-3xl border border-white/35 bg-white/35 p-6 sm:flex-row sm:items-center sm:p-8">
              <div className="relative h-28 w-28 shrink-0 overflow-hidden rounded-full border-4 border-white/60 bg-linear-to-br from-serene-primary to-[#89a794] shadow-[0_18px_40px_rgba(47,52,46,0.18)]">
                <div className="flex h-full w-full items-center justify-center bg-black/10 text-4xl font-display italic text-white/95">
                  {displayName.charAt(0)}
                </div>
                <button
                  type="button"
                  className="absolute bottom-2 right-2 flex h-9 w-9 items-center justify-center rounded-full bg-serene-primary text-serene-on-primary shadow-lg transition hover:brightness-110"
                  aria-label="Chỉnh sửa ảnh hồ sơ"
                >
                  <Check className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-2 text-center sm:text-left">
                <p className="font-display text-3xl italic text-serene-ink sm:text-4xl">{displayName}</p>
                <p className="text-sm text-serene-muted sm:text-base">{email}</p>
                <div className="flex flex-wrap items-center justify-center gap-2 pt-2 sm:justify-start">
                  <span className="rounded-full border border-serene-primary/20 bg-serene-accent/25 px-4 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-serene-primary">
                    Premium Member
                  </span>
                  <span className="rounded-full border border-serene-outline/30 bg-serene-surface/80 px-4 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-serene-muted">
                    Verified
                  </span>
                </div>
              </div>
            </div>
          </section>

          <section className="mt-12 space-y-6">
            <div className="flex items-center gap-2 border-b border-serene-ink/5 pb-2">
              <Shield className="h-4 w-4 text-serene-primary" />
              <h2 className="font-display text-2xl text-serene-ink">Quyền riêng tư &amp; Bảo mật</h2>
            </div>

            <div className="grid gap-4">
              <ToggleRow
                title="Ẩn danh tính (PII Masking)"
                description="Tự động che thông tin cá nhân trong nhật ký tâm sự."
                checked={maskIdentity}
                onChange={setMaskIdentity}
              />
              <ToggleRow
                title="Chia sẻ dữ liệu"
                description="Giúp chúng tôi cải thiện trải nghiệm bằng dữ liệu ẩn danh."
                checked={shareData}
                onChange={setShareData}
              />
            </div>
          </section>

          <section className="mt-12 space-y-6">
            <div className="flex items-center gap-2 border-b border-serene-ink/5 pb-2">
              <Palette className="h-4 w-4 text-serene-primary" />
              <h2 className="font-display text-2xl text-serene-ink">Giao diện</h2>
            </div>

            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 lg:gap-6">
              <ThemeCard
                label="Sunset Ocean"
                image={bg}
                selected={selectedTheme === 'sunset'}
                onSelect={() => setSelectedTheme('sunset')}
              />
              <ThemeCard
                label="Misty Forest"
                image={forest}
                selected={selectedTheme === 'forest'}
                onSelect={() => setSelectedTheme('forest')}
              />
              <ThemeCard
                label="Dawn Sky"
                image={bg2}
                selected={selectedTheme === 'dawn'}
                onSelect={() => setSelectedTheme('dawn')}
              />
              <ThemeCard
                label="Night Sky"
                image={bg3}
                selected={selectedTheme === 'night'}
                onSelect={() => setSelectedTheme('night')}
              />
            </div>
          </section>

          <section className="mt-12 space-y-6">
            <div className="flex items-center gap-2 border-b border-serene-ink/5 pb-2">
              <BellRing className="h-4 w-4 text-serene-primary" />
              <h2 className="font-display text-2xl text-serene-ink">Thông báo</h2>
            </div>

            <div className="grid gap-4">
              <ToggleRow
                title="Nhắc nhở Serene"
                description="Thông báo nhắc nhở thiền định và hít thở hàng ngày."
                checked={reminder}
                onChange={setReminder}
              />
              <ToggleRow
                title="Cảnh báo Ghi chú Tuần"
                description="Tổng kết những khoảnh khắc phản chiếu trong tuần."
                checked={weeklySummary}
                onChange={setWeeklySummary}
              />
            </div>
          </section>

          <section className="mt-12 rounded-[1.5rem] border border-red-500/20 bg-red-500/8 p-6 backdrop-blur-sm sm:p-8">
            <div className="mb-6 flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 text-red-600">
                <TriangleAlert className="h-6 w-6" />
              </div>
              <h2 className="font-display text-2xl text-red-950">Trợ giúp Khẩn cấp</h2>
            </div>

            <ToggleRow
              title="Truy cập nhanh SOS"
              description="Hiển thị nút hỗ trợ khẩn cấp trên màn hình chính."
              checked={sosAccess}
              onChange={setSosAccess}
              tone="danger"
            />
          </section>

          <footer className="mt-12 flex flex-col-reverse gap-3 border-t border-serene-ink/5 pt-8 sm:flex-row sm:justify-end sm:gap-5">
            <button
              type="button"
              className="rounded-full px-8 py-3 text-xs font-medium uppercase tracking-[0.28em] text-serene-primary transition hover:bg-serene-primary/5"
            >
              Hủy bỏ
            </button>
            <button
              type="button"
              className="rounded-full bg-serene-primary px-10 py-4 text-xs font-bold uppercase tracking-[0.28em] text-serene-on-primary shadow-[0_18px_36px_rgba(47,52,46,0.18)] transition hover:brightness-105"
            >
              Lưu thay đổi
            </button>
          </footer>
        </div>


      </div>
    </div>
  )
}