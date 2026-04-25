import { Download, Heart, Play, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
    FALLBACK_RESOURCE_CATEGORIES,
    getFallbackResources,
    resourceService,
    type ResourceCategory,
    type ResourceItem,
} from '../../services/resourceService'

function minutes(durationSec: number): string {
    return `${Math.max(1, Math.round(durationSec / 60))} min`
}

function normalizeCategory(category: ResourceCategory): ResourceCategory {
    if (category.id === 'work_study') return { ...category, label: 'Focus' }
    return category
}

export default function Resources() {
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()
    const requestedCategory = searchParams.get('category') || 'meditate'
    const categoryIds = useMemo(() => FALLBACK_RESOURCE_CATEGORIES.map((category) => category.id), [])
    const suggestedCategory = categoryIds.includes(requestedCategory) ? requestedCategory : 'meditate'
    const suggestedQuery = searchParams.get('q') || ''
    const [categories, setCategories] = useState<ResourceCategory[]>(FALLBACK_RESOURCE_CATEGORIES)
    const [items, setItems] = useState<ResourceItem[]>(getFallbackResources(suggestedCategory))
    const [selectedCategory, setSelectedCategory] = useState<string>(suggestedCategory)
    const [query, setQuery] = useState(suggestedQuery)

    useEffect(() => {
        resourceService
            .getCategories()
            .then((data) => {
                const apiCategories = data.categories.map(normalizeCategory)
                setCategories([FALLBACK_RESOURCE_CATEGORIES[0], ...apiCategories])
            })
            .catch(() => undefined)
    }, [])

    useEffect(() => {
        if (selectedCategory === 'all') return
        resourceService
            .list(selectedCategory, 10, 0)
            .then((data) => setItems(data.items.length ? data.items : getFallbackResources(selectedCategory)))
            .catch(() => setItems(getFallbackResources(selectedCategory)))
    }, [selectedCategory])

    const visibleItems = selectedCategory === 'all' ? getFallbackResources('all') : items
    const filteredItems = useMemo(() => {
        const normalizedQuery = query.trim().toLowerCase()
        if (!normalizedQuery) return visibleItems
        const tokens = normalizedQuery.split(/\s+/).filter(Boolean)
        return visibleItems.filter((item) => {
            const haystack = `${item.title} ${item.description ?? ''} ${(item.tags ?? []).join(' ')}`.toLowerCase()
            return haystack.includes(normalizedQuery) || tokens.some((token) => haystack.includes(token))
        })
    }, [visibleItems, query])

    const featured = filteredItems[0] ?? getFallbackResources('meditate')[0]
    const sideItems = filteredItems.slice(1, 4)
    const sleepStories = getFallbackResources('sleep').slice(0, 3)
    const soundscapes = getFallbackResources('sleep').slice(1, 4)

    const openItem = (item: ResourceItem) => {
        if (item.url.startsWith('/serene')) {
            navigate(item.url)
            return
        }
        window.open(item.url, '_blank', 'noopener,noreferrer')
    }

    return (
        <section className="mx-auto max-w-6xl rounded-[2.5rem] border border-white/50 bg-[#f5eee5]/78 p-5 shadow-[0_30px_90px_rgba(47,52,46,0.18)] backdrop-blur-2xl sm:p-8 lg:p-12">
            <div className="mb-7 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <p className="font-display text-2xl text-serene-ink">Thư viện của Serene</p>
                <label className="flex items-center gap-2 rounded-full bg-white/45 px-4 py-3 text-sm text-serene-muted shadow-inner">
                    <Search className="h-4 w-4" />
                    <input
                        value={query}
                        onChange={(event) => setQuery(event.target.value)}
                        placeholder="Search resources..."
                        className="w-full bg-transparent outline-none placeholder:text-serene-muted/60"
                    />
                </label>
            </div>

            <header className="text-center">
                <p className="text-[0.68rem] font-bold uppercase tracking-[0.34em] text-serene-primary/70">
                    Discovery Library
                </p>
                <h1 className="mt-4 font-display text-5xl font-light leading-none text-serene-ink md:text-7xl">
                    Khám phá <span className="italic text-serene-primary">Sự bình yên</span>
                </h1>
                <p className="mx-auto mt-5 max-w-2xl text-sm leading-relaxed text-serene-muted md:text-base">
                    Explore curated audio sessions designed to anchor your mind and restore inner peace through the rhythm of nature.
                </p>
            </header>

            <div className="mt-8 flex flex-wrap justify-center gap-3">
                {categories.map((cat) => (
                    <button
                        key={cat.id}
                        type="button"
                        onClick={() => setSelectedCategory(cat.id)}
                        className={`rounded-full px-5 py-2.5 text-xs font-semibold transition ${
                            selectedCategory === cat.id
                                ? 'bg-serene-primary text-serene-on-primary shadow-[0_12px_26px_rgba(47,52,46,0.2)]'
                                : 'bg-white/55 text-serene-muted hover:bg-white/85 hover:text-serene-ink'
                        }`}
                    >
                        {cat.label}
                    </button>
                ))}
            </div>

            <div className="mt-12 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
                <article className="rounded-[2rem] bg-white/52 p-5 shadow-[0_24px_60px_rgba(47,52,46,0.09)]">
                    <div className="relative overflow-hidden rounded-3xl">
                        {featured.thumbnail && (
                            <img src={featured.thumbnail} alt="" className="h-56 w-full object-cover" />
                        )}
                        <span className="absolute bottom-4 left-4 rounded-full bg-serene-primary px-3 py-1 text-[0.62rem] font-bold uppercase tracking-[0.18em] text-white">
                            Hot Session
                        </span>
                    </div>
                    <div className="mt-7 flex items-end justify-between gap-4">
                        <div>
                            <h2 className="font-display text-4xl text-serene-ink">{featured.title}</h2>
                            <p className="mt-2 text-xs text-serene-muted">
                                {minutes(featured.duration_sec)} • {featured.format.replaceAll('_', ' ')}
                            </p>
                        </div>
                        <button
                            type="button"
                            onClick={() => openItem(featured)}
                            className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-serene-primary text-serene-on-primary shadow-xl transition hover:scale-105"
                            aria-label={`Mở ${featured.title}`}
                        >
                            <Play className="ml-1 h-7 w-7 fill-current" />
                        </button>
                    </div>
                    <p className="mt-5 max-w-xl text-sm leading-relaxed text-serene-muted">{featured.description}</p>
                </article>

                <div className="grid gap-5">
                    {sideItems.map((item) => (
                        <button
                            key={item.id}
                            type="button"
                            onClick={() => openItem(item)}
                            className="group grid grid-cols-[88px_1fr_auto] items-center gap-4 rounded-[1.75rem] bg-white/50 p-4 text-left shadow-[0_18px_44px_rgba(47,52,46,0.07)] transition hover:-translate-y-1 hover:bg-white/75"
                        >
                            {item.thumbnail && (
                                <img src={item.thumbnail} alt="" className="h-20 w-20 rounded-2xl object-cover" />
                            )}
                            <div>
                                <h3 className="font-display text-2xl leading-tight text-serene-ink">{item.title}</h3>
                                <p className="mt-2 text-[0.7rem] text-serene-muted">
                                    {minutes(item.duration_sec)} • {item.format.replaceAll('_', ' ')}
                                </p>
                            </div>
                            <span className="flex h-9 w-9 items-center justify-center rounded-full border border-serene-primary/20 text-serene-primary group-hover:bg-serene-primary group-hover:text-white">
                                <Play className="ml-0.5 h-4 w-4 fill-current" />
                            </span>
                        </button>
                    ))}
                </div>
            </div>

            <div className="mt-12 grid gap-8 lg:grid-cols-2">
                <section>
                    <div className="mb-5 flex items-center justify-between">
                        <h2 className="font-display text-3xl text-serene-primary">Sleep Stories</h2>
                        <button className="text-[0.65rem] font-bold uppercase tracking-[0.22em] text-serene-muted">
                            View Collection
                        </button>
                    </div>
                    <div className="grid gap-4 sm:grid-cols-3">
                        {sleepStories.map((item) => (
                            <button key={item.id} type="button" onClick={() => openItem(item)} className="text-left">
                                {item.thumbnail && <img src={item.thumbnail} alt="" className="h-28 w-full rounded-3xl object-cover" />}
                                <h3 className="mt-3 font-display text-xl leading-tight text-serene-ink">{item.title}</h3>
                                <p className="mt-1 text-[0.68rem] text-serene-muted">Narrated by Serene</p>
                            </button>
                        ))}
                    </div>
                </section>
                <section>
                    <div className="mb-5 flex items-center justify-between">
                        <h2 className="font-display text-3xl text-serene-primary">Soundscapes</h2>
                        <p className="text-xs italic text-serene-muted">Pure immersion without narration</p>
                    </div>
                    <div className="grid gap-4 sm:grid-cols-3">
                        {soundscapes.map((item) => (
                            <button
                                key={item.id}
                                type="button"
                                onClick={() => openItem(item)}
                                className="relative min-h-40 overflow-hidden rounded-3xl p-4 text-left text-white shadow-xl"
                            >
                                {item.thumbnail && <img src={item.thumbnail} alt="" className="absolute inset-0 h-full w-full object-cover" />}
                                <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
                                <div className="relative mt-20">
                                    <h3 className="font-semibold leading-tight">{item.title}</h3>
                                    <p className="mt-1 text-[0.62rem] uppercase tracking-[0.18em] text-white/75">{item.format}</p>
                                </div>
                            </button>
                        ))}
                    </div>
                </section>
            </div>

            <footer className="mt-12 flex flex-wrap items-center justify-center gap-8 border-t border-serene-ink/5 pt-7 text-xs text-serene-muted">
                <span className="inline-flex items-center gap-2"><Heart className="h-4 w-4" /> Favorites</span>
                <span className="inline-flex items-center gap-2"><Download className="h-4 w-4" /> Offline</span>
                <p className="w-full text-center font-display text-lg italic text-serene-muted/60">
                    "Học cách chữa lành là hành trình đẹp để nhớ của mỗi con người."
                </p>
            </footer>
        </section>
    )
}
