import { useEffect, useMemo, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import sunset from '../../assets/backgrounds/bg-noon.png'
import dawn from '../../assets/backgrounds/bg-morning.png'
import nightTheme from '../../assets/backgrounds/bg-night.png'
import ocean from '../../assets/backgrounds/bg-reflection.png'
import bgReflection from '../../assets/backgrounds/bg-reflection.png'
import bgResource from '../../assets/backgrounds/bg-resource.png'
import bgReward from '../../assets/backgrounds/bg-reward.png'
import bgSetting from '../../assets/backgrounds/bg-setting.png'
import bgHelp from '../../assets/backgrounds/bg-help.png'
import bgMorning from '../../assets/backgrounds/bg-morning.png'
import bgNoon from '../../assets/backgrounds/bg-noon.png'
import bgNight from '../../assets/backgrounds/bg-night.png'
// import Footer from './Footer'
import {
    APP_SETTINGS_STORAGE_KEY,
    APP_SETTINGS_UPDATED_EVENT,
    DEFAULT_APP_SETTINGS,
    readAppSettings,
    type AppSettings,
    type ThemeOption,
} from '../../utils/appSettings'
import { resolveSereneHomeBackground } from '../../utils/sereneHomeBackground'
import Sidebar from './Sidebar'
import { GuestBanner } from '../guest/GuestBanner'
import { ROUTE_PATHS } from '../../routes/paths'
import SereneGuideOverlay from '../onboardingTour/SereneGuideOverlay'

const themeBackgroundMap: Record<ThemeOption, string> = {
    sunset: sunset,
    ocean: ocean,
    dawn: dawn,
    night: nightTheme,
}

function normalizePathname(pathname: string): string {
    if (pathname.length > 1 && pathname.endsWith('/')) {
        return pathname.slice(0, -1)
    }
    return pathname
}

export default function Main() {
    const location = useLocation()
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)
    const [appTheme, setAppTheme] = useState<ThemeOption>(() => readAppSettings().theme)
    /** Bumps every minute on `/serene` so time-of-day background refreshes without touching theme. */
    const [homeTimeTick, setHomeTimeTick] = useState(0)

    const pathname = normalizePathname(location.pathname)
    const isSereneHomeRoute = pathname === ROUTE_PATHS.home

    const backgroundImage = useMemo(() => {
        void homeTimeTick
        if (pathname === ROUTE_PATHS.reflect) {
            return bgReflection
        }
        if (pathname === ROUTE_PATHS.resources) {
            return bgResource
        }
        if (pathname === ROUTE_PATHS.rewards) {
            return bgReward
        }
        if (pathname === ROUTE_PATHS.setting) {
            return bgSetting
        }
        if (pathname === ROUTE_PATHS.support) {
            return bgHelp
        }
        if (pathname === ROUTE_PATHS.home) {
            return resolveSereneHomeBackground(bgMorning, bgNoon, bgNight)
        }
        return themeBackgroundMap[appTheme]
    }, [pathname, appTheme, homeTimeTick])

    const isFullBleedPage = location.pathname === ROUTE_PATHS.bamboo || location.pathname === ROUTE_PATHS.chat

    useEffect(() => {
        const handleSettingsUpdated = (event: Event) => {
            const customEvent = event as CustomEvent<AppSettings>
            const settings = customEvent.detail
            if (settings) {
                const theme = settings.theme ?? DEFAULT_APP_SETTINGS.theme
                setAppTheme(theme)
            }
        }

        const handleStorageUpdated = (event: StorageEvent) => {
            if (event.key !== APP_SETTINGS_STORAGE_KEY) {
                return
            }

            const nextSettings = readAppSettings()
            setAppTheme(nextSettings.theme)
        }

        window.addEventListener(APP_SETTINGS_UPDATED_EVENT, handleSettingsUpdated as EventListener)
        window.addEventListener('storage', handleStorageUpdated)

        return () => {
            window.removeEventListener(APP_SETTINGS_UPDATED_EVENT, handleSettingsUpdated as EventListener)
            window.removeEventListener('storage', handleStorageUpdated)
        }
    }, [])

    useEffect(() => {
        if (!isSereneHomeRoute) {
            return
        }
        const intervalId = window.setInterval(() => {
            setHomeTimeTick((n) => n + 1)
        }, 60_000)
        const onVisible = () => {
            if (document.visibilityState === 'visible') {
                setHomeTimeTick((n) => n + 1)
            }
        }
        document.addEventListener('visibilitychange', onVisible)
        return () => {
            window.clearInterval(intervalId)
            document.removeEventListener('visibilitychange', onVisible)
        }
    }, [isSereneHomeRoute])

    return (
        <div className="relative min-h-screen">
            <GuestBanner />
            <div className="fixed inset-0 -z-20">
                <img
                    src={backgroundImage}
                    alt="Hình nền yên bình"
                    className="h-full w-full object-cover"
                />
            </div>

            <Sidebar
                isOpen={isSidebarOpen}
                onHide={() => setIsSidebarOpen(false)}
                onReveal={() => setIsSidebarOpen(true)}
            />

            <main
                className={`min-h-screen transition-all duration-300 ${isFullBleedPage ? '' : isSidebarOpen ? 'lg:ml-60' : 'lg:ml-0'}`}
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
            <SereneGuideOverlay />
        </div>
    )
}
