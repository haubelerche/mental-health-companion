import { useEffect, useState } from 'react'
import {
    APP_SETTINGS_STORAGE_KEY,
    APP_SETTINGS_UPDATED_EVENT,
    readAppSettings,
    type AppSettings,
} from '../../utils/appSettings'

type Props = {
    streak: number
    className?: string
}

const DAYS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']

function getTodayDisplayIndex(): number {
    const day = new Date().getDay() // 0=Sun ... 6=Sat
    return day === 0 ? 6 : day - 1  // map Mon=0 ... Sun=6
}

export function StreakBar({ streak, className }: Props) {
    const [isDark, setIsDark] = useState(() => readAppSettings().mode === 'dark')

    useEffect(() => {
        const syncThemeMode = (settings: AppSettings) => {
            setIsDark(settings.mode === 'dark')
        }

        const handleSettingsUpdated = (event: Event) => {
            const customEvent = event as CustomEvent<AppSettings>
            if (customEvent.detail) {
                syncThemeMode(customEvent.detail)
            }
        }

        const handleStorageUpdated = (event: StorageEvent) => {
            if (event.key !== APP_SETTINGS_STORAGE_KEY) {
                return
            }
            syncThemeMode(readAppSettings())
        }

        window.addEventListener(APP_SETTINGS_UPDATED_EVENT, handleSettingsUpdated as EventListener)
        window.addEventListener('storage', handleStorageUpdated)
        return () => {
            window.removeEventListener(APP_SETTINGS_UPDATED_EVENT, handleSettingsUpdated as EventListener)
            window.removeEventListener('storage', handleStorageUpdated)
        }
    }, [])
    const todayIdx = getTodayDisplayIndex()
    const filledCount = Math.min(streak, 7)
    const completedIndices = new Set<number>()
    for (let offset = 0; offset < filledCount; offset += 1) {
        // Mark consecutive streak days backward from today (wrap across week boundary).
        const idx = (todayIdx - offset + 7) % 7
        completedIndices.add(idx)
    }

    return (
        <div className={`flex items-center gap-1.5 ${className ?? ''}`}>
            {DAYS.map((day, idx) => {
                const isCompleted = completedIndices.has(idx)
                const isToday = idx === todayIdx && !isCompleted

                return (
                    <div key={day} className="flex flex-1 flex-col items-center gap-1">
                        <div
                            className={[
                                'flex h-8 w-8 items-center justify-center rounded-full  font-semibold transition-all',
                                isCompleted
                                    ? (isDark ? 'bg-theme-accent text-white shadow-sm' : 'bg-serene-primary text-serene-on-primary shadow-sm')
                                    : isToday
                                        ? (isDark ? 'animate-pulse ring-2 ring-theme-accent ring-offset-1 bg-theme-accent/20 text-theme-accent' : 'animate-pulse ring-2 ring-serene-primary ring-offset-1 bg-serene-accent/30 text-serene-primary')
                                        : `${isDark ? 'border-white/10 bg-white/5 text-white/40' : 'border-white/40 bg-white/50 text-serene-muted'}`,
                            ].join(' ')}
                        >
                            {isCompleted ? '✓' : day.charAt(0)}
                        </div>
                        <span className={`text-sm ${isDark ? 'text-white/40' : 'text-serene-muted'}`}>{day}</span>
                    </div>
                )
            })}
        </div>
    )
}
