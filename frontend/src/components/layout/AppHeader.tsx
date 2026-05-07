import { NavLink, useLocation } from 'react-router-dom'
import { HomeIcon, Library, MessageSquare, Settings, Sparkles, Utensils } from 'lucide-react'
import { ROUTE_PATHS } from '../../routes/paths'
import { ThemeToggle } from '../common/ThemeToggle'

const PAGE_NAMES: Record<string, string> = {
    [ROUTE_PATHS.home]: 'Trang chủ',
    [ROUTE_PATHS.chat]: 'Chat',
    [ROUTE_PATHS.reflect]: 'Nhìn lại',
    [ROUTE_PATHS.resources]: 'Tài nguyên',
    [ROUTE_PATHS.nutrition]: 'Dinh dưỡng',
    [ROUTE_PATHS.support]: 'Hỗ trợ',
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

    const pageName = PAGE_NAMES[location.pathname] ?? 'Serene'

    return (
        <>
            {/* ── Desktop header ── */}
            <header
                className="fixed left-0 right-0 top-0 z-40 hidden items-center justify-between px-8 py-5 backdrop-blur-md bg-theme-bg-secondary/40 md:flex"
            >
                {/* Top-left: page name */}
                <span
                    className="font-display text-xl italic tracking-wide text-theme-text-secondary"
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
                                        ? 'text-theme-accent underline underline-offset-[5px] decoration-1'
                                        : 'text-theme-text-secondary/50 hover:text-theme-text-primary'
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
                        className="text-theme-text-secondary/50 hover:text-theme-text-primary transition-opacity"
                    >
                        <Settings className="h-4 w-4" />
                    </NavLink>
                </div>
            </header>

            {/* ── Mobile: top bar ── */}
            <div
                className="fixed left-0 right-0 top-0 z-40 flex items-center justify-between px-5 py-4 backdrop-blur-md md:hidden bg-theme-bg-secondary/40"
            >
                <span
                    className="font-display text-base italic text-theme-text-secondary"
                >
                    {pageName}
                </span>
                <div className="flex items-center gap-3">
                    <ThemeToggle />
                    <NavLink
                        to={ROUTE_PATHS.setting}
                        aria-label="Cài đặt"
                        className="text-theme-text-secondary/50 hover:text-theme-text-primary transition-opacity"
                    >
                        <Settings className="h-4 w-4" />
                    </NavLink>
                </div>
            </div>

            {/* ── Mobile: bottom nav pill ── */}
            <nav
                className="fixed bottom-4 left-1/2 z-50 flex w-[min(94vw,520px)] -translate-x-1/2 items-center justify-between rounded-3xl border px-3 py-2 shadow-[0_8px_32px_rgba(0,0,0,0.1)] backdrop-blur-xl md:hidden border-theme-border bg-theme-bg-secondary/95"
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
                                        ? 'bg-theme-accent/15 text-theme-accent'
                                        : 'text-theme-text-secondary hover:text-theme-text-primary'
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
