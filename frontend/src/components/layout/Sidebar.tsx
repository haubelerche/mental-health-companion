import { type MouseEvent, useEffect, useState } from 'react'
import { Bell, HelpCircle, HomeIcon, Library, MessageSquare, Sailboat, Settings, Sparkles, Utensils, Gift, MoreHorizontal, ChevronLeft, ChevronRight } from 'lucide-react'
import { Link, NavLink } from 'react-router-dom'
import { ROUTE_PATHS } from '../../routes/paths'
import { useThemeContext } from '../../contexts/ThemeContext'
import NotificationModal from '../pages/notifications/NotificationModal'
import { OPEN_NOTIFICATION_MODAL_EVENT } from '../pages/notifications/events'
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
    { icon: Gift, label: 'Thưởng', route: ROUTE_PATHS.rewards },
]

function getTourId(route: string): string | undefined {
    if (route === ROUTE_PATHS.home) return 'sidebar-home'
    if (route === ROUTE_PATHS.chat) return 'sidebar-chat'
    if (route === ROUTE_PATHS.reflect) return 'sidebar-reflect'
    if (route === ROUTE_PATHS.resources) return 'sidebar-resources'
    if (route === ROUTE_PATHS.nutrition) return 'sidebar-nutrition'
    if (route === ROUTE_PATHS.rewards) return 'sidebar-rewards'
    return undefined
}

export default function Sidebar({ isOpen, onHide, onReveal }: SidebarProps) {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'
    const [isMoreOpen, setIsMoreOpen] = useState(false)
    const [isNotificationOpen, setIsNotificationOpen] = useState(false)

    useEffect(() => {
        const openModal = () => setIsNotificationOpen(true)
        window.addEventListener(OPEN_NOTIFICATION_MODAL_EVENT, openModal)
        return () => window.removeEventListener(OPEN_NOTIFICATION_MODAL_EVENT, openModal)
    }, [])

    const sidebarContainerClass = isDark
        ? 'border-white/20 bg-black/30 text-white'
        : 'border-black/15 bg-white/70 text-serene-ink'
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

    const handleNavClick = () => {
        if (window.innerWidth < 1024) {
            onHide()
        }
    }

    return (
        <>
            {/* ── Desktop sidebar ── */}
            <aside
                onClick={handleSidebarBlankClick}
                className={[
                    'fixed left-0 top-0 z-[60] flex h-full w-60 flex-col border-r p-6 backdrop-blur-3xl transition-transform duration-300 lg:z-40',
                    sidebarContainerClass,
                    isOpen ? 'translate-x-0' : '-translate-x-full',
                ].join(' ')}
            >
                {/* Brand */}
                <div className="mb-7">
                    <Link to={ROUTE_PATHS.home} className="font-display text-4xl italic">Serene</Link>
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
                                onClick={handleNavClick}
                                data-tour-id={getTourId(item.route)}
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
                    <button
                        onClick={() => {
                            setIsNotificationOpen(true)
                            handleNavClick()
                        }}
                        className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 transition cursor-pointer ${hoverTextClass}`}
                    >
                        <Bell className="h-4 w-4" aria-hidden="true" />
                        <span>Thông báo</span>
                    </button>
                    <NavLink
                        to={ROUTE_PATHS.setting}
                        onClick={handleNavClick}
                        className={`flex items-center gap-3 rounded-xl px-3 py-2.5 transition ${hoverTextClass}`}
                    >
                        <Settings className="h-4 w-4" aria-hidden="true" />
                        <span>Cài đặt</span>
                    </NavLink>
                    <NavLink
                        to={ROUTE_PATHS.support}
                        onClick={handleNavClick}
                        data-tour-id="sidebar-help"
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

            {/* Mobile Sidebar Toggle Button */}
            <button
                onClick={isOpen ? onHide : onReveal}
                className={[
                    'fixed left-0 top-1/2 z-[70] flex h-10 w-6 -translate-y-1/2 items-center justify-center rounded-r-xl border border-l-0 shadow-md transition-all duration-300 lg:hidden',
                    isDark ? 'border-white/20 bg-black/40 text-white' : 'border-black/10 bg-white/60 text-serene-ink',
                    isOpen ? 'translate-x-60' : 'translate-x-0',
                ].join(' ')}
                aria-label={isOpen ? 'Đóng menu' : 'Mở menu'}
            >
                {isOpen ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>

            {/* Mobile Backdrop */}
            {isOpen && (
                <div
                    className="fixed inset-0 z-[55] bg-black/20 backdrop-blur-sm lg:hidden"
                    onClick={onHide}
                    aria-hidden="true"
                />
            )}

            {/* ── Mobile bottom nav ── */}
            <nav className={`fixed bottom-4 left-1/2 z-50 flex w-[min(94vw,560px)] -translate-x-1/2 items-center justify-between rounded-3xl border px-3 py-2 shadow-[0_8px_32px_rgba(47,52,46,0.14)] backdrop-blur-xl lg:hidden ${isDark ? 'border-white/25 bg-black/55' : 'border-white/45 bg-white/75'}`}>
                {navItems.slice(0, 4).map((item) => {
                    const Icon = item.icon
                    return (
                        <NavLink
                            key={item.label}
                            to={item.route}
                            end
                            onClick={() => setIsMoreOpen(false)}
                            data-tour-id={getTourId(item.route)}
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
                
                {/* Nút Thêm */}
                <div className="relative flex-1">
                    <button
                        type="button"
                        onClick={() => setIsMoreOpen(!isMoreOpen)}
                        className={[
                            'flex w-full flex-col items-center gap-1 rounded-2xl px-1 py-2 text-[12px] font-medium transition cursor-pointer',
                            isMoreOpen
                                ? (isDark ? 'bg-white/20 text-white' : 'bg-serene-primary/10 text-serene-primary')
                                : (isDark ? 'text-white/75 hover:text-white' : 'text-serene-muted/70 hover:text-serene-ink'),
                        ].join(' ')}
                    >
                        <MoreHorizontal className="h-5 w-5" />
                        <span>Thêm</span>
                    </button>
                    
                    {isMoreOpen && (
                        <div className={`absolute bottom-[calc(100%+12px)] right-0 w-48 rounded-2xl border p-2 shadow-xl backdrop-blur-xl animate-in fade-in slide-in-from-bottom-2 ${isDark ? 'border-white/25 bg-black/85' : 'border-white/45 bg-white/95'}`}>
                            {navItems.slice(4).map((item) => {
                                const Icon = item.icon
                                return (
                                    <NavLink
                                        key={item.label}
                                        to={item.route}
                                        end
                                        onClick={() => setIsMoreOpen(false)}
                                        data-tour-id={getTourId(item.route)}
                                        className={({ isActive }) =>
                                            [
                                                'flex items-center gap-3 rounded-xl px-3 py-2.5 text-[14px] font-medium transition',
                                                isActive
                                                    ? (isDark ? 'bg-white/20 text-white' : 'bg-serene-primary/10 text-serene-primary')
                                                    : (isDark ? 'text-white/75 hover:text-white' : 'text-serene-muted hover:text-serene-ink'),
                                            ].join(' ')
                                        }
                                    >
                                        <Icon className="h-4 w-4" />
                                        <span>{item.label}</span>
                                    </NavLink>
                                )
                            })}
                            <div className={`my-1 border-t ${isDark ? 'border-white/20' : 'border-black/10'}`}></div>
                            <button
                                onClick={() => {
                                    setIsMoreOpen(false)
                                    setIsNotificationOpen(true)
                                }}
                                className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-[14px] font-medium transition cursor-pointer ${isDark ? 'text-white/75 hover:bg-white/10 hover:text-white' : 'text-serene-muted hover:bg-black/5 hover:text-serene-ink'}`}
                            >
                                <Bell className="h-4 w-4" />
                                <span>Thông báo</span>
                            </button>
                            <NavLink
                                to={ROUTE_PATHS.setting}
                                onClick={() => setIsMoreOpen(false)}
                                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-[14px] font-medium transition ${isDark ? 'text-white/75 hover:bg-white/10 hover:text-white' : 'text-serene-muted hover:bg-black/5 hover:text-serene-ink'}`}
                            >
                                <Settings className="h-4 w-4" />
                                <span>Cài đặt</span>
                            </NavLink>
                            <NavLink
                                to={ROUTE_PATHS.support}
                                onClick={() => setIsMoreOpen(false)}
                                data-tour-id="sidebar-help"
                                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-[14px] font-medium transition ${isDark ? 'text-white/75 hover:bg-white/10 hover:text-white' : 'text-serene-muted hover:bg-black/5 hover:text-serene-ink'}`}
                            >
                                <HelpCircle className="h-4 w-4" />
                                <span>Hỗ trợ</span>
                            </NavLink>
                        </div>
                    )}
                </div>
            </nav>
            <NotificationModal open={isNotificationOpen} onClose={() => setIsNotificationOpen(false)} />
        </>
    )
}
