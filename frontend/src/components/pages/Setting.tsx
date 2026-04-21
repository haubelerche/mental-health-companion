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
import bg4 from '../../assets/bg-reflect.png'
import avatar from '../../assets/avatar.png'
import { useAuth } from '../../hooks/useAuth'
import { readAppSettings, saveAppSettings, type ThemeOption } from '../../utils/appSettings'
import { Switch } from '../ui/switch'
import { toast } from 'react-toastify'

type ToggleRowProps = {
  title: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
}

type ThemeCardProps = {
  label: string
  image: string
  selected: boolean
  onSelect: () => void
}

function ToggleRow({ title, description, checked, onChange }: ToggleRowProps) {
  return (
    <div className="flex items-center justify-between rounded-3xl border border-white/35 bg-white/30 p-5 transition hover:bg-white/45 sm:p-6">
      <div className="pr-4">
        <p className="text-base font-medium text-serene-ink sm:text-lg">{title}</p>
        <p className="mt-1 text-sm text-serene-muted">{description}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onChange} aria-label={title} />
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
  const initialSettings = readAppSettings()
  const [maskIdentity, setMaskIdentity] = useState(initialSettings.maskIdentity)
  const [shareData, setShareData] = useState(initialSettings.shareData)
  const [reminder, setReminder] = useState(initialSettings.reminder)
  const [weeklySummary, setWeeklySummary] = useState(initialSettings.weeklySummary)
  const [sosAccess, setSosAccess] = useState(initialSettings.sosAccess)
  const [selectedTheme, setSelectedTheme] = useState<ThemeOption>(initialSettings.theme)

  const displayName = user?.displayName || 'Lê Minh Anh'
  const email = user?.email || 'minhanh.le@serenemail.com'

  const handleSaveChanges = () => {
    const settings = {
      theme: selectedTheme,
      maskIdentity,
      shareData,
      reminder,
      weeklySummary,
      sosAccess,
    }

    saveAppSettings(settings)
    toast.success('Cài đặt đã được lưu thành công!')
    scrollTo({ top: 0, behavior: 'smooth' }) // cuộn lên đầu trang để người dùng thấy thông báo
    console.log('Saved setting states:', settings)
  }

  const handleCancel = () => {
    const settings = readAppSettings()
    setSelectedTheme(settings.theme)
    setMaskIdentity(settings.maskIdentity)
    setShareData(settings.shareData)
    setReminder(settings.reminder)
    setWeeklySummary(settings.weeklySummary)
    setSosAccess(settings.sosAccess)
  }

  return (
    <div className="relative min-h-full text-serene-ink">
      <div className="mx-auto flex w-full max-w-4xl flex-col items-center px-0 pb-10 pt-2 sm:px-3 lg:pb-14 lg:pt-4">
        <div className="w-full rounded-4xl border border-white/40 bg-white/40 px-5 py-6 shadow-md backdrop-blur-2xl sm:px-8 sm:py-8 lg:px-10 lg:py-10">
          <header className="text-center">
            <h1 className="font-display text-5xl font-light leading-tight text-serene-ink sm:text-6xl lg:text-7xl">
              Cài đặt
            </h1>
            <p className="mt-3 text-[0.68rem] uppercase tracking-[0.34em] text-serene-muted/75">
              Digital Sanctuary Configuration
            </p>
          </header>

          <section id='user-profile' className="mt-10 space-y-6">
            <div className="flex items-center gap-2 border-b border-serene-ink/5 pb-2">
              <User className="h-5 w-5 text-serene-primary" />
              <h2 className="font-display text-2xl text-serene-ink">Hồ sơ cá nhân</h2>
            </div>

            <div className="flex flex-col gap-6 rounded-3xl border border-white/35 bg-white/35 p-6 sm:flex-row sm:items-center sm:p-8">
              <div className="relative h-28 w-28 shrink-0">
                <img
                  src={avatar}
                  alt="Ảnh hồ sơ"
                  className="rounded-full border-2 border-white/70 object-cover"
                />
                <button
                  type="button"
                  className="absolute bottom-2 right-2 flex h-9 w-9 items-center justify-center rounded-full bg-serene-primary text-serene-on-primary shadow-lg transition hover:brightness-110"
                  aria-label="Chỉnh sửa ảnh hồ sơ"
                >
                  <Check className="h-5 w-5" />
                </button>
              </div>

              <div className="space-y-2 text-center sm:text-left">
                <p className="font-display text-3xl italic text-serene-ink sm:text-4xl">{displayName}</p>
                <p className="text-sm text-serene-muted sm:text-base">{email}</p>
                <span className="rounded-full border border-serene-outline/30 bg-green-500/20 px-4 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-green-600">
                  Verified
                </span>
              </div>
            </div>
          </section>

          <section className="mt-12 space-y-6">
            <div className="flex items-center gap-2 border-b border-serene-ink/5 pb-2">
              <Shield className="h-5 w-5 text-serene-primary" />
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
              <Palette className="h-5 w-5 text-serene-primary" />
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
                label="Blue Ocean"
                image={bg4}
                selected={selectedTheme === 'ocean'}
                onSelect={() => setSelectedTheme('ocean')}
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
              <BellRing className="h-5 w-5 text-serene-primary" />
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

          <section className="mt-12 rounded-3xl  p-6 backdrop-blur-sm sm:p-8">
            <div className="mb-6 flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-600/20 text-red-600">
                <TriangleAlert className="h-6 w-6" />
              </div>
              <h2 className="font-display text-2xl text-red-600">Trợ giúp Khẩn cấp</h2>
            </div>

            <ToggleRow
              title="Truy cập nhanh SOS"
              description="Hiển thị nút hỗ trợ khẩn cấp trên màn hình chính."
              checked={sosAccess}
              onChange={setSosAccess}
            />
          </section>

          <footer className="mt-12 flex flex-col-reverse gap-3 border-t border-serene-ink/5 pt-8 sm:flex-row sm:justify-end sm:gap-5">
            <button
              type="button"
              onClick={handleCancel}
              className="rounded-full px-8 py-3 text-xs font-medium uppercase tracking-[0.28em] text-serene-primary transition hover:bg-serene-primary/5"
            >
              Hủy bỏ
            </button>
            <button
              type="button"
              onClick={handleSaveChanges}
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