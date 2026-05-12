import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { CalendarDays, Cross, MapPin, Navigation, Phone, Search, UsersRound } from 'lucide-react'
import healing from '../../assets/scenes/healing.jpg'
import { connectService, type ClinicItem, type HotlineItem } from '../../services/connectService'
import { safetyService } from '../../services/safetyService'
import type { ReferralOption } from '../../services/safetyService'
import { useThemeContext } from '../../contexts/ThemeContext'
import Mascot from '../pixel/Mascot'
import { onboardingTourService } from '../../services/onboardingTourService'
import { ROUTE_PATHS } from '../../routes/paths'
const DEFAULT_HOTLINES: HotlineItem[] = [
    { name: 'Hotline 24/7', number: '1800-599-920', description: 'Hỗ trợ khẩn cấp và lắng nghe ngay lập tức' },
    { name: 'Cấp cứu y tế', number: '115', description: 'Gọi cấp cứu trong tình huống nguy hiểm' },
]

const DEFAULT_CLINICS: ClinicItem[] = [
    { name: 'Willow Wellness Clinic', address: 'Chuyên về sức khỏe tâm thần tổng quát và trị liệu thiện định', distance_km: 0.8 },
    { name: 'Ocean Side Support Group', address: 'Nhóm hỗ trợ cộng đồng hằng tuần tập trung vào chữa lành tập thể', distance_km: 1.2 },
    { name: 'Mindful Reach Counseling', address: 'Tham vấn 1-1 với chuyên gia về lo âu và kiệt sức', distance_km: 2.5 },
    { name: 'Peaceful Mind Hotline', address: 'Dịch vụ lắng nghe tình nguyện dành cho những ai cần được thấu hiểu', distance_km: null },
]

const REFERRAL_META: Record<string, { label: string; sub: string; icon: typeof UsersRound }> = {
    counselor: { label: 'Tư vấn viên', sub: 'Đặt lịch tư vấn chuyên nghiệp', icon: CalendarDays },
    trusted_contact: { label: 'Người tin cậy', sub: 'Liên hệ người thân hoặc bạn bè', icon: UsersRound },
    clinic: { label: 'Phòng khám gần bạn', sub: 'Tìm cơ sở y tế phù hợp', icon: MapPin },
}

export default function Support() {
    const navigate = useNavigate()
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const [searchParams] = useSearchParams()
    const [hotlines, setHotlines] = useState<HotlineItem[]>(DEFAULT_HOTLINES)
    const [clinics, setClinics] = useState<ClinicItem[]>(DEFAULT_CLINICS)
    const [referrals, setReferrals] = useState<ReferralOption[]>([])
    const suggestedPlace = useMemo(
        () => searchParams.get('q')?.trim() || searchParams.get('address')?.trim() || searchParams.get('clinic')?.trim() || '',
        [searchParams],
    )
    const initialMapQuery = suggestedPlace || 'phòng tham vấn tâm lý gần tôi'
    const [mapSearch, setMapSearch] = useState(initialMapQuery)
    const [mapQuery, setMapQuery] = useState(initialMapQuery)

    useEffect(() => {
        connectService.hotlines().then((data) => setHotlines(data.hotlines.length ? data.hotlines : DEFAULT_HOTLINES)).catch(() => undefined)
        connectService.clinics().then((data) => setClinics(data.clinics.length ? data.clinics : DEFAULT_CLINICS)).catch(() => undefined)
        safetyService.getReferralOptions()
            .then(d => setReferrals(d.options))
            .catch(() => {
                if (import.meta.env.DEV) console.warn('[Connect] referral options fetch failed')
            })
    }, [])

    const mapSrc = useMemo(
        () => `https://www.google.com/maps?q=${encodeURIComponent(mapQuery)}&output=embed`,
        [mapQuery],
    )
    const mapHref = useMemo(
        () => `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(mapQuery)}`,
        [mapQuery],
    )

    const showClinicOnMap = (clinic: ClinicItem) => {
        const nextQuery = [clinic.name, clinic.address].filter(Boolean).join(', ')
        setMapSearch(nextQuery)
        setMapQuery(nextQuery)
    }

    const handleMapSearch = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        const nextQuery = mapSearch.trim()
        if (!nextQuery) return
        setMapQuery(nextQuery)
    }

    const replayTour = async () => {
        await onboardingTourService.start('first_run')
        navigate(`${ROUTE_PATHS.home}?tour=replay`)
    }

    return (
        <section data-tour-id="help-entry" className="mx-auto max-w-6xl text-theme-text-primary">
            <div className={`rounded-[2.75rem] ${isDark ? 'bg-black/40 border border-white/10' : 'bg-theme-surface/35'} p-6 shadow-xl backdrop-blur-2xl md:p-10`}>
                <div className={`rounded-full  px-6 py-3 text-center font-display tracking-wide text-xl font-semibold italic text-theme-text-secondary/70`}>
                    Serene là AI, không thay thế chuyên gia
                </div>

                <header className="mt-8 flex items-start justify-between gap-5">
                    <div>
                        <p className="text-[0.68rem] font-bold uppercase tracking-[0.34em] text-theme-accent/70">
                            Referral & Human Support
                        </p>
                        <h1 className="mt-2 font-display text-5xl italic leading-none text-theme-text-primary md:text-7xl">
                            You are not alone.
                        </h1>
                        <p className="mt-5 max-w-2xl text-sm leading-relaxed text-theme-text-secondary md:text-base">
                            Nhận sự hỗ trợ chuyên sâu từ con người khi bạn cần. Chúng tôi luôn đồng hành cùng bạn.
                        </p>
                    </div>
                    <Mascot variant="quiet" size="lg" decorative className="hidden md:block" />
                </header>
                <div className="mt-5 flex justify-end">
                    <button
                        type="button"
                        onClick={() => void replayTour()}
                        className="rounded-full bg-theme-accent px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:brightness-105"
                    >
                        Hau dẫn mình đi lại một vòng
                    </button>
                </div>

                <section className={`mt-9 grid gap-6 rounded-[2rem] p-6 shadow-inner lg:grid-cols-[1fr_220px] ${isDark ? 'bg-black/20 border border-white/5' : 'bg-theme-surface/40'}`}>
                    <div>
                        <div className="mb-5 flex items-center gap-3">
                            <span className="font-display text-4xl text-theme-accent">*</span>
                            <div>
                                <h2 className="font-display text-2xl italic text-theme-text-primary">Immediate Support</h2>
                                <p className="mt-2 text-sm text-theme-text-secondary">
                                    Nếu bạn đang trong tình trạng khẩn cấp hoặc cần người lắng nghe ngay lập tức, hãy liên hệ các đường dây nóng dưới đây.
                                </p>
                            </div>
                        </div>

                        <div className="grid gap-4 md:grid-cols-2">
                            {hotlines.slice(0, 2).map((item, index) => (
                                <a
                                    key={`${item.name}-${item.number}`}
                                    href={`tel:${item.number.replace(/\s/g, '')}`}
                                    className={`flex items-center justify-between rounded-3xl ${isDark ? 'bg-white/5 border border-white/5' : 'bg-theme-surface/65'} px-5 py-4 shadow-sm transition hover:-translate-y-0.5 hover:bg-theme-surface/80`}
                                >
                                    <div>
                                        <p className="text-[0.6rem] font-bold uppercase tracking-[0.24em] text-theme-text-secondary/70">
                                            {index === 0 ? 'Hotline 24/7' : 'Cấp cứu y tế'}
                                        </p>
                                        <p className="mt-1 font-display text-3xl font-bold text-theme-text-primary">{item.number}</p>
                                    </div>
                                    {index === 0 ? <Phone className="h-5 w-5 text-theme-accent" /> : <Cross className="h-5 w-5 text-rose-500" />}
                                </a>
                            ))}
                        </div>
                    </div>

                    <img src={healing} alt="" className={`hidden h-full min-h-44 rounded-3xl object-cover shadow-2xl lg:block ${isDark ? 'brightness-75' : ''}`} />
                </section>

                <div className="mt-10 grid gap-8 lg:grid-cols-[1fr_330px]">
                    <section>
                        <h2 className="mb-5 font-display text-2xl italic text-theme-accent/80">Cơ sở hỗ trợ chuyên môn</h2>
                        <div className="grid gap-4 md:grid-cols-2">
                            {clinics.slice(0, 4).map((item, idx) => (
                                <article
                                    key={idx}
                                    className={`rounded-[1.75rem] ${isDark ? 'bg-white/5 border border-white/5' : 'bg-theme-surface/40'} p-5 shadow-lg backdrop-blur-md`}
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <span className="flex h-11 w-11 items-center justify-center rounded-full bg-theme-accent/20 text-theme-accent">
                                            {idx % 2 === 0 ? <MapPin className="h-5 w-5" /> : <UsersRound className="h-5 w-5" />}
                                        </span>
                                        <p className="text-[0.62rem] text-theme-text-secondary">
                                            {item.distance_km ? `${item.distance_km} km away` : 'Trực tuyến'}
                                        </p>
                                    </div>
                                    <h3 className="mt-5 font-display text-xl text-theme-text-primary">{item.name}</h3>
                                    <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-theme-text-secondary">{item.address || 'VinMec'}</p>
                                    <button
                                        type="button"
                                        onClick={() => showClinicOnMap(item)}
                                        className="mt-5 text-[0.65rem] font-bold uppercase tracking-[0.2em] text-theme-accent"
                                    >
                                        Xem trên bản đồ ↗
                                    </button>
                                </article>
                            ))}
                        </div>
                    </section>

                    <aside>
                        <h2 className="mb-5 font-display text-2xl italic text-theme-text-primary">Phòng tham vấn tâm lý gần nhất</h2>
                        <div className={`overflow-hidden rounded-[2rem] ${isDark ? 'bg-black/30 border border-white/10' : 'bg-theme-surface/45'} p-3 shadow-2xl backdrop-blur-xl`}>
                            <form onSubmit={handleMapSearch} className={`mb-3 flex items-center gap-2 rounded-full ${isDark ? 'bg-white/5' : 'bg-theme-surface'} px-3 py-2 shadow-sm`}>
                                <Search className="h-4 w-4 shrink-0 text-theme-accent" />
                                <input
                                    value={mapSearch}
                                    onChange={(event) => setMapSearch(event.target.value)}
                                    placeholder="Nhập địa chỉ hoặc phòng tham vấn..."
                                    className="min-w-0 flex-1 bg-transparent text-xs text-theme-text-primary outline-none placeholder:text-theme-text-secondary/60"
                                    aria-label="Tìm địa chỉ trên bản đồ"
                                />
                                <button
                                    type="submit"
                                    className="rounded-full bg-theme-accent px-3 py-1.5 text-[0.65rem] font-bold uppercase tracking-[0.18em] text-white"
                                >
                                    Tìm
                                </button>
                            </form>

                            <div className={`relative h-[310px] overflow-hidden rounded-[1.6rem] ${isDark ? 'brightness-90 opacity-90' : 'bg-theme-surface'}`}>
                                <iframe
                                    key={mapSrc}
                                    title={`Bản đồ ${mapQuery}`}
                                    src={mapSrc}
                                    className="h-full w-full border-0"
                                    loading="lazy"
                                    referrerPolicy="no-referrer-when-downgrade"
                                    allowFullScreen
                                />
                                <a
                                    href={mapHref}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="absolute bottom-3 right-3 inline-flex items-center gap-2 rounded-full bg-theme-accent px-4 py-3 text-xs font-semibold text-white shadow-lg"
                                >
                                    <Navigation className="h-4 w-4" /> Mở Maps
                                </a>
                            </div>
                        </div>
                    </aside>
                </div>

                <div className={`mx-auto mt-12 max-w-xl rounded-[2rem] ${isDark ? 'bg-black/20 border border-white/5' : 'bg-theme-surface/40'} px-7 py-6 text-center shadow-lg`}>
                    <p className="font-display text-2xl italic text-theme-text-primary">
                        "Peace is not the absence of trouble, but the presence of connection."
                    </p>
                </div>
            </div>

            {referrals.length > 0 && (
                <section className={`mt-6 rounded-4xl bg-theme-surface/55 backdrop-blur-xl p-5 `}>
                    <h3 className="mb-4 font-display text-2xl text-theme-text-primary">Gợi ý hỗ trợ từ Serene</h3>
                    <div className="grid gap-3 md:grid-cols-3">
                        {referrals.map(r => {
                            const meta = REFERRAL_META[r.type] ?? { label: r.type, sub: '', icon: Navigation }
                            const Icon = meta.icon  
                            return (
                                <div
                                    key={r.type}
                                    className={`flex items-center gap-3 rounded-2xl p-4 ${isDark ? 'bg-white/10 border border-white/5' : 'bg-theme-surface/50'}`}
                                >
                                    <Icon className="h-5 w-5 text-theme-accent" />
                                    <div>
                                        <div className="text-sm font-semibold text-theme-text-primary">{meta.label}</div>
                                        <div className="mt-0.5 text-xs text-theme-text-secondary">{meta.sub}</div>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </section>
            )}
        </section>
    )
}
