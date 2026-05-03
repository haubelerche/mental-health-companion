import RevealSection from '../../../utils/RevealSection'

export default function AboutAiSection() {
    return (
        <RevealSection id="about-ai" className="relative min-h-screen px-6 py-30" variant='fade-left'>
          
            <div className="mx-auto flex h-full w-full max-w-4xl items-center justify-center text-center">
                <div className="w-full rounded-4xl border border-white/20 bg-white/20 px-8 py-14 backdrop-blur-3xl sm:px-12">
                    <p className="text-xs uppercase tracking-[0.3em] text-white/80">Digital Sanctuary</p>
                    <h3 className="mt-5 font-display text-4xl italic leading-tight text-white sm:text-6xl">
                        Người bạn AI
                        <br />
                        luôn lắng nghe
                    </h3>
                    <p className="mx-auto mt-7 max-w-3xl text-base leading-relaxed text-white/90 sm:text-lg">
                        Serene là người đồng hành AI thấu cảm, mang đến những cuộc trò chuyện sâu sắc
                        giúp bạn thực hành chánh niệm và giải tỏa căng thẳng.
                    </p>
                </div>
            </div>
        </RevealSection>
    )
}
