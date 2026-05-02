import { useEffect, useState } from 'react'
import {
    APP_SETTINGS_STORAGE_KEY,
    APP_SETTINGS_UPDATED_EVENT,
    readAppSettings,
    type AppSettings,
} from '../../utils/appSettings'

type Props = {
    words?: string[]
    selected: string[]
    onChange: (selected: string[]) => void
    className?: string
}

const DEFAULT_WORDS = [
    'Bình yên', 'Hứng khởi', 'Biết ơn', 'Tự tin',
    'Mệt mỏi', 'Lo âu', 'Buồn', 'Căng thẳng',
    'Vui vẻ', 'Trống rỗng', 'Cô đơn', 'Bối rối',
]

export function MoodWordChips({ words = DEFAULT_WORDS, selected, onChange, className }: Props) {
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

    const toggle = (word: string) => {
        onChange(
            selected.includes(word)
                ? selected.filter((w) => w !== word)
                : [...selected, word],
        )
    }

    return (
        <div className={`flex flex-wrap gap-2 ${className ?? ''}`}>
            {words.map((word) => (
                <button
                    key={word}
                    type="button"
                    onClick={() => toggle(word)}
                    className={[
                        'rounded-full px-4 py-2 text-sm font-medium transition-all active:scale-95 cursor-pointer',
                        selected.includes(word)
                            ? (isDark ? 'bg-theme-accent text-white shadow-sm' : 'bg-serene-primary text-serene-on-primary shadow-sm')
                            : `${isDark ? 'border-white/10 bg-white/5 hover:bg-white/10 text-white/70' : 'border border-gray-300 bg-white/70 hover:bg-serene-on-primary text-serene-ink'}`,
                    ].join(' ')}
                >
                    {word}
                </button>
            ))}
        </div>
    )
}
