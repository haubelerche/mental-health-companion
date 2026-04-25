import { Bell, ChevronDown, KeyRound, LogIn, LogOut, PanelLeft, PanelLeftClose } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { ROUTE_PATHS } from '../../routes/paths'
import { toast } from 'react-toastify'

type HeaderMainProps = {
    isSidebarOpen: boolean
    onToggleSidebar: () => void
}

function getGreetingByHour(hour: number) {
    if (hour >= 5 && hour < 11) return 'Buổi sáng'
    if (hour >= 11 && hour < 14) return 'Buổi trưa'
    if (hour >= 14 && hour < 18) return 'Buổi chiều'
    return 'Buổi tối'
}

export default function HeaderMain({ isSidebarOpen, onToggleSidebar }: HeaderMainProps) {
    const [now, setNow] = useState(() => new Date())
    const [isDropdownOpen, setIsDropdownOpen] = useState(false)
    const dropdownRef = useRef<HTMLDivElement>(null)
    const navigate = useNavigate()
    const { user, logout } = useAuth()

    useEffect(() => {
        const timer = window.setInterval(() => setNow(new Date()), 60_000)
        return () => window.clearInterval(timer)
    }, [])

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsDropdownOpen(false)
            }
        }

        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const greeting = getGreetingByHour(now.getHours())
    const displayName = user?.displayName || 'Elena'

    const handleLoginNavigation = () => {
        setIsDropdownOpen(false)
        navigate(ROUTE_PATHS.login)
    }

    const handleChangePasswordNavigation = () => {
        setIsDropdownOpen(false)
        navigate(ROUTE_PATHS.forget)
    }

    const handleLogout = async () => {
        await logout()
        toast.success('Đăng xuất thành công!')
        setIsDropdownOpen(false)
        navigate(ROUTE_PATHS.landing)
    }

    return (
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-white/35 px-5 py-4 backdrop-blur-xl sm:px-8 lg:px-12">
            <div className="flex items-center gap-3 sm:gap-4">
                <button
                    type="button"
                    onClick={onToggleSidebar}
                    className="rounded-full p-2 text-white/90 transition hover:bg-white/25"
                    aria-label={isSidebarOpen ? 'Ẩn sidebar' : 'Hiện sidebar'}
                >
                    {isSidebarOpen ? (
                        <PanelLeftClose className="h-5 w-5" />
                    ) : (
                        <PanelLeft className="h-5 w-5" />
                    )}
                </button>
                <img
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuC6xpig2l3SMnAnmPD3226klv7fSDDOAMHWjUcCZaakIEznH7s6gqVLuhEbeQ_ioWvn515mTic_UfBHcOp799nLyXYwNMRIrHn-dwI-g2tFHEOcNNCrWuoTCKErn1V0RYZ6Mr1Wl7evlwFzsL4tHYsEfQWmGwaz1HKOirvXAuuFa1IvMCQwBLMCe-SBnR0VSZDTIvV_m9VYUGHjpEZ7c9J6p_GIXUM-MY6KD5l6LKA2L2ylmr9tsRl5Sn05lyM2SsF6x-eveAtafiM"
                    alt="Ảnh hồ sơ"
                    className="h-11 w-11 rounded-full border-2 border-white/70 object-cover"
                />
                <p className="font-display text-lg text-white sm:text-2xl">
                    {greeting} tốt lành nhé {displayName}!
                </p>
            </div>
            <div className="flex items-center gap-2 sm:gap-4">
                <button
                    type="button"
                    className="rounded-full p-2 text-white/90 transition hover:bg-white/25"
                >
                    <Bell className="h-5 w-5" />
                </button>
                <div className="relative" ref={dropdownRef}>
                    <button
                        type="button"
                        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                        className="rounded-full p-2 text-white/90 transition hover:bg-white/25"
                        aria-label="Mở menu tài khoản"
                        aria-haspopup="menu"
                        aria-expanded={isDropdownOpen}
                    >
                        <ChevronDown className={`h-5 w-5 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
                    </button>

                    {isDropdownOpen && (
                        <div className="absolute right-0 mt-2 w-56 rounded-2xl border border-white/25 bg-white p-2 shadow-xl" role="menu">
                            <button
                                type="button"
                                onClick={handleLoginNavigation}
                                className="flex w-full items-center gap-3 px-4 py-3 text-sm text-on-surface transition hover:bg-serene-primary/10 rounded-lg"
                                role="menuitem"
                            >
                                <LogIn className="h-4 w-4 text-primary" />
                                Đăng nhập
                            </button>

                            <button
                                type="button"
                                onClick={handleChangePasswordNavigation}
                                className="flex w-full items-center gap-3 px-4 py-3 text-sm text-on-surface transition hover:bg-serene-primary/10 rounded-lg"
                                role="menuitem"
                            >
                                <KeyRound className="h-4 w-4 text-primary" />
                                Đổi mật khẩu
                            </button>

                            <button
                                type="button"
                                onClick={handleLogout}
                                className="flex w-full items-center gap-3 px-4 py-3 text-sm text-red-500 transition hover:bg-red-50 rounded-lg"
                                role="menuitem"
                            >
                                <LogOut className="h-4 w-4" />
                                Đăng xuất
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </header>
    )
}