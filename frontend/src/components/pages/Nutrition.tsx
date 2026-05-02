import { useEffect, useState, useMemo } from 'react'
import { Search, Sparkles, X } from 'lucide-react'
import { dashboardService, type NutritionDailyTip } from '../../services/dashboardService'
import a1 from '../../assets/nutrition-a1.jpg'
import a2 from '../../assets/nutrition-a2.jpg'
// ─── Static pools (randomised each mount) ──────────────────────────────────────

const DAILY_FACTS = [
    'Não bộ tiêu thụ ~20% tổng năng lượng cơ thể mỗi ngày — mỗi bữa ăn bạn đang nuôi trực tiếp tư duy và cảm xúc.',
    '90% serotonin được sản xuất tại ruột, không phải não. Hệ vi sinh vật đường ruột chính là "cơ quan cảm xúc" thứ hai.',
    'Omega-3 DHA trong cá hồi xây màng tế bào thần kinh — thiếu Omega-3 liên quan đến tăng nguy cơ trầm cảm lên 2–3 lần.',
    'Thiếu magiê làm hệ thần kinh dễ bị kích thích hơn, gây lo âu và mất ngủ. Hạt bí, rau cải xanh là nguồn dồi dào.',
    'Chế độ ăn Địa Trung Hải giảm nguy cơ trầm cảm 33% so với chế độ phương Tây, theo nghiên cứu 10.000 người tại Tây Ban Nha.',
    'Đường tinh luyện gây viêm thần kinh — cơ chế trực tiếp làm giảm BDNF, protein cần thiết để não hình thành ký ức mới.',
    'Vitamin D từ trứng, cá béo và ánh nắng kích hoạt hơn 200 gene liên quan đến sức khỏe não và hệ miễn dịch.',
    'Một bữa sáng giàu protein duy trì dopamine cao suốt buổi sáng — lý do vì sao bỏ bữa sáng liên quan đến khó tập trung.',
]

const ALL_RECIPES = [
    { name: 'Smoothie xanh gừng & cải bó xôi', mood: 'Năng lượng', time: '5 phút', tags: ['Buổi sáng', 'Chay', 'Tăng năng lượng'], ingredients: 'Cải bó xôi, chuối, gừng tươi, sữa hạnh nhân, hạt lanh' },
    { name: 'Bơ toast + trứng lòng đào', mood: 'Tập trung', time: '10 phút', tags: ['Buổi sáng', 'Protein cao'], ingredients: 'Bánh mì đen, bơ trái, trứng, muối hồng Himalaya, ớt khô' },
    { name: 'Yến mạch qua đêm & quả mọng', mood: 'Ổn định', time: '8 phút', tags: ['Buổi sáng', 'Ít đường', 'Chay'], ingredients: 'Yến mạch rolled, sữa hạt, việt quất, dâu tây, hạt chia, mật ong' },
    { name: 'Cá hồi nướng & quinoa xanh', mood: 'Vui vẻ', time: '25 phút', tags: ['Omega-3', 'Protein cao'], ingredients: 'Cá hồi, quinoa, bông cải xanh, chanh, dầu olive, tỏi' },
    { name: 'Salad óc chó táo xanh', mood: 'Trí nhớ', time: '10 phút', tags: ['Chay', 'Trị lo âu'], ingredients: 'Rau arugula, táo xanh, óc chó, phô mai brie, giấm balsamic' },
    { name: 'Cháo đậu đỏ nấm shiitake', mood: 'Thư giãn', time: '30 phút', tags: ['Chay', 'Ngủ ngon'], ingredients: 'Đậu đỏ, nấm shiitake, gạo lứt, dầu mè, rong biển khô' },
    { name: 'Dark chocolate & berry bark', mood: 'Hạnh phúc', time: '15 phút', tags: ['Ít đường', 'Tăng năng lượng'], ingredients: 'Socola đen 75%, quả mâm xôi, hạt lanh, fleur de sel' },
    { name: 'Miso soup đậu hũ & wakame', mood: 'Bình yên', time: '12 phút', tags: ['Chay', 'Ngủ ngon'], ingredients: 'Tương miso trắng, đậu hũ non, rong wakame, nấm enoki, hành lá' },
    { name: 'Overnight chia pudding xoài', mood: 'Năng lượng', time: '5 phút', tags: ['Buổi sáng', 'Chay', 'Ít đường'], ingredients: 'Hạt chia, sữa dừa, xoài tươi, vani, mật agave' },
    { name: 'Cơm gạo lứt gà & rau xào', mood: 'Ổn định', time: '20 phút', tags: ['Protein cao'], ingredients: 'Gạo lứt, ức gà, bông cải xanh, dưa leo, mè đen' },
    { name: 'Trà matcha latte hạt yến', mood: 'Tập trung', time: '5 phút', tags: ['Buổi sáng', 'Ít đường'], ingredients: 'Bột matcha, sữa yến mạch, mật ong, bột quế' },
    { name: 'Salad cá ngừ avocado', mood: 'Trí nhớ', time: '8 phút', tags: ['Omega-3', 'Protein cao'], ingredients: 'Cá ngừ đóng hộp, bơ, dưa chuột, chanh, rau mùi tây' },
]

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

const TAGS = ['Buổi sáng', 'Chay', 'Tăng năng lượng', 'Trị lo âu', 'Ngủ ngon', 'Protein cao', 'Ít đường', 'Omega-3']

// ─── Component ─────────────────────────────────────────────────────────────────

export default function Nutrition() {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const [dailyTip, setDailyTip] = useState<NutritionDailyTip | null>(null)
    const [query, setQuery] = useState('')
    const [activeTag, setActiveTag] = useState<string | null>(null)

    const todayFact = useMemo(
        () => DAILY_FACTS[Math.floor(Math.random() * DAILY_FACTS.length)],
        [],
    )

    const featuredRecipes = useMemo(() => {
        return [...ALL_RECIPES].sort(() => Math.random() - 0.5).slice(0, 3)
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
        return ALL_RECIPES.filter((r) => {
            const matchQuery = !q || r.name.toLowerCase().includes(q) || r.ingredients.toLowerCase().includes(q)
            const matchTag = !activeTag || r.tags.includes(activeTag)
            return matchQuery && matchTag
        }).slice(0, 6)
    }, [query, activeTag, featuredRecipes])

    const MOOD_STYLE = getMoodStyle(isDark)

    return (
        <div className="space-y-6 pb-16 lg:space-y-8">

            {/* ── Daily fact banner ───────────────────────────────────────── */}
            <section className="flex items-start gap-3 rounded-[22px] bg-theme-accent/20 px-5 py-4 backdrop-blur-sm">
                <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-theme-accent" />
                <div>
                    <p className="mb-1 text-[10px] uppercase tracking-[0.28em] text-theme-accent/70">Fact hôm nay</p>
                    <p className="text-sm leading-relaxed text-theme-text-primary">{todayFact}</p>
                </div>
            </section>

            {/* ── Section 1: Content LEFT · Image RIGHT ──────────────────── */}
            <section className="grid gap-4 lg:grid-cols-2 lg:items-stretch">

                <div className={`flex flex-col justify-center rounded-[28px] ${isDark ? 'bg-black/30' : 'bg-theme-surface/45'} p-7 backdrop-blur-xl lg:p-9`}>
                    <p className="text-[10px] uppercase tracking-[0.3em] text-theme-text-secondary/60">Khoa học nền tảng</p>
                    <h1 className="mt-3 font-display text-4xl italic leading-tight text-theme-text-primary sm:text-5xl">
                        Dinh dưỡng<br />định hình<br />tâm trí
                    </h1>
                    <p className="mt-5 text-sm leading-relaxed text-theme-text-secondary">
                        Não bộ tiêu thụ khoảng 20% năng lượng cơ thể mỗi ngày. Mỗi bữa ăn không chỉ là nhiên liệu — đó là nguyên liệu trực tiếp để não sản xuất serotonin, dopamine và GABA, những chất điều phối cảm xúc, sự tập trung và giấc ngủ.
                    </p>
                    <p className="mt-3 text-sm leading-relaxed text-theme-text-secondary">
                        Nghiên cứu từ Đại học Melbourne (2017) cho thấy thay đổi chế độ ăn 12 tuần giảm triệu chứng trầm cảm hiệu quả tương đương liệu pháp tâm lý — một phát hiện thay đổi cách nhìn nhận về sức khỏe tâm thần hoàn toàn.
                    </p>
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

                <div className={`flex flex-col justify-center rounded-[28px] ${isDark ? 'bg-black/30' : 'bg-theme-surface/45'} p-7 backdrop-blur-xl lg:p-9`}>
                    <p className="text-[10px] uppercase tracking-[0.3em] text-theme-text-secondary/60">Tăng cường tâm trạng</p>
                    <h2 className="mt-3 font-display text-4xl italic leading-tight text-theme-text-primary sm:text-5xl">
                        Ăn gì<br />để vui hơn?
                    </h2>
                    <ul className="mt-5 space-y-4">
                        {[
                            { food: 'Cá hồi & cá mòi', why: 'Omega-3 DHA xây dựng màng tế bào thần kinh, giảm viêm não, cải thiện tâm trạng rõ rệt.' },
                            { food: 'Việt quất & dâu tây', why: 'Flavonoid tăng tuần hoàn não, hỗ trợ trí nhớ ngắn hạn và phản xạ nhận thức.' },
                            { food: 'Óc chó & hạt lanh', why: 'ALA (tiền chất Omega-3) và magiê — bộ đôi giảm lo âu và ổn định thần kinh.' },
                            { food: 'Kimchi, miso, sữa chua', why: 'Lợi khuẩn sản sinh GABA và nuôi dưỡng trục ruột–não, điều hòa serotonin nội sinh.' },
                        ].map((item) => (
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
            <section className={`rounded-[28px] ${isDark ? 'bg-black/30' : 'bg-theme-surface/45'} p-6 backdrop-blur-xl lg:p-8`}>
                <div className="mb-5">
                    <p className="text-[10px] uppercase tracking-[0.3em] text-theme-text-secondary/60">Khám phá</p>
                    <h3 className="mt-1.5 font-display text-3xl italic text-theme-text-primary">Tra cứu công thức</h3>
                </div>

                {/* Search input */}
                <div className="relative mb-3">
                    <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-theme-text-secondary/45" />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Tìm theo tên món hoặc nguyên liệu..."
                        className={`w-full rounded-2xl ${isDark ? 'bg-white/5 border border-white/10' : 'bg-theme-surface/70'} py-3 pl-11 pr-10 text-sm text-theme-text-primary placeholder-theme-text-secondary/45 outline-none transition focus:ring-1 focus:ring-theme-accent/30`}
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
                    {TAGS.map((tag) => (
                        <button
                            key={tag}
                            type="button"
                            onClick={() => setActiveTag(activeTag === tag ? null : tag)}
                            className={`rounded-full border px-3 py-1.5 text-xs transition ${activeTag === tag
                                ? 'border-theme-accent bg-theme-accent text-white'
                                : `${isDark ? 'border-white/10 bg-white/5 text-white/50 hover:bg-white/10 hover:text-white/80' : 'border-theme-border/30 bg-theme-surface/60 text-theme-text-secondary hover:border-theme-accent/50 hover:text-theme-text-primary'}`
                                }`}
                        >
                            {tag}
                        </button>
                    ))}
                </div>

                {/* Recipe cards */}
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {filteredRecipes.length === 0 ? (
                        <p className="col-span-3 py-10 text-center text-sm text-theme-text-secondary/60">
                            Không tìm thấy công thức phù hợp.
                        </p>
                    ) : (
                        filteredRecipes.map((recipe) => (
                            <article
                                key={recipe.name}
                                className={`rounded-[20px] border ${isDark ? 'border-white/10 bg-white/5' : 'border-theme-border/20 bg-theme-surface/65'} p-4 transition hover:bg-theme-accent/10 hover:border-theme-accent/30`}
                            >
                                <div className="mb-2 flex items-start justify-between gap-2">
                                    <h4 className="text-sm font-semibold leading-snug text-theme-text-primary">{recipe.name}</h4>
                                    <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${MOOD_STYLE[recipe.mood] ?? 'bg-theme-surface text-theme-text-secondary border-theme-border'}`}>
                                        {recipe.mood}
                                    </span>
                                </div>
                                <p className="text-xs leading-relaxed text-theme-text-secondary">{recipe.ingredients}</p>
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
