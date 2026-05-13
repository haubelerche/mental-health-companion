import './landing.css'
import LandingHeader from './LandingHeader'
import HeroScene from './HeroScene'
import WhySereneSection from './WhySereneSection'
import SleepyNightSection from './SleepyNightSection'
import FeaturesSection from './FeaturesSection'
import PersonaSection from './PersonaSection'
import JourneySection from './JourneySection'
import FinalCTASection from './FinalCTASection'
import LandingFooter from './LandingFooter'

export default function Landing() {
    return (
        <div className="serene-landing">
            {/* Fixed elements */}
            <LandingHeader />
            {/* Main content */}
            <main>
                <HeroScene />
                {/* Content sections */}
                <WhySereneSection />
                <SleepyNightSection />
                <FeaturesSection />
                <PersonaSection />
                <JourneySection />
                <FinalCTASection />
            </main>
            <LandingFooter />
        </div>
    )
}