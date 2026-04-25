import { useEffect, useState } from 'react'
import { connectService, type ClinicItem, type HotlineItem } from '../../services/connectService'
import { safetyService } from '../../services/safetyService'
import type { ReferralOption } from '../../services/safetyService'

const REFERRAL_META: Record<string, { label: string; sub: string; emoji: string }> = {
    counselor:       { label: 'Tư vấn viên', sub: 'Đặt lịch tư vấn chuyên nghiệp', emoji: '👨‍⚕️' },
    trusted_contact: { label: 'Người tin cậy', sub: 'Liên hệ người thân hoặc bạn bè', emoji: '🤝' },
    clinic:          { label: 'Phòng khám gần bạn', sub: 'Tìm cơ sở y tế phù hợp', emoji: '🏥' },
}

export default function Connect() {
    const [hotlines, setHotlines] = useState<HotlineItem[]>([])
    const [clinics, setClinics] = useState<ClinicItem[]>([])
    const [referrals, setReferrals] = useState<ReferralOption[]>([])

    useEffect(() => {
        connectService.hotlines().then((data) => setHotlines(data.hotlines)).catch(() => undefined)
        connectService.clinics().then((data) => setClinics(data.clinics)).catch(() => undefined)
        safetyService.getReferralOptions()
            .then(d => setReferrals(d.options))
            .catch(() => {
                if (import.meta.env.DEV) console.warn('[Connect] referral options fetch failed')
            })
    }, [])

    return (
        <section className="rounded-3xl border border-white/35 bg-white/60 p-8 backdrop-blur-xl">
            <h2 className="font-display text-4xl text-serene-ink">Kết nối</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div>
                    <h3 className="mb-2 text-sm font-semibold text-serene-ink">Hotlines</h3>
                    <div className="space-y-2">
                        {hotlines.map((item) => (
                            <a
                                key={`${item.label}-${item.phone}`}
                                href={`tel:${item.phone.replace(/\s/g, '')}`}
                                className="block rounded-lg bg-white/80 px-3 py-2 text-sm text-serene-ink"
                            >
                                {item.label}: <span className="font-semibold">{item.phone}</span>
                            </a>
                        ))}
                    </div>
                </div>
                <div>
                    <h3 className="mb-2 text-sm font-semibold text-serene-ink">Cơ sở hỗ trợ</h3>
                    <div className="space-y-2">
                        {clinics.slice(0, 6).map((item, idx) => (
                            <article key={`${item.name}-${idx}`} className="rounded-lg bg-white/80 px-3 py-2 text-sm">
                                <p className="font-medium text-serene-ink">{item.name}</p>
                                <p className="text-serene-muted">{item.address || 'VinMec'}</p>
                            </article>
                        ))}
                    </div>
                </div>
            </div>
            {referrals.length > 0 && (
                <section className="mt-6">
                    <h3 className="font-semibold text-[var(--color-serene-ink)] mb-3 text-base">
                        <span aria-hidden="true">🧭</span> Kết nối hỗ trợ
                    </h3>
                    <div className="flex flex-col gap-3">
                        {referrals.map(r => {
                            const meta = REFERRAL_META[r.type] ?? { label: r.type, sub: '', emoji: '📋' }
                            return (
                                <div
                                    key={r.type}
                                    className="bg-[var(--color-la-ban-bg)] rounded-2xl p-4 flex items-center gap-3"
                                >
                                    <span className="text-2xl" aria-hidden="true">{meta.emoji}</span>
                                    <div>
                                        <div className="font-semibold text-[var(--color-serene-ink)] text-sm">{meta.label}</div>
                                        <div className="text-xs text-[var(--color-serene-muted)] mt-0.5">{meta.sub}</div>
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
