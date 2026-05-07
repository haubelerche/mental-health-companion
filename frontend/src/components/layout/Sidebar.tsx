import { type MouseEvent } from 'react'
import { Bell, HelpCircle, HomeIcon, Library, MessageSquare, Sailboat, Settings, Sparkles, Utensils } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { ROUTE_PATHS } from '../../routes/paths'
import { useThemeContext } from '../../contexts/ThemeContext'
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

    { icon: Utensils, label: 'Dinh dưỡng', route: ROUTE_PATHS.nutrition },
    { icon: Sailboat, label: 'Thư', route: ROUTE_PATHS.bamboo },
]

export default function Sidebar({ isOpen, onHide, onReveal }: SidebarProps) {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const sidebarContainerClass = isDark
        ? 'border-white/20 bg-black/30 text-white'
        : 'border-black/15 bg-white/55 text-serene-ink'
    const secondaryTextClass = isDark ? 'text-white/75' : 'text-serene-muted/85'
    const hoverTextClass = isDark ? 'hover:bg-white/15 hover:text-white' : 'hover:bg-white/65 hover:text-serene-ink'
    const activeNavClass = isDark
        ? 'bg-white/20 text-white shadow-[0_4px_16px_rgba(0,0,0,0.35)]'
        : 'bg-serene-primary/90 text-serene-on-primary shadow-[0_4px_16px_rgba(77,99,89,0.3)]'
    const defaultNavClass = isDark ? `text-white/75 ${hoverTextClass}` : `text-serene-muted ${hoverTextClass}`
    const iconBadgeClass = isDark ? 'bg-white/15 group-hover:bg-white/25' : 'bg-serene-primary/8 group-hover:bg-white/60'

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
                    sidebarContainerClass,
                    isOpen ? 'translate-x-0' : '-translate-x-full',
                ].join(' ')}
            >
                {/* Brand */}
                <div className="mb-7">
                    <h1 className="font-display text-4xl italic">Serene</h1>
                    <p className={`mt-2 text-xs uppercase tracking-[0.24em] ${secondaryTextClass}`}>
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
                                            ? activeNavClass
                                            : defaultNavClass,
                                    ].join(' ')
                                }
                            >
                                {({ isActive }) => (
                                    <>
                                        <span
                                            className={[
                                                'flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-xl transition-colors',
                                                isActive ? 'bg-white/20' : iconBadgeClass,
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
                <div className={`mt-4 space-y-1 border-t pt-4 text-base ${isDark ? 'border-white/20 text-white/75' : 'border-black/10 text-serene-muted'}`}>
                    <NavLink
                        to={ROUTE_PATHS.notifications}
                        className={`flex items-center gap-3 rounded-xl px-3 py-2.5 transition ${hoverTextClass}`}
                    >
                        <Bell className="h-4 w-4" aria-hidden="true" />
                        <span>Thông báo</span>
                    </NavLink>
                    <NavLink
                        to={ROUTE_PATHS.setting}
                        className={`flex items-center gap-3 rounded-xl px-3 py-2.5 transition ${hoverTextClass}`}
                    >
                        <Settings className="h-4 w-4" aria-hidden="true" />
                        <span>Cài đặt</span>
                    </NavLink>
                    <NavLink
                        to={ROUTE_PATHS.support}
                        className={`flex items-center gap-3 rounded-xl px-3 py-2.5 transition ${hoverTextClass}`}
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
            <nav className={`fixed bottom-4 left-1/2 z-50 flex w-[min(94vw,560px)] -translate-x-1/2 items-center justify-between rounded-3xl border px-3 py-2 shadow-[0_8px_32px_rgba(47,52,46,0.14)] backdrop-blur-xl lg:hidden ${isDark ? 'border-white/25 bg-black/55' : 'border-white/45 bg-white/75'}`}>
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
                                        ? (isDark ? 'bg-white/20 text-white' : 'bg-serene-primary/10 text-serene-primary')
                                        : (isDark ? 'text-white/75 hover:text-white' : 'text-serene-muted/70 hover:text-serene-ink'),
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