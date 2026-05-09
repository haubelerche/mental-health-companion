import { Play, ChevronDown, ChevronUp, BookOpen, Volume2 } from 'lucide-react'
import { useState } from 'react'
import { type ResourceItem } from '../../../services/resourceService'
import { useThemeContext } from '../../../contexts/ThemeContext'
function minutes(durationSec: number): string {
    return `${Math.max(1, Math.round(durationSec / 60))} phút`
}

interface ResourceGridProps {
    items: ResourceItem[]
    onOpen: (item: ResourceItem) => void
}

export function ResourceGrid({ items, onOpen }: ResourceGridProps) {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

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
            <article className={`rounded-4xl bg-theme-surface border border-theme-secondary/50 shadow-xl`}>
                <div className="relative overflow-hidden rounded-t-3xl cursor-pointer" onClick={() => onOpen(featured)}>
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
                <div className="mt-5 flex items-end justify-between gap-4 p-5">
                    <div>
                        <h2
                            dangerouslySetInnerHTML={{ __html: featured.title }}
                            className={`font-display font-semibold text-4xl ${isDark ? 'text-white' : 'text-serene-ink'}`}>
                        </h2>

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
                                className={`group grid grid-cols-[72px_1fr_auto] items-center gap-3 rounded-[1.75rem] bg-theme-surface border border-theme-secondary/20 p-4 text-left shadow-lg transition hover:-translate-y-1`}
                            >
                                {item.thumbnail ? (
                                    <img src={item.thumbnail} alt="" className="h-20 w-20 rounded-2xl object-cover shadow" />
                                ) : (
                                    <div className="h-16 w-16 rounded-2xl bg-serene-primary/10" />
                                )}
                                <div>
                                    <h3
                                        title={item.title}
                                        dangerouslySetInnerHTML={{ __html: item.title }}
                                        className={`font-display font-semibold line-clamp-2 leading-tight ${isDark ? 'text-white' : 'text-serene-primary'}`}>

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
                                className={`mx-auto cursor-pointer flex items-center gap-2 rounded-full bg-theme-surface px-6 py-3 text-sm font-semibold border border-theme-secondary/10 hover:border-theme-secondary/40`}
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
