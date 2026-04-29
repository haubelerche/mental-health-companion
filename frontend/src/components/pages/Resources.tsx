import { Download, Heart, Play, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
    resourceService,
    type ResourceItem,
} from '../../services/resourceService'
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

function minutes(durationSec: number): string {
    return `${Math.max(1, Math.round(durationSec / 60))} phút`
}

const RESOURCE_CATEGORY_IDS = ['all', 'meditate', 'sleep', 'music', 'wisdom', 'movement', 'work_study']
// ── Generic resource grid (other tabs) ────────────────────────────────────────
function ResourceGrid({
    items,
    onOpen,
}: {
    items: ResourceItem[]
    onOpen: (item: ResourceItem) => void
}) {
    if (items.length === 0) {
        return (
            <div className="flex h-40 items-center justify-center rounded-3xl bg-white/30 text-sm text-serene-muted">
                Chưa có nội dung cho chủ đề này.
            </div>
        )
    }

    const [featured, ...rest] = items
    const sideItems = rest.slice(0, 3)

    return (
        <div className="space-y-6">
            {/* Featured */}
            <article className="rounded-[2rem] bg-white/52 p-5 shadow-[0_24px_60px_rgba(47,52,46,0.09)]">
                <div className="relative overflow-hidden rounded-3xl">
                    {featured.thumbnail ? (
                        <img src={featured.thumbnail} alt="" className="h-52 w-full object-cover" />
                    ) : (
                        <div className="h-52 w-full rounded-3xl bg-serene-primary/15" />
                    )}
                    <span className="absolute bottom-4 left-4 rounded-full bg-serene-primary px-3 py-1 text-[0.62rem] font-bold uppercase tracking-[0.18em] text-white">
                        Nổi bật
                    </span>
                </div>
                <div className="mt-5 flex items-end justify-between gap-4">
                    <div>
                        <h2 className="font-display text-4xl text-serene-ink">{featured.title}</h2>
                        <p className="mt-1.5 text-xs text-serene-muted">
                            {minutes(featured.duration_sec)} · {featured.format.replace(/_/g, ' ')}
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={() => onOpen(featured)}
                        className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full bg-serene-primary text-serene-on-primary shadow-xl transition hover:scale-105"
                        aria-label={`Mở ${featured.title}`}
                    >
                        <Play className="ml-1 h-6 w-6 fill-current" />
                    </button>
                </div>
                {featured.description && (
                    <p className="mt-4 text-sm leading-relaxed text-serene-muted">{featured.description}</p>
                )}
            </article>

            {/* Side items */}
            {sideItems.length > 0 && (
                <div className="grid gap-4 sm:grid-cols-3">
                    {sideItems.map((item) => (
                        <button
                            key={item.id}
                            type="button"
                            onClick={() => onOpen(item)}
                            className="group grid grid-cols-[72px_1fr_auto] items-center gap-3 rounded-[1.75rem] bg-white/50 p-4 text-left shadow-[0_18px_44px_rgba(47,52,46,0.07)] transition hover:-translate-y-1 hover:bg-white/75"
                        >
                            {item.thumbnail ? (
                                <img src={item.thumbnail} alt="" className="h-16 w-16 rounded-2xl object-cover" />
                            ) : (
                                <div className="h-16 w-16 rounded-2xl bg-serene-primary/10" />
                            )}
                            <div>
                                <h3 className="font-display text-lg leading-tight text-serene-ink">
                                    {item.title}
                                </h3>
                                <p className="mt-1 text-[0.68rem] text-serene-muted">
                                    {minutes(item.duration_sec)} · {item.format.replace(/_/g, ' ')}
                                </p>
                            </div>
                            <span className="flex h-8 w-8 items-center justify-center rounded-full border border-serene-primary/20 text-serene-primary transition group-hover:bg-serene-primary group-hover:text-white">
                                <Play className="ml-0.5 h-3.5 w-3.5 fill-current" />
                            </span>
                        </button>
                    ))}
                </div>
            )}
        </div>
    )
}

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
        if (item.url.startsWith('/serene')) {
            navigate(item.url)
            return
        }
        window.open(item.url, '_blank', 'noopener,noreferrer')
    }

    return (
        <section className="mx-auto max-w-6xl rounded-[2.5rem] border border-white/50 bg-[#f5eee5]/78 p-5 shadow-[0_30px_90px_rgba(47,52,46,0.18)] backdrop-blur-2xl sm:p-8 lg:p-10">

            {/* Header */}
            <div className="mb-7 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                    <p className="text-[0.68rem] font-bold uppercase tracking-[0.34em] text-serene-primary/70">
                        Thư viện
                    </p>
                    <h1 className="mt-1 font-display text-4xl text-serene-ink md:text-5xl">Tài nguyên</h1>
                </div>
                <label className="flex items-center gap-2 rounded-full bg-white/45 px-4 py-3 text-sm text-serene-muted shadow-inner">
                    <Search className="h-4 w-4 flex-shrink-0" />
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
                            className={`flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold transition ${
                                isActive
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
                        <div className="flex h-40 items-center justify-center rounded-3xl bg-white/30 text-sm text-serene-muted">
                            Đang tải tài nguyên...
                        </div>
                    ) : (
                        <ResourceGrid items={filteredItems} onOpen={openItem} />
                    )}
                </motion.div>
            </AnimatePresence>

            {/* Footer */}
            <footer className="mt-12 flex flex-wrap items-center justify-center gap-8 border-t border-serene-ink/5 pt-7 text-xs text-serene-muted">
                <span className="inline-flex items-center gap-2">
                    <Heart className="h-4 w-4" /> Yêu thích
                </span>
                <span className="inline-flex items-center gap-2">
                    <Download className="h-4 w-4" /> Offline
                </span>
                <p className="w-full text-center font-display text-lg italic text-serene-muted/60">
                    "Học cách chữa lành là hành trình đẹp để nhớ của mỗi con người."
                </p>
            </footer>
        </section>
    )
}
