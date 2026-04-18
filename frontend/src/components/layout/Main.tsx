
import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import bg from '../../assets/bg3.png'
// import Footer from './Footer'
import HeaderMain from './HeaderMain'
import Sidebar from './Sidebar'


export default function Main() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)


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