
import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import bg from '../../assets/bg3.png'
// import Footer from './Footer'
import HeaderMain from './HeaderMain'
import Sidebar from './Sidebar'

function getGreetingByHour(hour: number) {
    if (hour >= 5 && hour < 11) return 'Buổi sáng'
    if (hour >= 11 && hour < 14) return 'Buổi trưa'
    if (hour >= 14 && hour < 18) return 'Buổi chiều'
    return 'Buổi tối'
}

export default function Main() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)
    const [now, setNow] = useState(() => new Date())

    useEffect(() => {
        const timer = window.setInterval(() => setNow(new Date()), 60_000)
        return () => window.clearInterval(timer)
    }, [])

    const greeting = getGreetingByHour(now.getHours())

    return (
        <div className="relative min-h-screen">
            <div className="fixed inset-0 -z-20">
                <img
                    src={bg}
                    alt="Mặt biển lúc hoàng hôn"
                    className="h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-white/20" />
            </div>

            <Sidebar isOpen={isSidebarOpen} />

            <main
                className={`min-h-screen transition-all duration-300 ${isSidebarOpen ? 'lg:ml-72' : 'lg:ml-0'}`}
            >
                <HeaderMain
                    isSidebarOpen={isSidebarOpen}
                    greeting={greeting}
                    onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
                />

                <div className="mx-auto max-w-7xl px-5 pb-28 pt-8 sm:px-8 lg:px-12 lg:py-12">
                    <Outlet />
                </div>

                {/* <Footer /> */}
            </main>
        </div>
    )
}