import { useEffect, useState, type MouseEvent } from 'react'
import { Bell, Book, Compass, HelpCircle, HomeIcon, Library, MessageSquare, Sailboat, Settings, Sparkles, Utensils } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { ROUTE_PATHS } from '../../routes/paths'
import {
    APP_SETTINGS_STORAGE_KEY,
    APP_SETTINGS_UPDATED_EVENT,
    readAppSettings,
    type AppSettings,
} from '../../utils/appSettings'


type SidebarProps = {
    isOpen: boolean
    onHide: () => void
    onReveal: () => void
}

const navItems = [
    { icon: HomeIcon, label: 'Trang chủ', route: ROUTE_PATHS.home },
    { icon: MessageSquare, label: 'Chat', route: ROUTE_PATHS.chat },
    { icon: Sparkles, label: 'Nhìn lại', route: ROUTE_PATHS.reflect },
    { icon: Library, label: 'Tài nguyên', route: ROUTE_PATHS.resources },
    { icon: Book, label: 'Bài tập', route: ROUTE_PATHS.exercises },
    { icon: Utensils, label: 'Dinh dưỡng', route: ROUTE_PATHS.nutrition },
    { icon: Compass, label: 'Kết nối', route: ROUTE_PATHS.connect },
    { icon: Sailboat, label: 'Thư', route: ROUTE_PATHS.bamboo },
]

export default function Sidebar({ isOpen, onHide, onReveal }: SidebarProps) {
    const [isDark, setIsDark] = useState(() => readAppSettings().mode === 'dark')

    useEffect(() => {
        const syncThemeMode = (settings: AppSettings) => {
            setIsDark(settings.mode === 'dark')
        }

        const handleSettingsUpdated = (event: Event) => {
            const customEvent = event as CustomEvent<AppSettings>
            if (customEvent.detail) {
                syncThemeMode(customEvent.detail)
            }
        }

        const handleStorageUpdated = (event: StorageEvent) => {
            if (event.key !== APP_SETTINGS_STORAGE_KEY) {
                return
            }
            syncThemeMode(readAppSettings())
        }

        window.addEventListener(APP_SETTINGS_UPDATED_EVENT, handleSettingsUpdated as EventListener)
        window.addEventListener('storage', handleStorageUpdated)
        return () => {
            window.removeEventListener(APP_SETTINGS_UPDATED_EVENT, handleSettingsUpdated as EventListener)
            window.removeEventListener('storage', handleStorageUpdated)
        }
    }, [])

    const handleSidebarBlankClick = (event: MouseEvent<HTMLElement>) => {
        const target = event.target as HTMLElement
        if (target.closest('a, button')) {
            return
        }

        onHide()
    }

    return (
        <>
            {/* ── Desktop sidebar ── */}
            <aside
                onClick={handleSidebarBlankClick}
                className={[
                    'fixed left-0 top-0 z-40 hidden h-full w-60 flex-col border-r p-6 backdrop-blur-3xl transition-transform duration-300 lg:flex',
                    'border-theme-border bg-theme-bg-primary text-theme-text-primary',
                    isOpen ? 'translate-x-0' : '-translate-x-full',
                ].join(' ')}
            >
                {/* Brand */}
                <div className="mb-7">
                    <h1 className="font-display text-4xl italic">Serene</h1>
                    <p className="mt-2 text-xs uppercase tracking-[0.24em] text-theme-text-secondary">
                        Digital Sanctuary
                    </p>
                </div>

                {/* Primary nav */}
                <nav className="flex flex-1 flex-col gap-1">
                    {navItems.map((item) => {
                        const Icon = item.icon
                        return (
                            <NavLink
                                key={item.label}
                                to={item.route}
                                end
                                className={({ isActive }) =>
                                    [
                                        'group flex items-center gap-3 rounded-2xl px-3.5 py-2.5 text-left transition-all duration-200',
                                        isActive
                                            ? 'bg-theme-accent/25 text-theme-accent shadow-[0_4px_16px_rgba(0,0,0,0.35)]'
                                            : 'text-theme-text-secondary hover:bg-theme-accent/10 hover:text-theme-text-primary',
                                    ].join(' ')
                                }
                            >
                                {({ isActive }) => (
                                    <>
                                        <span
                                            className={[
                                                'flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-xl transition-colors',
                                                isActive ? 'bg-theme-accent/20' : 'bg-theme-accent/10 group-hover:bg-theme-accent/15',
                                            ].join(' ')}
                                        >
                                            <Icon className="h-3.5 w-3.5" />
                                        </span>
                                        <span className="font-display text-[19px]">{item.label}</span>
                                    </>
                                )}
                            </NavLink>
                        )
                    })}
                </nav>

                {/* Bottom links */}
                <div className="mt-4 space-y-1 border-t border-theme-border/50 pt-4 text-base text-theme-text-secondary">
                    <button
                        type="button"
                        className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition hover:bg-theme-accent/10 hover:text-theme-text-primary"
                    >
                        <Bell className="h-4 w-4" aria-hidden="true" />
                        <span>Thông báo</span>
                    </button>
                    <NavLink
                        to={ROUTE_PATHS.setting}
                        className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition hover:bg-theme-accent/10 hover:text-theme-text-primary"
                    >
                        <Settings className="h-4 w-4" aria-hidden="true" />
                        <span>Cài đặt</span>
                    </NavLink>
                    <NavLink
                        to={ROUTE_PATHS.connect}
                        className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition hover:bg-theme-accent/10 hover:text-theme-text-primary"
                    >
                        <HelpCircle className="h-4 w-4" />
                        <span>Hỗ trợ</span>
                    </NavLink>
                </div>
            </aside>

            {!isOpen && (
                <div
                    className="fixed left-0 top-0 z-40 hidden h-screen w-4 cursor-e-resize lg:block"
                    onMouseEnter={onReveal}
                    aria-hidden="true"
                />
            )}

            {/* ── Mobile bottom nav ── */}
            <nav className="fixed bottom-4 left-1/2 z-50 flex w-[min(94vw,520px)] -translate-x-1/2 items-center justify-between rounded-3xl border px-3 py-2 shadow-[0_8px_32px_rgba(0,0,0,0.1)] backdrop-blur-xl border-theme-border bg-theme-bg-secondary/95 lg:hidden">
                {navItems.slice(0, 5).map((item) => {
                    const Icon = item.icon
                    return (
                        <NavLink
                            key={item.label}
                            to={item.route}
                            end
                            className={({ isActive }) =>
                                [
                                    'flex flex-1 flex-col items-center gap-1 rounded-2xl px-1 py-2 text-[12px] font-medium transition',
                                    isActive
                                        ? 'bg-theme-accent/15 text-theme-accent'
                                        : 'text-theme-text-secondary hover:text-theme-text-primary',
                                ].join(' ')
                            }
                        >
                            <Icon className="h-5 w-5" />
                            <span>{item.label}</span>
                        </NavLink>
                    )
                })}
            </nav>
        </>
    )
}
