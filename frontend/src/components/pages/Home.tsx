
import { Link } from 'react-router-dom'
import bg from '../../assets/bg.png'
import HeroSection from './landing/HeroSection'
import AboutAiSection from './landing/AboutAiSection'
import OceanSoundSection from './landing/OceanSoundSection'
import BreathSection from './landing/BreathSection'

export default function Home() {
    return (
        <div className="relative min-h-screen text-white">
            <div className="fixed inset-0 -z-20">
                <img src={bg} alt="Serene sunset ocean" className="h-full w-full object-cover" />
                <div className="absolute inset-0 bg-black/20" />
            </div>

            {/* <div className="auth-noise -z-10" /> */}

            <header className="sticky top-0 z-40 border-b border-white/10 bg-black/10 backdrop-blur-xl">
                <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4">
                    <h1 className="font-display text-3xl italic tracking-tight text-white">Serene</h1>
                    <nav className="hidden items-center gap-8 md:flex">
                        <a href="#hero" className="text-sm tracking-wide text-white/85 hover:text-white">Hero</a>
                        <a href="#about-ai" className="text-sm tracking-wide text-white/85 hover:text-white">AI Companion</a>
                        <a href="#ocean-sound" className="text-sm tracking-wide text-white/85 hover:text-white">Ocean Sound</a>
                        <a href="#breath-space" className="text-sm tracking-wide text-white/85 hover:text-white">Breath</a>
                    </nav>
                    <Link to="/login" className="rounded-full bg-white px-5 py-2 text-sm font-semibold text-serene-ink transition hover:bg-white/90">
                        Đăng nhập
                    </Link>
                </div>
            </header>

            <main className="relative z-10">
                <HeroSection />
                <AboutAiSection />
                <OceanSoundSection />
                <BreathSection />
            </main>
        </div>
    )
}