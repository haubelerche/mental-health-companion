import bg from '../../../assets/bg.png'
import Header from '../../layout/HeaderLanding'
import AboutAiSection from './AboutAiSection'
import BreathSection from './BreathSection'
import HeroSection from './HeroSection'
import OceanSoundSection from './OceanSoundSection'

export default function Home() {
    return (
        <div className="relative min-h-screen text-gray-50">
            <div className="fixed inset-0 -z-20">
                <img src={bg} alt="Serene sunset ocean" className="h-full w-full object-cover" />
                <div className="absolute inset-0 bg-black/20" />
            </div>
            <Header />
            <main className="relative z-10">
                <HeroSection />
                <AboutAiSection />
                <OceanSoundSection />
                <BreathSection />
            </main>
        </div>
    )
}