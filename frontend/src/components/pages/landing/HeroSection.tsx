import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import RevealSection from '../../../utils/RevealSection'

export default function HeroSection() {
    return (
        <RevealSection id="hero" className="flex min-h-screen items-center px-6 py-30" delay={0}>
            <div className="mx-auto w-full max-w-5xl text-center">
                <h2 className="font-display text-5xl italic leading-tight text-white drop-shadow-2xl sm:text-7xl lg:text-8xl">
                    Tìm lại sự bình yên
                    <br />
                    trong tâm hồn
                </h2>
                <p className="mx-auto mt-8 max-w-3xl text-base font-light text-white/90 sm:text-xl drop-shadow-md">
                    Serene đồng hành cùng bạn trên hành trình thấu hiểu bản thân thông qua
                    sự tĩnh lặng của đại dương.
                </p>
                <div className="mt-10 flex items-center justify-center gap-4">
                    <Link
                        to="/register"
                        className="inline-flex items-center gap-2 font-display rounded-full border border-white/30 bg-white/20 px-9 py-4 text-2xl italic backdrop-blur-3xl transition hover:bg-white/40"
                    >
                        Bắt đầu ngay
                        <ArrowRight />
                    </Link>
                </div>
            </div>
        </RevealSection>
    )
}
