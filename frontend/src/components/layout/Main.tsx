
import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import sunset from '../../assets/bg.png'
import dawn from '../../assets/bg2.png'
import night from '../../assets/bg3.png'
import ocean from '../../assets/bg-reflect.png'
// import Footer from './Footer'
import {
    APP_SETTINGS_STORAGE_KEY,
    APP_SETTINGS_UPDATED_EVENT,
    DEFAULT_APP_SETTINGS,
    readAppSettings,
    type AppSettings,
    type ThemeOption,
} from '../../utils/appSettings'
import HeaderMain from './HeaderMain'
import Sidebar from './Sidebar'
import { GuestBanner } from '../guest/GuestBanner'

const themeBackgroundMap: Record<ThemeOption, string> = {
    sunset: sunset,
    ocean: ocean,
    dawn: dawn,
    night: night,
}

export default function Main() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)
    const [backgroundImage, setBackgroundImage] = useState(
        themeBackgroundMap[DEFAULT_APP_SETTINGS.theme],
    )

    useEffect(() => {
        const currentSettings = readAppSettings()
        setBackgroundImage(themeBackgroundMap[currentSettings.theme])

        const handleSettingsUpdated = (event: Event) => {
            const customEvent = event as CustomEvent<AppSettings>
            const theme = customEvent.detail?.theme ?? DEFAULT_APP_SETTINGS.theme
            setBackgroundImage(themeBackgroundMap[theme])
        }

        const handleStorageUpdated = (event: StorageEvent) => {
            if (event.key !== APP_SETTINGS_STORAGE_KEY) {
                return
            }

            const nextSettings = readAppSettings()
            setBackgroundImage(themeBackgroundMap[nextSettings.theme])
        }

        window.addEventListener(APP_SETTINGS_UPDATED_EVENT, handleSettingsUpdated as EventListener)
        window.addEventListener('storage', handleStorageUpdated)

        return () => {
            window.removeEventListener(APP_SETTINGS_UPDATED_EVENT, handleSettingsUpdated as EventListener)
            window.removeEventListener('storage', handleStorageUpdated)
        }
    }, [])

    return (
        <div className="relative min-h-screen">
            <GuestBanner />
            <div className="fixed inset-0 -z-20">
                <img
                    src={backgroundImage}
                    alt="Hình nền yên bình"
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