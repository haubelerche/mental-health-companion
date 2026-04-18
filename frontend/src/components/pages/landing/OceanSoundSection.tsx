import bg from '../../../assets/bg.png'

export default function OceanSoundSection() {
    return (
        <section id="ocean-sound" className="px-6 py-30">
            <div className="mx-auto grid w-full max-w-7xl grid-cols-1 gap-10 lg:grid-cols-2 lg:items-center">
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
                        <article className="rounded-3xl border border-white/20 bg-white/10 p-6 backdrop-blur-xl transition hover:bg-white/15">
                            <h5 className="font-display text-2xl italic text-white">Ocean Ambient</h5>
                            <p className="mt-2 text-white/80">Âm thanh đại dương thực tế từ những bờ biển yên bình.</p>
                        </article>
                        <article className="rounded-3xl border border-white/20 bg-white/10 p-6 backdrop-blur-xl transition hover:bg-white/15">
                            <h5 className="font-display text-2xl italic text-white">Breath of the Sea</h5>
                            <p className="mt-2 text-white/80">Điều hòa nhịp thở theo chu kỳ tự nhiên của thủy triều.</p>
                        </article>
                    </div>
                </div>

                <div className="relative">
                    <div className="aspect-4/5 overflow-hidden rounded-4xl border border-white/15 shadow-[0_40px_60px_-20px_rgba(0,0,0,0.35)]">
                        <img src={bg} alt="Ocean water detail" className="h-full w-full object-cover" />
                        <div className="absolute inset-0 bg-linear-to-t from-black/75 via-transparent to-transparent border border-white/10 rounded-4xl" />
                    </div>
                    <div className="absolute bottom-8 left-8 right-8 rounded-3xl border border-white/20 bg-white/10 p-6 backdrop-blur-2xl">
                        <p className="font-display text-2xl italic text-white">Serene</p>
                        <p className="mt-2 text-sm text-white/90">
                            "Để tâm hồn bạn trôi theo dòng chảy của sự bình yên."
                        </p>
                    </div>
                </div>
            </div>
        </section>
    )
}
