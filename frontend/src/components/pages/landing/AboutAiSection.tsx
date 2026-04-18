import RevealSection from './RevealSection'

export default function AboutAiSection() {
    return (
        <RevealSection id="about-ai" className="relative min-h-screen px-6 py-30" delay={0.15}>
            {/* <div className="absolute inset-0 -z-10">
                <img src={bg3} alt="Peaceful deep ocean" className="h-full w-full object-cover" />
                <div className="absolute inset-0 bg-black/30" />
            </div> */}
            <div className="mx-auto flex h-full w-full max-w-4xl items-center justify-center text-center">
                <div className="w-full rounded-4xl border border-white/20 bg-white/10 px-8 py-14 backdrop-blur-3xl sm:px-12">
                    <p className="text-xs uppercase tracking-[0.3em] text-white/80">Digital Sanctuary</p>
                    <h3 className="mt-5 font-display text-4xl italic leading-tight text-white sm:text-6xl">
                        Người bạn AI
                        <br />
                        luôn lắng nghe
                    </h3>
                    <p className="mx-auto mt-7 max-w-3xl text-base leading-relaxed text-white/90 sm:text-lg">
                        Serene là người đồng hành AI thấu cảm, mang đến những cuộc trò chuyện sâu sắc
                        giúp bạn thực hành chánh niệm và giải tỏa căng thẳng trong không gian đại dương an yên.
                    </p>
                </div>
            </div>
        </RevealSection>
    )
}
