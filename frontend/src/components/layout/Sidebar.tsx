import { useEffect, useState } from 'react'
import { Bell, HelpCircle, HomeIcon, Library, MessageSquare, Sailboat, Settings, Sparkles, Utensils, Gift, ChevronLeft, ChevronRight } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { ROUTE_PATHS } from '../../routes/paths'
import { useThemeContext } from '../../contexts/ThemeContext'
import NotificationModal from '../pages/notifications/NotificationModal'
import { OPEN_NOTIFICATION_MODAL_EVENT } from '../pages/notifications/events'
import Logo from '../ui/Logo'
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



    return (
        <>
            {/* ── Desktop sidebar ── */}
            <aside
                className={[
                    'fixed left-0 top-0 z-[60] flex h-full w-60 flex-col border-r p-6 backdrop-blur-3xl transition-transform duration-300 lg:z-40',
                    sidebarContainerClass,
                    isOpen ? 'translate-x-0' : '-translate-x-full',
                ].join(' ')}
            >
                {/* Brand */}
                <div className="mb-7 serene-landing bg-transparent!">
                    <Logo 
                        path={ROUTE_PATHS.home} 
                        fontSize="2.5rem" 
                        className='pixel-headline' 
                        textShadow="2px 2px 0 #020812, -1px -1px 0 #020812, 1px -1px 0 #020812, -1px 1px 0 #020812, 1px 1px 0 #020812"
                    />
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
                        }}
                        className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 transition cursor-pointer ${hoverTextClass}`}
                    >
                        <Bell className="h-4 w-4" aria-hidden="true" />
                        <span>Thông báo</span>
                    </button>
                    <NavLink
                        to={ROUTE_PATHS.setting}
                        className={`flex items-center gap-3 rounded-xl px-3 py-2.5 transition ${hoverTextClass}`}
                    >
                        <Settings className="h-4 w-4" aria-hidden="true" />
                        <span>Cài đặt</span>
                    </NavLink>
                    <NavLink
                        to={ROUTE_PATHS.support}
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
                    'fixed left-0 top-1/2 z-[70] flex h-10 w-6 -translate-y-1/2 items-center justify-center rounded-r-xl border border-l-0 shadow-md transition-all duration-300',
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


            <NotificationModal open={isNotificationOpen} onClose={() => setIsNotificationOpen(false)} />
        </>
    )
}
