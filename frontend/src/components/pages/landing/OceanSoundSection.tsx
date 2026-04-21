import { Droplets, Waves, Wind } from 'lucide-react'
import bg from '../../../assets/healing.jpg'
import RevealSection from '../../../utils/RevealSection'

export default function OceanSoundSection() {
    return (
        <RevealSection id="ocean-sound" className="relative min-h-screen px-6 py-20" delay={0.2}>
            <div className="mx-auto w-full max-w-7xl flex gap-5 flex-col lg:items-center lg:justify-between lg:flex-row">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.35em] text-white/75">Ocean Awareness</p>
                    <h4 className="mt-6 font-display text-4xl italic leading-tight text-white sm:text-6xl">
                        Âm thanh của
                        <br />
                        sự tĩnh lặng
                    </h4>
                    <p className="mt-6 max-w-xl text-base leading-relaxed text-white/85 sm:text-lg">
                        Khám phá sức mạnh chữa lành của sóng biển và nhịp thở chậm rãi.
                        Tại đây bạn có thể ngắt kết nối với ồn ào, và kết nối lại với chính mình.
                    </p>

                    <div className="mt-10 space-y-5">
                        <article className="flex gap-3 items-center rounded-3xl border border-white/20 backdrop p-5">
                            <Waves size={40} className="text-white/50" />
                            <div>
                                <h5 className="font-display text-2xl italic text-white">Ocean Ambient</h5>
                                <p className=" text-white/80">Âm thanh đại dương thực tế từ những bờ biển yên bình.</p>
                            </div>
                        </article>
                        <article className="flex gap-3 items-center rounded-3xl border border-white/20 backdrop p-5">
                            <Wind size={40} className="text-white/50" />
                            <div>
                                <h5 className="font-display text-2xl italic text-white">Breath of the Sea</h5>
                                <p className=" text-white/80">Điều hòa nhịp thở theo chu kỳ tự nhiên của thủy triều.</p>
                            </div>
                        </article>
                    </div>
                </div>

                <div className="relative">
                    <div className="aspect-3/4 overflow-hidden rounded-4xl border border-white/15">
                        <img src={bg} alt="Ocean water detail" height={540} width={480} className="object-cover" />
                        <div className="absolute inset-0 bg-linear-to-t from-black/75 via-transparent to-transparent border border-white/10 rounded-4xl" />
                        <div className="absolute inset-0 bg-linear-to-b from-black/45 via-transparent to-transparent border border-white/10 rounded-4xl" />
                    </div>
                    <div className="flex items-center gap-3 absolute bottom-8 left-8 right-8 rounded-3xl border border-white/20 backdrop p-5">
                        <Droplets />
                        <div>
                            <p className="font-display text-2xl italic text-white">Serene</p>
                            <p className=" text-sm text-white/90 font-display italic">
                                "Để tâm hồn bạn trôi theo dòng chảy của sự bình yên."
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </RevealSection>
    )
}
