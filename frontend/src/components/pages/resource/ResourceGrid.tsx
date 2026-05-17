import { Play, BookOpen, Volume2 } from 'lucide-react'
import { type ResourceItem } from '../../../services/resourceService'
import { useThemeContext } from '../../../contexts/ThemeContext'
import PixelEmptyState from '../../pixel/PixelEmptyState'

function formatDuration(sec: number): string {
    const m = Math.max(1, Math.round(sec / 60))
    return m >= 60 ? `${Math.floor(m / 60)} giờ ${m % 60 > 0 ? `${m % 60} phút` : ''}`.trim() : `${m} phút`
}

function FormatIcon({ format }: { format: string }) {
    if (format === 'article') return <BookOpen className="h-3 w-3" />
    if (format === 'audio') return <Volume2 className="h-3 w-3" />
    return <Play className="h-3 w-3 fill-current" />
}

interface ResourceGridProps {
    items: ResourceItem[]
    onOpen: (item: ResourceItem) => void
    compact?: boolean
}

export function ResourceGrid({ items, onOpen, compact = false }: ResourceGridProps) {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    if (items.length === 0) {
        return (
            <PixelEmptyState
                mascot="rock"
                title="Chưa có nội dung cho chủ đề này"
                description="Tài nguyên mới sẽ xuất hiện khi backend trả về nội dung phù hợp."
            />
        )
    }

    return (
        <div className={`grid grid-cols-2 gap-4 sm:grid-cols-2 md:grid-cols-3 ${compact ? '' : 'lg:grid-cols-4'}`}>
            {items.map((item) => (
                <button
                    key={item.id}
                    type="button"
                    onClick={() => onOpen(item)}
                    className={`
                        group relative flex flex-col overflow-hidden rounded-2xl text-left
                        border transition-all duration-200
                        hover:-translate-y-1 hover:shadow-xl
                        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-serene-primary
                        ${isDark
                            ? 'bg-white/5 border-white/10 hover:bg-white/8 hover:border-white/20'
                            : 'bg-white border-black/6 hover:border-serene-primary/20 shadow-sm'
                        }
                    `}
                >
                    {/* Thumbnail */}
                    <div className="relative aspect-video w-full overflow-hidden bg-serene-primary/8">
                        {item.thumbnail ? (
                            <img
                                src={item.thumbnail}
                                alt=""
                                className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                                loading="lazy"
                            />
                        ) : (
                            <div className="h-full w-full bg-gradient-to-br from-serene-primary/20 to-serene-primary/5" />
                        )}

                        {/* Overlay on hover */}
                        <div className="absolute inset-0 bg-black/0 transition-colors duration-200 group-hover:bg-black/30 flex items-center justify-center">
                            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/90 text-serene-ink opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
                                <FormatIcon format={item.format} />
                            </span>
                        </div>

                        {/* Duration pill */}
                        {item.duration_sec > 0 && (
                            <span className="absolute bottom-2 right-2 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
                                {formatDuration(item.duration_sec)}
                            </span>
                        )}
                    </div>

                    {/* Info */}
                    <div className="flex flex-1 flex-col gap-1 p-3">
                        <p
                            title={item.title}
                            className={`line-clamp-2 text-sm font-semibold leading-snug ${
                                isDark ? 'text-white/90' : 'text-serene-ink'
                            }`}
                            dangerouslySetInnerHTML={{ __html: item.title }}
                        />
                        <p className={`mt-auto text-[11px] font-medium capitalize ${isDark ? 'text-white/40' : 'text-serene-muted/70'}`}>
                            {item.format.replace(/_/g, ' ')}
                        </p>
                    </div>
                </button>
            ))}
        </div>
    )
}
