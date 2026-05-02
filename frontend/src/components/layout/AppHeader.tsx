import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { HomeIcon, Library, MessageSquare, Settings, Sparkles, Utensils } from 'lucide-react'
import { ROUTE_PATHS } from '../../routes/paths'
import {
    APP_SETTINGS_STORAGE_KEY,
    APP_SETTINGS_UPDATED_EVENT,
    readAppSettings,
    type AppSettings,
} from '../../utils/appSettings'
import { ThemeToggle } from '../common/ThemeToggle'

const PAGE_NAMES: Record<string, string> = {
    [ROUTE_PATHS.home]: 'Trang chủ',
    [ROUTE_PATHS.chat]: 'Chat',
    [ROUTE_PATHS.reflect]: 'Nhìn lại',
    [ROUTE_PATHS.resources]: 'Tài nguyên',
    [ROUTE_PATHS.nutrition]: 'Dinh dưỡng',
    [ROUTE_PATHS.connect]: 'Kết nối',
    [ROUTE_PATHS.setting]: 'Cài đặt',
    [ROUTE_PATHS.checkin]: 'Check-in',
    [ROUTE_PATHS.exercises]: 'Bài tập',
    [ROUTE_PATHS.screening]: 'Khảo sát',
    [ROUTE_PATHS.results]: 'Kết quả',
    [ROUTE_PATHS.safetyCheck]: 'An toàn',
}

const DESKTOP_NAV = [
    { label: 'Trang chủ', route: ROUTE_PATHS.home },
    { label: 'Chat', route: ROUTE_PATHS.chat },
    { label: 'Nhìn lại', route: ROUTE_PATHS.reflect },
    { label: 'Tài nguyên', route: ROUTE_PATHS.resources },
    { label: 'Dinh dưỡng', route: ROUTE_PATHS.nutrition },
]

const MOBILE_NAV = [
    { icon: HomeIcon, label: 'Trang chủ', route: ROUTE_PATHS.home },
    { icon: MessageSquare, label: 'Chat', route: ROUTE_PATHS.chat },
    { icon: Sparkles, label: 'Nhìn lại', route: ROUTE_PATHS.reflect },
    { icon: Library, label: 'Tài nguyên', route: ROUTE_PATHS.resources },
    { icon: Utensils, label: 'Dinh dưỡng', route: ROUTE_PATHS.nutrition },
]

export function AppHeader() {
    const location = useLocation()
    const [isDark, setIsDark] = useState(() => readAppSettings().theme === 'night')

    useEffect(() => {
        const onSettings = (e: Event) => {
            const ce = e as CustomEvent<AppSettings>
            if (ce.detail) setIsDark(ce.detail.theme === 'night')
        }
        const onStorage = (e: StorageEvent) => {
            if (e.key === APP_SETTINGS_STORAGE_KEY) setIsDark(readAppSettings().theme === 'night')
        }
        window.addEventListener(APP_SETTINGS_UPDATED_EVENT, onSettings as EventListener)
        window.addEventListener('storage', onStorage)
        return () => {
            window.removeEventListener(APP_SETTINGS_UPDATED_EVENT, onSettings as EventListener)
            window.removeEventListener('storage', onStorage)
        }
    }, [])

    const pageName = PAGE_NAMES[location.pathname] ?? 'Serene'

    return (
        <>
            {/* ── Desktop header ── */}
            <header
                className={`fixed left-0 right-0 top-0 z-40 hidden items-center justify-between px-8 py-5 backdrop-blur-md md:flex ${
                    isDark ? 'bg-black/10' : 'bg-white/15'
                }`}
            >
                {/* Top-left: page name */}
                <span
                    className={`font-display text-xl italic tracking-wide ${
                        isDark ? 'text-white/75' : 'text-serene-ink/70'
                    }`}
                >
                    {pageName}
                </span>

                {/* Top-center: nav links */}
                <nav className="flex items-center gap-8">
                    {DESKTOP_NAV.map((item) => (
                        <NavLink
                            key={item.route}
                            to={item.route}
                            end
                            className={({ isActive }) =>
                                `font-display text-[15px] transition-all duration-150 ${
                                    isActive
                                        ? isDark
                                            ? 'text-white underline underline-offset-[5px] decoration-1'
                                            : 'text-serene-ink underline underline-offset-[5px] decoration-1'
                                        : isDark
                                            ? 'text-white/45 hover:text-white/80'
                                            : 'text-serene-ink/40 hover:text-serene-ink/80'
                                }`
                            }
                        >
                            {item.label}
                        </NavLink>
                    ))}
                </nav>

                {/* Top-right: settings & theme toggle */}
                <div className="flex items-center gap-3">
                    <ThemeToggle />
                    <NavLink
                        to={ROUTE_PATHS.setting}
                        aria-label="Cài đặt"
                        className={`transition-opacity ${
                            isDark ? 'text-white/45 hover:text-white/80' : 'text-serene-ink/40 hover:text-serene-ink/80'
                        }`}
                    >
                        <Settings className="h-4 w-4" />
                    </NavLink>
                </div>
            </header>

            {/* ── Mobile: top bar ── */}
            <div
                className={`fixed left-0 right-0 top-0 z-40 flex items-center justify-between px-5 py-4 backdrop-blur-md md:hidden ${
                    isDark ? 'bg-black/10' : 'bg-white/15'
                }`}
            >
                <span
                    className={`font-display text-base italic ${
                        isDark ? 'text-white/75' : 'text-serene-ink/70'
                    }`}
                >
                    {pageName}
                </span>
                <NavLink
                    to={ROUTE_PATHS.setting}
                    aria-label="Cài đặt"
                    className={isDark ? 'text-white/45 hover:text-white/75' : 'text-serene-ink/40 hover:text-serene-ink/75'}
                >
                    <Settings className="h-4 w-4" />
                </NavLink>
            </div>

            {/* ── Mobile: bottom nav pill ── */}
            <nav
                className={`fixed bottom-4 left-1/2 z-50 flex w-[min(94vw,520px)] -translate-x-1/2 items-center justify-between rounded-3xl border px-3 py-2 shadow-[0_8px_32px_rgba(47,52,46,0.14)] backdrop-blur-xl md:hidden ${
                    isDark ? 'border-white/25 bg-black/55' : 'border-white/45 bg-white/75'
                }`}
            >
                {MOBILE_NAV.map((item) => {
                    const Icon = item.icon
                    return (
                        <NavLink
                            key={item.route}
                            to={item.route}
                            end
                            className={({ isActive }) =>
                                `flex flex-1 flex-col items-center gap-1 rounded-2xl px-1 py-2 text-[12px] font-medium transition ${
                                    isActive
                                        ? isDark
                                            ? 'bg-white/20 text-white'
                                            : 'bg-serene-primary/10 text-serene-primary'
                                        : isDark
                                            ? 'text-white/75 hover:text-white'
                                            : 'text-serene-muted/70 hover:text-serene-ink'
                                }`
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
