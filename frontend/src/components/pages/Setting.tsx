import {
  ArrowRight,
  BellRing,
  Check,
  LogOut,
  Palette,
  Repeat,
  TriangleAlert,
  User,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import bg from '../../assets/bg.png'
import bg2 from '../../assets/bg2.png'
import bg3 from '../../assets/bg3.png'
import bg4 from '../../assets/bg-reflect.png'
import avatar from '../../assets/avatar.png'
import { useAuth } from '../../hooks/useAuth'
import { ROUTE_PATHS } from '../../routes/paths'
import {
  APP_SETTINGS_UPDATED_EVENT,
  readAppSettings,
  saveAppSettings,
  updateAppMode,
  type AppearanceMode,
  type AppSettings,
  type ThemeOption,
} from '../../utils/appSettings'
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
  isDark: boolean
  onSelect: () => void
}

function ToggleRow({ title, description, checked, onChange }: ToggleRowProps) {
  const isDark = readAppSettings().mode === 'dark'
  return (
    <div className={`flex items-center justify-between rounded-3xl border ${isDark ? 'border-white/10 bg-white/30' : 'border-white/35 bg-white/30'} p-5 transition hover:bg-white/45 sm:p-6`}>
      <div className="pr-4">
        <p className="text-base font-semibold text-theme-text-primary sm:text-lg">{title}</p>
        <p className="mt-1 text-sm text-theme-text-primary">{description}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onChange} aria-label={title} />
    </div>
  )
}

function ThemeCard({ label, image, selected, isDark, onSelect }: ThemeCardProps) {
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
          selected ? 'border-serene-primary shadow-2xl border-3' : (isDark ? 'border-white/10' : 'border-transparent'),
        ].join(' ')}
      >
        <img src={image} alt={label} className="h-full w-full object-cover" />
      </div>
      <p
        className={[
          'mt-3 text-center text-[0.7rem] font-semibold uppercase tracking-[0.28em]',
          selected ? 'text-serene-primary' : (isDark ? 'text-theme-text-secondary' : 'text-serene-muted'),
        ].join(' ')}
      >
        {label}
      </p>
    </button>
  )
}

export default function Setting() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const initialSettings = readAppSettings()
  const [isDark, setIsDark] = useState(initialSettings.mode === 'dark')
  const [maskIdentity, setMaskIdentity] = useState(initialSettings.maskIdentity)
  const [shareData, setShareData] = useState(initialSettings.shareData)
  const [reminder, setReminder] = useState(initialSettings.reminder)
  const [weeklySummary, setWeeklySummary] = useState(initialSettings.weeklySummary)
  const [sosAccess, setSosAccess] = useState(initialSettings.sosAccess)
  const [selectedMode, setSelectedMode] = useState<AppearanceMode>(initialSettings.mode)
  const [selectedTheme, setSelectedTheme] = useState<ThemeOption>(initialSettings.theme)
  const [savedSettings, setSavedSettings] = useState(initialSettings)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  const displayName = user?.displayName || 'Lê Minh Anh'
  const email = user?.email || 'minhanh.le@serenemail.com'

  const previewTheme = (theme: ThemeOption) => {
    const previewSettings: AppSettings = {
      theme,
      mode: selectedMode,
      maskIdentity,
      shareData,
      reminder,
      weeklySummary,
      sosAccess,
    }
    window.dispatchEvent(
      new CustomEvent<AppSettings>(APP_SETTINGS_UPDATED_EVENT, {
        detail: previewSettings,
      }),
    )
  }

  const handleSaveChanges = () => {
    const settings = {
      theme: selectedTheme,
      mode: selectedMode,
      maskIdentity,
      shareData,
      reminder,
      weeklySummary,
      sosAccess,
    }

    saveAppSettings(settings)
    toast.success('Cài đặt đã được lưu thành công!')
    setSavedSettings(settings)
  }

  const handleCancel = () => {
    const settings = savedSettings
    setSelectedTheme(settings.theme)
    setSelectedMode(settings.mode)
    setMaskIdentity(settings.maskIdentity)
    setShareData(settings.shareData)
    setReminder(settings.reminder)
    setWeeklySummary(settings.weeklySummary)
    setSosAccess(settings.sosAccess)
    previewTheme(settings.theme)
  }

  const handleLogout = async () => {
    setIsLoggingOut(true)
    try {
      await logout()
      toast.success('Đăng xuất thành công')
      navigate(ROUTE_PATHS.landing, { replace: true })
    } catch {
      toast.error('Không thể đăng xuất. Vui lòng thử lại.')
    } finally {
      setIsLoggingOut(false)
    }
  }

  return (
    <div className={`relative min-h-full text-theme-text-primary transition-colors duration-200`}>
      <div className="mx-auto flex w-full max-w-4xl flex-col items-center px-0 pb-10 pt-2 sm:px-3 lg:pb-14 lg:pt-4">
        <div className={`w-full rounded-4xl border ${isDark ? 'border-white/10 bg-black/40' : 'border-white/50 bg-white/50'} px-5 py-6 shadow-md backdrop-blur-2xl sm:px-8 sm:py-8 lg:px-10 lg:py-10`}>
          <header className="text-center">
            <h1 className={`font-display text-5xl font-light leading-tight ${isDark ? 'text-white' : 'text-serene-ink'} sm:text-6xl lg:text-7xl`}>
              Cài đặt
            </h1>
            <p className={`mt-3 text-[0.68rem] uppercase tracking-[0.34em] ${isDark ? 'text-white/60' : 'text-serene-muted/75'}`}>
              Digital Sanctuary Configuration
            </p>
          </header>

          <section id='user-profile' className="mt-10 space-y-6">
            <div className={`flex items-center gap-2 border-b ${isDark ? 'border-white/10' : 'border-serene-ink/5'} pb-2`}>
              <User className="h-5 w-5 text-serene-primary" />
              <h2 className={`font-display text-2xl ${isDark ? 'text-white' : 'text-serene-ink'}`}>Hồ sơ cá nhân</h2>
            </div>

            <div className={`flex flex-col gap-6 rounded-3xl border ${isDark ? 'border-white/10 bg-white/30' : 'border-white/35 bg-white/35'} p-6 sm:flex-row sm:items-center sm:p-8`}>
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

              <div className="space-y-2 text-center sm:text-left flex-1">
                <p className={`font-display text-3xl italic ${isDark ? 'text-white' : 'text-serene-ink'} sm:text-4xl`}>{displayName}</p>
                <p className={`text-sm ${isDark ? 'text-theme-text-secondary' : 'text-serene-muted'} sm:text-base`}>{email}</p>
                <span className="rounded-full border border-serene-outline/30 bg-green-500/20 px-4 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-green-600">
                  Verified
                </span>
              </div>
              <div className=''>
                <Link to={ROUTE_PATHS.profile} className="inline-flex gap-3 items-center rounded-full bg-serene-primary px-4 py-2 text-xs font-medium uppercase tracking-[0.22em] text-serene-on-primary transition hover:brightness-105">
                  Xem chi tiết
                  <ArrowRight />
                </Link>
              </div>
            </div>
          </section>

          <section className="mt-12 space-y-6">
            <div className={`flex items-center gap-2 border-b ${isDark ? 'border-white/10' : 'border-serene-ink/5'} pb-2`}>
              <Palette className="h-5 w-5 text-serene-primary" />
              <h2 className={`font-display text-2xl ${isDark ? 'text-white' : 'text-serene-ink'}`}>Giao diện</h2>
            </div>

            <div className="grid gap-4">
              <ToggleRow
                title="Chế độ tối"
                description="Bật để dùng tông màu tối cho giao diện chính."
                checked={selectedMode === 'dark'}
                onChange={(checked) => {
                  const nextMode: AppearanceMode = checked ? 'dark' : 'light'
                  setSelectedMode(nextMode)
                  setIsDark(checked)
                  setSavedSettings((prev) => ({ ...prev, mode: nextMode }))
                  updateAppMode(nextMode)
                }}
              />
            </div>

            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 lg:gap-6">
              <ThemeCard
                label="Sunset Ocean"
                image={bg}
                selected={selectedTheme === 'sunset'}
                isDark={isDark}
                onSelect={() => {
                  setSelectedTheme('sunset')
                  previewTheme('sunset')
                }}
              />
              <ThemeCard
                label="Blue Ocean"
                image={bg4}
                selected={selectedTheme === 'ocean'}
                isDark={isDark}
                onSelect={() => {
                  setSelectedTheme('ocean')
                  previewTheme('ocean')
                }}
              />
              <ThemeCard
                label="Dawn Sky"
                image={bg2}
                selected={selectedTheme === 'dawn'}
                isDark={isDark}
                onSelect={() => {
                  setSelectedTheme('dawn')
                  previewTheme('dawn')
                }}
              />
              <ThemeCard
                label="Night Sky"
                image={bg3}
                selected={selectedTheme === 'night'}
                isDark={isDark}
                onSelect={() => {
                  setSelectedTheme('night')
                  previewTheme('night')
                }}
              />
            </div>
          </section>

          <section className="mt-12 space-y-6">
            <div className={`flex items-center gap-2 border-b ${isDark ? 'border-white/10' : 'border-serene-ink/5'} pb-2`}>
              <BellRing className="h-5 w-5 text-serene-primary" />
              <h2 className={`font-display text-2xl ${isDark ? 'text-white' : 'text-serene-ink'}`}>Thông báo</h2>
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

          <section className={`my-12`}>
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

          <section className="mt-12 space-y-6 ">
            <div className={`flex items-center gap-2 border-b ${isDark ? 'border-white/10' : 'border-serene-ink/5'} pb-2`}>
              <Repeat className="h-5 w-5 text-serene-primary" />
              <h2 className={`font-display text-2xl ${isDark ? 'text-white' : 'text-serene-ink'}`}>Cá nhân hóa Onboarding</h2>
            </div>
            <div className={`rounded-3xl border ${isDark ? 'border-white/10 bg-white/40' : 'border-white/35 bg-white/35'} p-6 `}>
              <p className={`text-sm ${isDark ? 'text-theme-text-secondary' : 'text-serene-muted'}`}>
                Bạn có thể chạy lại onboarding để cập nhật mục tiêu, khung giờ sinh hoạt và gợi ý trong phần
                {' '}
                “Hôm nay của bạn”.
              </p>
              <button
                type="button"
                onClick={() => navigate(ROUTE_PATHS.onboarding)}
                className="mt-4 rounded-full bg-serene-primary px-6 py-3 text-xs font-bold uppercase tracking-[0.22em] text-serene-on-primary transition hover:brightness-105"
              >
                Mở lại onboarding
              </button>
            </div>
          </section>

          <section className="mt-8 text-center">
            <button
              type="button"
              onClick={() => void handleLogout()}
              disabled={isLoggingOut}
              className="inline-flex gap-2 items-center mt-4 rounded-full bg-red-600 px-6 py-3 text-xs font-bold uppercase tracking-[0.22em] text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-70"
            >
              <LogOut className="h-5 w-5 " />
              {isLoggingOut ? 'Đang đăng xuất...' : 'Đăng xuất '}
            </button>

          </section>

          {/*nếu có thay đổi thì mới hiện*/}

          {(maskIdentity !== savedSettings.maskIdentity ||
            shareData !== savedSettings.shareData ||
            reminder !== savedSettings.reminder ||
            weeklySummary !== savedSettings.weeklySummary ||
            sosAccess !== savedSettings.sosAccess ||
            selectedMode !== savedSettings.mode ||
            selectedTheme !== savedSettings.theme) && (
              <footer className={`mt-12 flex flex-col-reverse gap-3 border-t ${isDark ? 'border-white/10' : 'border-serene-ink/5'} pt-8 sm:flex-row sm:justify-end sm:gap-5`}>
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
            )}
        </div>


      </div>
    </div>
  )
}