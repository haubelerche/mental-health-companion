import {
  ArrowLeft,
  BellRing,
  ChevronRight,
  Gift,
  HelpCircle,
  LogOut,
  Palette,
  Repeat,
  User,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../hooks/useAuth'
import { ROUTE_PATHS } from '../../routes/paths'
import {
  readAppSettings,
  saveAppSettings,
  updateAppMode,
  type AppearanceMode,
} from '../../utils/appSettings'
import { Switch } from '../ui/switch'
import { toast } from 'react-toastify'
import { onboardingTourService } from '../../services/onboardingTourService'

type ToggleRowProps = {
  title: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
}

type TabId = 'main' | 'notifications' | 'appearance'

function ToggleRow({ title, description, checked, onChange }: ToggleRowProps) {
  return (
    <div className="flex items-center justify-between rounded-3xl border border-theme-secondary/20 bg-theme-surface/80 p-5 transition hover:bg-theme-surface/60 sm:p-6 shadow-sm">
      <div className="pr-4">
        <p className="text-base font-semibold text-theme-text-primary sm:text-lg">{title}</p>
        <p className="mt-1 text-sm text-theme-text-secondary">{description}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onChange} aria-label={title} />
    </div>
  )
}



function SettingMenuItem({ icon: Icon, title, description, onClick }: { icon: LucideIcon, title: string, description: string, onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex w-full cursor-pointer items-center justify-between rounded-2xl border border-theme-secondary/50 bg-theme-surface p-5 transition hover:bg-theme-accent/10 shadow-sm mb-3 text-left"
    >
      <div className="flex items-center gap-4">
        <Icon className="h-6 w-6 text-theme-text-primary shrink-0" />
        <div>
          <p className="text-base font-medium text-theme-text-primary">{title}</p>
          <p className="text-sm text-theme-text-secondary">{description}</p>
        </div>
      </div>
      <ChevronRight className="h-5 w-5 text-theme-text-secondary shrink-0" />
    </button>
  )
}

export default function Setting() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const initialSettings = readAppSettings()
  
  const [activeTab, setActiveTab] = useState<TabId>('main')
  
  const [maskIdentity, setMaskIdentity] = useState(initialSettings.maskIdentity)
  const [shareData, setShareData] = useState(initialSettings.shareData)
  const [reminder, setReminder] = useState(initialSettings.reminder)
  const [weeklySummary, setWeeklySummary] = useState(initialSettings.weeklySummary)
  const [selectedMode, setSelectedMode] = useState<AppearanceMode>(initialSettings.mode)
  const [savedSettings, setSavedSettings] = useState(initialSettings)
  const [isLoggingOut, setIsLoggingOut] = useState(false)


  const handleSaveChanges = () => {
    const settings = {
      ...savedSettings,
      maskIdentity,
      shareData,
      reminder,
      weeklySummary,
      mode: selectedMode,
    }

    saveAppSettings(settings)
    toast.success('Cài đặt đã được lưu thành công!')
    setSavedSettings(settings)
  }

  const handleCancel = () => {
    const settings = savedSettings
    setMaskIdentity(settings.maskIdentity)
    setShareData(settings.shareData)
    setReminder(settings.reminder)
    setWeeklySummary(settings.weeklySummary)
    setSelectedMode(settings.mode)
    updateAppMode(settings.mode)
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

  const handleReplayTour = async () => {
    try {
      await onboardingTourService.start('first_run')
      navigate(`${ROUTE_PATHS.home}?tour=replay`)
    } catch {
      toast.error('Không thể mở lại hướng dẫn lúc này. Vui lòng thử lại.')
    }
  }



  const renderNotifications = () => (
    <section className="space-y-6">
      <div className="flex items-center gap-2 border-b border-theme-border/30 pb-2">
        <BellRing className="h-5 w-5 text-theme-accent" />
        <h2 className="font-display text-2xl text-theme-text-primary">Thông báo</h2>
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
  )

  const renderAppearance = () => (
    <section className="space-y-6">
      <div className="flex items-center gap-2 border-b border-theme-border/30 pb-2">
        <Palette className="h-5 w-5 text-theme-accent" />
        <h2 className="font-display text-2xl text-theme-text-primary">Giao diện</h2>
      </div>

      <div className="grid gap-4">
        <ToggleRow
          title="Chế độ tối"
          description="Bật để dùng tông màu tối cho giao diện chính."
          checked={selectedMode === 'dark'}
          onChange={(checked) => {
            const nextMode: AppearanceMode = checked ? 'dark' : 'light'
            setSelectedMode(nextMode)
            setSavedSettings((prev) => ({ ...prev, mode: nextMode }))
            updateAppMode(nextMode)
          }}
        />
      </div>
    </section>
  )

  return (
    <div className="relative min-h-full text-theme-text-primary transition-colors duration-200">
      <div className="mx-auto flex w-full max-w-4xl flex-col items-center px-0 pb-10 pt-2 sm:px-3 lg:pb-14 lg:pt-4">
        
        {activeTab !== 'main' && (
          <div className="w-full mb-6 flex justify-start">
            <button
              onClick={() => setActiveTab('main')}
              className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium text-theme-text-secondary cursor-pointer bg-theme-surface hover:text-theme-text-primary"
            >
              <ArrowLeft className="h-4 w-4" />
              Quay lại danh mục
            </button>
          </div>
        )}

        <div className="w-full rounded-4xl border border-theme-border bg-theme-surface/80 px-5 py-6 shadow-xl backdrop-blur-2xl sm:px-8 sm:py-8 lg:px-10 lg:py-10">
          
          {activeTab === 'main' ? (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
              <header className="mb-10 text-center">
                <h1 className="font-display text-5xl font-light leading-tight text-theme-text-primary sm:text-6xl lg:text-7xl">
                  Cài đặt
                </h1>
                <p className="mt-3 text-[0.68rem] uppercase tracking-[0.34em] text-theme-text-secondary/70">
                  Digital Sanctuary Configuration
                </p>
              </header>

              <div className="space-y-1">
                <SettingMenuItem
                  icon={User}
                  title="Hồ sơ cá nhân"
                  description="Quản lý thông tin tài khoản và danh tính của bạn"
                  onClick={() => navigate(ROUTE_PATHS.profile)}
                />
                <SettingMenuItem
                  icon={Gift}
                  title="Cửa hàng Thưởng"
                  description="Xem số dư Tim và mở khóa vật phẩm"
                  onClick={() => navigate(ROUTE_PATHS.rewards)}
                />
                <SettingMenuItem
                  icon={BellRing}
                  title="Thông báo"
                  description="Nhắc nhở thiền định và tổng kết tuần"
                  onClick={() => setActiveTab('notifications')}
                />
                <SettingMenuItem
                  icon={Palette}
                  title="Giao diện"
                  description="Chế độ sáng/tối"
                  onClick={() => setActiveTab('appearance')}
                />

                <SettingMenuItem
                  icon={Repeat}
                  title="Cá nhân hóa Onboarding"
                  description="Cập nhật mục tiêu và khung giờ sinh hoạt"
                  onClick={() => navigate(ROUTE_PATHS.onboarding)}
                />
                <SettingMenuItem
                  icon={HelpCircle}
                  title="Xem lại hướng dẫn"
                  description="Hau dẫn bạn đi lại một vòng trong app"
                  onClick={() => void handleReplayTour()}
                />
              </div>

              <section className="mt-10 text-center">
                <button
                  type="button"
                  onClick={() => void handleLogout()}
                  disabled={isLoggingOut}
                  className="inline-flex gap-2 items-center rounded-full bg-red-600 px-6 py-3 text-xs font-bold uppercase tracking-[0.22em] text-red-50 transition hover:bg-red-600/20 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <LogOut className="h-5 w-5 " />
                  {isLoggingOut ? 'Đang đăng xuất...' : 'Đăng xuất '}
                </button>
              </section>
            </div>
          ) : (
            <div className="animate-in fade-in slide-in-from-right-4 duration-300">
              {activeTab === 'notifications' && renderNotifications()}
              {activeTab === 'appearance' && renderAppearance()}
            </div>
          )}

          {(maskIdentity !== savedSettings.maskIdentity ||
            shareData !== savedSettings.shareData ||
            reminder !== savedSettings.reminder ||
            weeklySummary !== savedSettings.weeklySummary ||
            selectedMode !== savedSettings.mode) && (
              <footer className="mt-12 flex flex-col-reverse gap-3 border-t border-theme-border/30 pt-8 sm:flex-row sm:justify-end sm:gap-5">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="rounded-full px-8 py-3 text-xs font-medium uppercase tracking-[0.28em] text-theme-accent transition hover:bg-theme-accent/5"
                >
                  Hủy bỏ
                </button>
                <button
                  type="button"
                  onClick={handleSaveChanges}
                  className="rounded-full bg-theme-accent px-10 py-4 text-xs font-bold uppercase tracking-[0.28em] text-white shadow-lg transition hover:brightness-105"
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
