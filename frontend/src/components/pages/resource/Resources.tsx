import { Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
    resourceService,
    type ResourceItem,
} from './../../../services/resourceService'
import { ResourceGrid } from './ResourceGrid'
import { YouTubeEmbed, isYouTubeUrl } from './YouTubeEmbed'
import Loading from '../../ui/Loading'

// ── Vietnamese category labels ────────────────────────────────────────────────
const VI_LABELS: Record<string, { label: string; icon: string }> = {
    all: { label: 'Tất cả', icon: '✦' },
    meditate: { label: 'Thiền định', icon: '♧' },
    sleep: { label: 'Ngủ', icon: '🌙' },
    music: { label: 'Âm nhạc', icon: '♪' },
    wisdom: { label: 'Trí tuệ', icon: '◌' },
    movement: { label: 'Vận động', icon: '↟' },
    work_study: { label: 'Tập trung', icon: '◎' },
}

function localizeCategory(id: string, fallbackLabel: string) {
    return VI_LABELS[id] ?? { label: fallbackLabel, icon: '○' }
}

const RESOURCE_CATEGORY_IDS = ['all', 'meditate', 'sleep', 'music', 'wisdom', 'movement', 'work_study']

// ── Main component ─────────────────────────────────────────────────────────────
export default function Resources() {
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()
    const requestedCategory = searchParams.get('category') || 'all'
    const initialCategory = RESOURCE_CATEGORY_IDS.includes(requestedCategory) ? requestedCategory : 'sleep'

    const [categories, setCategories] = useState([{ id: 'all', label: 'Tất cả', icon: '✦' }])
    const [selectedCategory, setSelectedCategory] = useState<string>(initialCategory)
    const [items, setItems] = useState<ResourceItem[]>([])
    const [query, setQuery] = useState(searchParams.get('q') || '')
    const [loadingResources, setLoadingResources] = useState(true)
    const [youtubeOpen, setYoutubeOpen] = useState(false)
    const [youtubeItem, setYoutubeItem] = useState<ResourceItem | null>(null)

    useEffect(() => {
        resourceService
            .getCategories()
            .then((data) => {
                setCategories([{ id: 'all', label: 'Tất cả', icon: '✦' }, ...data.categories])
            })
            .catch(() => undefined)
    }, [])

    useEffect(() => {
        let active = true

        const loadResources = async () => {
            setLoadingResources(true)
            try {
                const categoryParam =
                    selectedCategory === 'all'
                        ? undefined
                        : selectedCategory

                const data = await resourceService.list(categoryParam, 50, 0)

                if (active) setItems(data.items)
            } catch {
                if (active) setItems([])
            } finally {
                if (active) setLoadingResources(false)
            }
        }

        void loadResources()
        return () => {
            active = false
        }
    }, [categories, selectedCategory])

    const visibleItems = items

    const filteredItems = useMemo(() => {
        const q = query.trim().toLowerCase()
        if (!q) return visibleItems
        const tokens = q.split(/\s+/).filter(Boolean)
        return visibleItems.filter((item) => {
            const hay = `${item.title} ${item.description ?? ''} ${(item.tags ?? []).join(' ')}`.toLowerCase()
            return hay.includes(q) || tokens.some((t) => hay.includes(t))
        })
    }, [visibleItems, query])

    const openItem = (item: ResourceItem) => {
        // Handle internal routes
        if (item.url.startsWith('/serene')) {
            navigate(item.url)
            return
        }

        // Handle YouTube videos
        if (isYouTubeUrl(item.url)) {
            setYoutubeItem(item)
            setYoutubeOpen(true)
            return
        }

        // Handle external links
        window.open(item.url, '_blank', 'noopener,noreferrer')
    }

    return (
        <section className="mx-auto max-w-6xl rounded-[2.5rem] border border-white/50 bg-[#f5eee5]/78 p-5 shadow-[0_30px_90px_rgba(47,52,46,0.18)] backdrop-blur-2xl sm:p-8 lg:p-10">

            {/* Header */}
            <div className="mb-7 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                    <h1 className="mt-1 font-display text-4xl text-serene-ink md:text-5xl"> Thư viện tài nguyên</h1>
                </div>
                <label className="flex items-center gap-2 border border-gray-300 rounded-full bg-white px-4 py-3 text-sm text-serene-muted shadow-inner">
                    <Search className="h-4 w-4 shrink-0" />
                    <input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Tìm kiếm..."
                        className="w-full bg-transparent outline-none placeholder:text-serene-muted/60"
                    />
                </label>
            </div>

            {/* Category tabs */}
            <div className="mb-8 flex flex-wrap gap-2">
                {categories.map((cat) => {
                    const vi = localizeCategory(cat.id, cat.label)
                    const isActive = selectedCategory === cat.id
                    return (
                        <button
                            key={cat.id}
                            type="button"
                            onClick={() => setSelectedCategory(cat.id)}
                            className={`flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold transition ${isActive
                                ? 'bg-serene-primary text-serene-on-primary shadow-[0_8px_20px_rgba(77,99,89,0.25)]'
                                : 'bg-white/55 text-serene-muted hover:bg-white/85 hover:text-serene-ink'
                                }`}
                        >
                            <span>{vi.icon}</span>
                            <span>{vi.label}</span>
                        </button>
                    )
                })}
            </div>

            {/* Tab content */}
            <AnimatePresence mode="wait">
                <motion.div
                    key={selectedCategory}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.2, ease: 'easeOut' }}
                >
                    {loadingResources ? (
                        <Loading text="Đang tải tài nguyên..." />
                    ) : (
                        <ResourceGrid items={filteredItems} onOpen={openItem} />
                    )}
                </motion.div>
            </AnimatePresence>

            {/* YouTube modal */}
            <AnimatePresence>
                {youtubeOpen && youtubeItem && (
                    <YouTubeEmbed
                        url={youtubeItem.url}
                        title={youtubeItem.title}
                        isOpen={youtubeOpen}
                        onClose={() => {
                            setYoutubeOpen(false)
                            setYoutubeItem(null)
                        }}
                    />
                )}
            </AnimatePresence>

            {/* Footer */}
            <footer className="mt-12 flex flex-wrap items-center justify-center gap-8 border-t border-serene-ink/20 pt-7 text-xs ">

                <p className="w-full text-center font-display text-lg italic text-serene-muted/60">
                    "Học cách chữa lành là hành trình đẹp để nhớ của mỗi con người."
                </p>
            </footer>
        </section>
    )
}
