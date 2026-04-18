import { Bell, PanelLeft, PanelLeftClose, Settings } from 'lucide-react'
import { useEffect, useState } from 'react';

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

    useEffect(() => {
        const timer = window.setInterval(() => setNow(new Date()), 60_000)
        return () => window.clearInterval(timer)
    }, [])

    const greeting = getGreetingByHour(now.getHours())
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
                    {greeting} tốt lành nhé Elena!
                </p>
            </div>
            <div className="flex items-center gap-2 sm:gap-4">
                <button
                    type="button"
                    className="rounded-full p-2 text-white/90 transition hover:bg-white/25"
                >
                    <Bell className="h-5 w-5" />
                </button>
                <button
                    type="button"
                    className="rounded-full p-2 text-white/90 transition hover:bg-white/25"
                >
                    <Settings className="h-5 w-5" />
                </button>
            </div>
        </header>
    )
}