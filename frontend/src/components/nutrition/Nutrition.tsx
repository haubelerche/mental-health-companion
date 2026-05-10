import { useEffect, useState, useMemo } from 'react'
import { Search, X } from 'lucide-react'
import { dashboardService, type NutritionDailyTip } from '../../services/dashboardService'
import { useThemeContext } from '../../contexts/ThemeContext'
import nutritionContent from '../../../data/nutritionContent.json'
import a1 from '../../assets/nutrition-a1.jpg'
import a2 from '../../assets/nutrition-a2.jpg'
import Mascot from '../pixel/Mascot'
import PixelEmptyState from '../pixel/PixelEmptyState'

// ─── Types ──────────────────────────────────────────────────────────────────────

type NutritionRecipe = {
    name: string
    mood: string
    time: string
    tags: string[]
    ingredients: string
    benefit?: string
}

type NutritionMoodFood = {
    food: string
    why: string
    tags?: string[]
}

type NutritionContent = {
    dailyFacts: string[]
    tags: string[]
    scienceSection: {
        eyebrow: string
        titleLines: string[]
        paragraphs: string[]
    }
    moodFoods: NutritionMoodFood[]
    recipes: NutritionRecipe[]
}

const CONTENT = nutritionContent as NutritionContent

const getMoodStyle = (isDark: boolean): Record<string, string> => ({
    'Năng lượng': isDark ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' : 'bg-amber-100 text-amber-700 border-amber-200',
    'Tập trung': isDark ? 'bg-blue-500/20 text-blue-300 border-blue-500/30' : 'bg-blue-100 text-blue-700 border-blue-200',
    'Ổn định': isDark ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' : 'bg-emerald-100 text-emerald-700 border-emerald-200',
    'Vui vẻ': isDark ? 'bg-pink-500/20 text-pink-300 border-pink-500/30' : 'bg-pink-100 text-pink-700 border-pink-200',
    'Trí nhớ': isDark ? 'bg-violet-500/20 text-violet-300 border-violet-500/30' : 'bg-violet-100 text-violet-700 border-violet-200',
    'Thư giãn': isDark ? 'bg-teal-500/20 text-teal-300 border-teal-500/30' : 'bg-teal-100 text-teal-700 border-teal-200',
    'Hạnh phúc': isDark ? 'bg-rose-500/20 text-rose-300 border-rose-500/30' : 'bg-rose-100 text-rose-700 border-rose-200',
    'Bình yên': isDark ? 'bg-slate-500/20 text-slate-300 border-slate-500/30' : 'bg-slate-100 text-slate-600 border-slate-200',
})

// ─── Component ─────────────────────────────────────────────────────────────────

export default function Nutrition() {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const [dailyTip, setDailyTip] = useState<NutritionDailyTip | null>(null)
    const [query, setQuery] = useState('')
    const [activeTag, setActiveTag] = useState<string | null>(null)

    const todayFact = useMemo(() => {
        return CONTENT.dailyFacts[0] ?? 'Một bữa ăn đều đặn, đủ chất và ít chế biến là nền tảng tốt cho sức khỏe thể chất lẫn tinh thần.'
    }, [])

    const featuredRecipes = useMemo(() => {
        return CONTENT.recipes.slice(0, 3)
    }, [])

    useEffect(() => {
        let mounted = true
        dashboardService
            .getNutritionDailyTip()
            .then((data) => { if (mounted) setDailyTip(data) })
            .catch(() => undefined)
        return () => { mounted = false }
    }, [])

    const filteredRecipes = useMemo(() => {
        const q = query.trim().toLowerCase()
        if (!q && !activeTag) return featuredRecipes
        return CONTENT.recipes.filter((r) => {
            const matchQuery = !q || r.name.toLowerCase().includes(q) || r.ingredients.toLowerCase().includes(q) || (r.benefit ?? '').toLowerCase().includes(q)
            const matchTag = !activeTag || r.tags.includes(activeTag)
            return matchQuery && matchTag
        }).slice(0, 6)
    }, [query, activeTag, featuredRecipes])

    const MOOD_STYLE = getMoodStyle(isDark)

    return (
        <div className="space-y-6 pb-16 lg:space-y-8">

            {/* ── Daily fact banner ───────────────────────────────────────── */}
            <section className="flex items-start gap-3 rounded-[22px] bg-theme-surface/80 px-5 py-4 backdrop-blur-sm">
                <Mascot variant="eat" size="sm" decorative />
                <div>
                    <p className="mb-1 text-[10px] uppercase tracking-[0.28em] text-theme-text-primary font-bold">Fact hôm nay</p>
                    <p className="text-sm leading-relaxed text-theme-text-secondary">{todayFact}</p>
                </div>
            </section>

            {/* ── Section 1: Content LEFT · Image RIGHT ──────────────────── */}
            <section className="grid gap-4 lg:grid-cols-2 lg:items-stretch">

                <div className={`flex flex-col justify-center rounded-[28px] bg-theme-surface/80 p-7 backdrop-blur-xl lg:p-9`}>
                    <p className="text-[10px] uppercase tracking-[0.3em] text-theme-text-secondary/60">{CONTENT.scienceSection.eyebrow}</p>
                    <h1 className="mt-3 font-display text-4xl italic leading-tight text-theme-text-primary sm:text-5xl">
                        {CONTENT.scienceSection.titleLines.map((line, index) => (
                            <span key={line}>
                                {line}{index < CONTENT.scienceSection.titleLines.length - 1 && <br />}
                            </span>
                        ))}
                    </h1>
                    {CONTENT.scienceSection.paragraphs.map((paragraph) => (
                        <p key={paragraph} className="mt-5 text-sm leading-relaxed text-theme-text-secondary">
                            {paragraph}
                        </p>
                    ))}
                    {dailyTip && (
                        <div className="mt-5 rounded-2xl bg-theme-accent/20 px-4 py-3">
                            <p className="mb-1 text-[10px] uppercase tracking-[0.2em] text-theme-accent/70">Gợi ý từ AI hôm nay</p>
                            <p className="text-sm font-semibold text-theme-text-primary">{dailyTip.dish}</p>
                            <p className="mt-1 text-xs leading-relaxed text-theme-text-secondary">{dailyTip.benefit}</p>
                            {dailyTip.tip && (
                                <p className="mt-1.5 text-[11px] text-theme-text-secondary/70">{dailyTip.tip}</p>
                            )}
                        </div>
                    )}
                </div>

                <div className="relative min-h-72 overflow-hidden rounded-[28px] shadow-sm lg:min-h-0">
                    <img src={a1} alt="Tô yến mạch với trái cây tươi" className={`h-full w-full object-cover ${isDark ? 'brightness-75' : ''}`} />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                    <blockquote className="absolute bottom-6 left-6 right-6 text-white">
                        <p className="font-display text-2xl italic leading-snug">
                            "Ăn sáng đúng cách —<br />ngày bắt đầu đúng nhịp"
                        </p>
                        <p className="mt-1.5 text-xs text-white/60">Bữa sáng giàu protein + chất xơ</p>
                    </blockquote>
                </div>
            </section>

            {/* ── Section 2: Image LEFT · Content RIGHT ──────────────────── */}
            <section className="grid gap-4 lg:grid-cols-2 lg:items-stretch">

                <div className="relative min-h-72 overflow-hidden rounded-[28px] shadow-sm lg:min-h-0">
                    <img src={a2} alt="Bát cơm cân bằng dinh dưỡng" className={`h-full w-full object-cover ${isDark ? 'brightness-75' : ''}`} />
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black/50" />
                    <div className="absolute bottom-5 left-5">
                        <span className="rounded-full border border-white/40 bg-white/15 px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-white backdrop-blur-md">
                            Đĩa ăn cân bằng ½ + ¼ + ¼
                        </span>
                    </div>
                </div>

                <div className={`flex flex-col justify-center rounded-[28px] bg-theme-surface/80 p-7 backdrop-blur-xl lg:p-9`}>
                    <p className="text-[10px] uppercase tracking-[0.3em] text-theme-text-secondary/60">Tăng cường tâm trạng</p>
                    <h2 className="mt-3 font-display text-4xl italic leading-tight text-theme-text-primary sm:text-5xl">
                        Ăn gì<br />để vui hơn?
                    </h2>
                    <ul className="mt-5 space-y-4">
                        {CONTENT.moodFoods.map((item) => (
                            <li key={item.food} className="flex gap-3.5">
                                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-theme-accent" />
                                <div>
                                    <p className="text-sm font-semibold text-theme-text-primary">{item.food}</p>
                                    <p className="mt-0.5 text-xs leading-relaxed text-theme-text-secondary">{item.why}</p>
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            </section>

            {/* ── Recipe search ───────────────────────────────────────────── */}
            <section className={`rounded-[28px] bg-theme-surface/80 p-6 backdrop-blur-2xl lg:p-8`}>
                <div className="mb-5">
                    <p className="text-[10px] uppercase tracking-[0.3em] text-theme-text-secondary/60">Khám phá</p>
                    <h3 className="mt-1.5 font-display text-3xl italic text-theme-text-primary">Tra cứu công thức</h3>
                </div>

                {/* Search input */}
                <div className="relative mb-3">
                    <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-theme-text-secondary" />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Tìm theo tên món, nguyên liệu hoặc lợi ích..."
                        className={`w-full border border-theme-secondary/30 rounded-2xl bg-theme-surface/70 py-3 pl-11 pr-10 text-sm text-theme-text-primary placeholder-theme-text-secondary/45 outline-none transition focus:ring-1 focus:ring-theme-accent/30`}
                    />
                    {query && (
                        <button
                            type="button"
                            onClick={() => setQuery('')}
                            className="absolute right-4 top-1/2 -translate-y-1/2 text-theme-text-secondary/50 transition hover:text-theme-text-secondary"
                        >
                            <X className="h-4 w-4" />
                        </button>
                    )}
                </div>

                {/* Tag pills */}
                <div className="mb-6 flex flex-wrap gap-2">
                    {CONTENT.tags.map((tag) => (
                        <button
                            key={tag}
                            type="button"
                            onClick={() => setActiveTag(activeTag === tag ? null : tag)}
                            className={`rounded-full border px-3 py-1.5 text-xs transition ${activeTag === tag
                                ? 'border-theme-accent bg-theme-accent text-white'
                                : `border-theme-secondary/30 bg-theme-surface text-theme-text-primary hover:border-theme-accent/50`
                                }`}
                        >
                            {tag}
                        </button>
                    ))}
                </div>

                {/* Recipe cards */}
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {filteredRecipes.length === 0 ? (
                        <div className="col-span-3">
                            <PixelEmptyState
                                mascot="eat"
                                title="Chưa tìm thấy công thức phù hợp"
                                description="Thử một nguyên liệu hoặc nhãn khác để tìm gợi ý chăm cơ thể nhẹ nhàng hơn."
                            />
                        </div>
                    ) : (
                        filteredRecipes.map((recipe) => (
                            <article
                                key={recipe.name}
                                className={`rounded-[20px] border border-theme-secondary/50 bg-theme-surface/80 p-4 transition hover:bg-theme-accent/10 hover:border-theme-accent/30`}
                            >
                                <div className="mb-2 flex items-start justify-between gap-2">
                                    <h4 className="text-sm font-semibold leading-snug text-theme-text-primary">{recipe.name}</h4>
                                    <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${MOOD_STYLE[recipe.mood] ?? 'bg-theme-surface text-theme-text-secondary border-theme-border'}`}>
                                        {recipe.mood}
                                    </span>
                                </div>
                                <p className="text-xs leading-relaxed text-theme-text-secondary">{recipe.ingredients}</p>
                                {recipe.benefit && (
                                    <p className="mt-2 text-[11px] leading-relaxed text-theme-text-secondary/70">{recipe.benefit}</p>
                                )}
                                <p className="mt-2.5 text-[10px] text-theme-text-secondary/50">⏱ {recipe.time}</p>
                            </article>
                        ))
                    )}
                </div>

                {!query && !activeTag && (
                    <p className="mt-4 text-center text-[10px] text-theme-text-secondary/45">
                        Gợi ý mới mỗi lần bạn ghé thăm · Tìm kiếm hoặc chọn tag để khám phá thêm
                    </p>
                )}
            </section>
        </div>
    )
}
