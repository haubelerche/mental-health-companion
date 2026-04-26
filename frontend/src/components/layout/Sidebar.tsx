import { Compass, HelpCircle, HomeIcon, Leaf, Library, MessageSquare, Sparkles, User } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { ROUTE_PATHS } from '../../routes/paths'

type SidebarProps = {
    isOpen: boolean
}

const navItems = [
    { icon: HomeIcon, label: 'Trang chủ', route: ROUTE_PATHS.home },
    { icon: MessageSquare, label: 'Chat', route: ROUTE_PATHS.chat },
    { icon: Sparkles, label: 'Nhìn lại', route: ROUTE_PATHS.reflect },
    { icon: Library, label: 'Tài nguyên', route: ROUTE_PATHS.resources },
    { icon: Compass, label: 'Kết nối', route: ROUTE_PATHS.connect },
    { icon: Leaf, label: 'Rừng Trúc', route: ROUTE_PATHS.bamboo },
]

export default function Sidebar({ isOpen }: SidebarProps) {
    return (
        <>
            {/* ── Desktop sidebar ── */}
            <aside
                className={[
                    'fixed left-0 top-0 z-40 hidden h-full w-72 flex-col border-r border-white/30 bg-white/35 p-8 backdrop-blur-3xl transition-transform duration-300 lg:flex',
                    isOpen ? 'translate-x-0' : '-translate-x-[110%]',
                ].join(' ')}
            >
                {/* Brand */}
                <div className="mb-10">
                    <h1 className="font-display text-6xl italic text-serene-ink">Serene</h1>
                    <p className="mt-2 text-[11px] uppercase tracking-[0.3em] text-serene-muted/70">
                        Digital Sanctuary
                    </p>
                </div>

                {/* Primary nav */}
                <nav className="flex flex-1 flex-col gap-1.5">
                    {navItems.map((item) => {
                        const Icon = item.icon
                        return (
                            <NavLink
                                key={item.label}
                                to={item.route}
                                end
                                className={({ isActive }) =>
                                    [
                                        'group flex items-center gap-3.5 rounded-2xl px-4 py-3 text-left transition-all duration-200',
                                        isActive
                                            ? 'bg-serene-primary/90 text-serene-on-primary shadow-[0_4px_16px_rgba(77,99,89,0.3)]'
                                            : 'text-serene-muted hover:bg-white/65 hover:text-serene-ink',
                                    ].join(' ')
                                }
                            >
                                {({ isActive }) => (
                                    <>
                                        <span
                                            className={[
                                                'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl transition-colors',
                                                isActive ? 'bg-white/20' : 'bg-serene-primary/8 group-hover:bg-white/60',
                                            ].join(' ')}
                                        >
                                            <Icon className="h-4 w-4" />
                                        </span>
                                        <span className="font-display text-xl">{item.label}</span>
                                    </>
                                )}
                            </NavLink>
                        )
                    })}
                </nav>

                {/* Bottom links */}
                <div className="mt-6 space-y-1 border-t border-white/20 pt-6 text-sm text-serene-muted">
                    <NavLink
                        to={`${ROUTE_PATHS.setting}#user-profile`}
                        className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition hover:bg-white/50 hover:text-serene-ink"
                    >
                        <User className="h-4 w-4" />
                        <span>Tài khoản</span>
                    </NavLink>
                    <NavLink
                        to={ROUTE_PATHS.connect}
                        className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition hover:bg-white/50 hover:text-serene-ink"
                    >
                        <HelpCircle className="h-4 w-4" />
                        <span>Hỗ trợ</span>
                    </NavLink>
                </div>
            </aside>

            {/* ── Mobile bottom nav ── */}
            <nav className="fixed bottom-4 left-1/2 z-50 flex w-[min(94vw,480px)] -translate-x-1/2 items-center justify-between rounded-3xl border border-white/45 bg-white/75 px-3 py-2 shadow-[0_8px_32px_rgba(47,52,46,0.14)] backdrop-blur-xl lg:hidden">
                {navItems.slice(0, 5).map((item) => {
                    const Icon = item.icon
                    return (
                        <NavLink
                            key={item.label}
                            to={item.route}
                            end
                            className={({ isActive }) =>
                                [
                                    'flex flex-1 flex-col items-center gap-1 rounded-2xl px-1 py-2 text-[10px] font-medium transition',
                                    isActive
                                        ? 'bg-serene-primary/10 text-serene-primary'
                                        : 'text-serene-muted/70 hover:text-serene-ink',
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
