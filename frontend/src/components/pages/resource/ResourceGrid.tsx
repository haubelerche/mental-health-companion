import { Play, ChevronDown, ChevronUp, BookOpen, Volume2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { type ResourceItem } from '../../../services/resourceService'
import {
    APP_SETTINGS_STORAGE_KEY,
    APP_SETTINGS_UPDATED_EVENT,
    readAppSettings,
    type AppSettings,
} from '../../../utils/appSettings'

function minutes(durationSec: number): string {
    return `${Math.max(1, Math.round(durationSec / 60))} phút`
}

interface ResourceGridProps {
    items: ResourceItem[]
    onOpen: (item: ResourceItem) => void
}

export function ResourceGrid({ items, onOpen }: ResourceGridProps) {
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

    const [expandedCount, setExpandedCount] = useState(3)

    if (items.length === 0) {
        return (
            <div className={`flex h-40 items-center justify-center rounded-3xl ${isDark ? 'bg-white/5 border border-white/10' : 'bg-white/30'} text-sm ${isDark ? 'text-white/40' : 'text-serene-muted'}`}>
                Chưa có nội dung cho chủ đề này.
            </div>
        )
    }

    const [featured, ...rest] = items
    const displayedSideItems = rest.slice(0, expandedCount)
    const hasMore = expandedCount < rest.length
    const isFullyExpanded = expandedCount >= rest.length

    return (
        <div className="space-y-6">
            {/* Featured */}
            <article className={`rounded-4xl ${isDark ? 'bg-white/5 border border-white/10' : 'bg-white/52'} p-5 shadow-lg`}>
                <div className="relative overflow-hidden rounded-3xl cursor-pointer" onClick={() => onOpen(featured)}>
                    {featured.thumbnail ? (
                        <div className="aspect-video relative">
                            <img
                                src={featured.thumbnail}
                                className="h-full w-full object-cover"
                            />

                            {/* overlay tối */}
                            <div className="absolute inset-0 bg-black/40" />
                        </div>
                    ) : (
                        <div className="h-52 w-full rounded-3xl bg-serene-primary/15" />
                    )}

                    {/* label */}
                    <span className="absolute bottom-4 left-4 rounded-full bg-serene-primary px-3 py-1 tracking-wide font-bold uppercase  text-white">
                        Nổi bật
                    </span>

                    {/* nút play ở giữa */}
                    <button
                        type="button"
                        onClick={() => onOpen(featured)}
                        className="cursor-pointer absolute left-1/2 top-1/2 flex h-14 w-14 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-red-500 text-serene-on-primary shadow-xl transition hover:scale-120 duration-300"
                        aria-label={`Mở ${featured.title}`}
                    >
                        <Play className="ml-1 h-6 w-6 fill-current" />
                    </button>
                </div>
                <div className="mt-5 flex items-end justify-between gap-4">
                    <div>
                        <h2 className={`font-display font-semibold text-4xl ${isDark ? 'text-white' : 'text-serene-ink'}`}>{featured.title}</h2>
                        <p className={`mt-1.5 ml-1.5 text-sm ${isDark ? 'text-white/60' : 'text-serene-muted'}`}>
                            <span>{minutes(featured.duration_sec)}</span> · <span className='font-semibold capitalize'>{featured.format.replace(/_/g, ' ')}</span>
                        </p>
                    </div>

                </div>
                {featured.description && (
                    <p className={`mt-4 text-sm leading-relaxed ${isDark ? 'text-white/70' : 'text-serene-muted'}`}>{featured.description}</p>
                )}
            </article>

            {/* Side items */}
            {displayedSideItems.length > 0 && (
                <div className="space-y-4">
                    <div className="grid gap-4 sm:grid-cols-3">
                        {displayedSideItems.map((item) => (
                            <div
                                key={item.id}

                                onClick={() => onOpen(item)}
                                className={`group grid grid-cols-[72px_1fr_auto] items-center gap-3 rounded-[1.75rem] ${isDark ? 'bg-white/5 border border-white/5 hover:bg-white/10' : 'bg-white/50 hover:bg-white/75'} p-4 text-left shadow-lg transition hover:-translate-y-1`}
                            >
                                {item.thumbnail ? (
                                    <img src={item.thumbnail} alt="" className="h-20 w-20 rounded-2xl object-cover shadow" />
                                ) : (
                                    <div className="h-16 w-16 rounded-2xl bg-serene-primary/10" />
                                )}
                                <div>
                                    <h3 className={`font-display text-lg font-semibold leading-tight ${isDark ? 'text-white' : 'text-serene-ink'}`}>
                                        {item.title}
                                    </h3>
                                    <p className={`mt-1 text-xs ${isDark ? 'text-white/60' : 'text-serene-muted'}`}>
                                        <span>{minutes(item.duration_sec)}</span> · <span className='font-semibold capitalize'>{item.format.replace(/_/g, ' ')}</span>
                                    </p>
                                </div>
                                <button className={`cursor-pointer flex h-8 w-8 items-center justify-center rounded-full border ${isDark ? 'border-theme-accent text-theme-accent group-hover:bg-theme-accent group-hover:text-white' : 'border-serene-primary text-serene-primary group-hover:bg-serene-primary group-hover:text-white'} transition`}>
                                    {item.format === 'article' ? <BookOpen className="ml-0.5 h-3.5 w-3.5 fill-current" />
                                        : item.format === 'audio' ? <Volume2 className="ml-0.5 h-3.5 w-3.5 fill-current" />
                                            : <Play className="ml-0.5 h-3.5 w-3.5 fill-current" />}
                                </button>
                            </div>
                        ))}
                    </div>

                    {/* See more / Show less button */}
                    {items.length > 4 ? (
                        (hasMore || isFullyExpanded) && (
                            <button
                                type="button"
                                onClick={() => {
                                    if (hasMore) {
                                        setExpandedCount((prev) => prev + 6)
                                    } else {
                                        setExpandedCount(3)
                                    }
                                }}
                                className={`mx-auto flex items-center gap-2 rounded-full ${isDark ? 'bg-white/5 border border-white/10 hover:bg-white/10' : 'bg-white/55 hover:bg-white/85'} px-6 py-3 text-sm font-semibold ${isDark ? 'text-white/60' : 'text-serene-muted'} transition ${isDark ? 'hover:text-white' : 'hover:text-serene-ink'}`}
                            >
                                {hasMore ? (
                                    <>
                                        <span>Xem thêm</span>
                                        <ChevronDown className="h-4 w-4" />
                                    </>
                                ) : (
                                    <>
                                        <span>Ẩn bớt</span>
                                        <ChevronUp className="h-4 w-4" />
                                    </>
                                )}
                            </button>
                        )
                    ) : (
                        <div></div>
                    )}


                </div>
            )}
        </div>
    )
}
