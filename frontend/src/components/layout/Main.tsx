
import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
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
import Sidebar from './Sidebar'
import { GuestBanner } from '../guest/GuestBanner'
import { ROUTE_PATHS } from '../../routes/paths'

const themeBackgroundMap: Record<ThemeOption, string> = {
    sunset: sunset,
    ocean: ocean,
    dawn: dawn,
    night: night,
}

export default function Main() {
    const location = useLocation()
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)
    const [backgroundImage, setBackgroundImage] = useState(() => {
        const currentSettings = readAppSettings()
        return themeBackgroundMap[currentSettings.theme]
    })
    const isFullBleedPage = location.pathname === ROUTE_PATHS.bamboo

    useEffect(() => {
        const applyMode = (mode: string) => {
            if (mode === 'dark') {
                document.documentElement.setAttribute('data-theme', 'dark')
            } else {
                document.documentElement.removeAttribute('data-theme')
            }
        }

        const handleSettingsUpdated = (event: Event) => {
            const customEvent = event as CustomEvent<AppSettings>
            const settings = customEvent.detail
            if (settings) {
                const theme = settings.theme ?? DEFAULT_APP_SETTINGS.theme
                setBackgroundImage(themeBackgroundMap[theme])
                applyMode(settings.mode)
            }
        }

        const handleStorageUpdated = (event: StorageEvent) => {
            if (event.key !== APP_SETTINGS_STORAGE_KEY) {
                return
            }

            const nextSettings = readAppSettings()
            setBackgroundImage(themeBackgroundMap[nextSettings.theme])
            applyMode(nextSettings.mode)
        }

        // Initial apply
        applyMode(readAppSettings().mode)

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

            <Sidebar
                isOpen={isSidebarOpen}
                onHide={() => setIsSidebarOpen(false)}
                onReveal={() => setIsSidebarOpen(true)}
            />

            <main
                className={`min-h-screen transition-all duration-300 ${isSidebarOpen ? 'lg:ml-60' : 'lg:ml-0'}`}
            >
                <div
                    className={
                        isFullBleedPage
                            ? 'min-h-screen'
                            : 'mx-auto max-w-6xl px-4 pb-24 pt-6 sm:px-6 lg:px-8 lg:py-8'
                    }
                >
                    <Outlet />
                </div>
            </main>
        </div>
    )
}
