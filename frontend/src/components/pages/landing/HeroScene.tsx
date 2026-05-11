import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

// Asset imports
import landingSunny from '../../../assets/motion/landing-sunny.gif'
import landingRain from '../../../assets/motion/landing-rain.gif'
import birdGif from '../../../assets/motion/bird.gif'

// Preload rain GIF so it's ready when user scrolls
const preloadRain = new Image()
preloadRain.src = landingRain

type Phase = 'sunny' | 'rain' | 'done'

export default function HeroScene() {
    const wrapperRef = useRef<HTMLDivElement>(null)
    const [phase, setPhase] = useState<Phase>('sunny')
    const [rainLoaded, setRainLoaded] = useState(false)

    const subtitleMap: Record<Phase, string> = {
        sunny: 'Không cần cố tỏ ra mạnh mẽ. Chỉ cần là chính mình.',
        rain: 'Đôi khi mọi thứ không ổn — và điều đó hoàn toàn bình thường.',
        done: 'Serene ở đây, khi bạn sẵn sàng.',
    }

    useEffect(() => {
        const wrapper = wrapperRef.current
        if (!wrapper) return

        let lastPhase: Phase = 'sunny'
        // Total scroll space = 300vh; sticky viewport = 100vh → 200vh of "scroll travel"
        // Phase change thresholds:
        //   0–33%   → sunny
        //   33–66%  → rain
        //   66–100% → done (released by browser naturally)
        const handleScroll = () => {
            const rect = wrapper.getBoundingClientRect()
            const wrapperH = wrapper.offsetHeight        // 300vh
            const traveled = -rect.top                  // how far we've scrolled into wrapper
            const viewH = window.innerHeight
            const travelMax = wrapperH - viewH          // 200vh of scroll travel
            const ratio = Math.max(0, Math.min(1, traveled / travelMax))

            let next: Phase = 'sunny'
            if (ratio >= 0.66) next = 'done'
            else if (ratio >= 0.33) next = 'rain'

            if (next !== lastPhase) {
                lastPhase = next
                setPhase(next)
            }
        }

        window.addEventListener('scroll', handleScroll, { passive: true })
        return () => window.removeEventListener('scroll', handleScroll)
    }, [])

    // 'rain' and 'done' both show the rain scene; 'done' just hides the CTA
    const sunnyOpacity = phase === 'sunny' ? 1 : 0
    // Only show rain if it has loaded — else fall back to keeping sunny visible
    const rainOpacity = phase !== 'sunny' && rainLoaded ? 1 : 0
    const effectiveSunnyOpacity = rainOpacity === 0 ? 1 : sunnyOpacity

    return (
        // 300vh tall wrapper — gives browser scroll room while sticky child stays fixed
        <div ref={wrapperRef} className="hero-wrapper">
            <div className="hero-sticky">
                {/* Sunny layer — stays visible until rain is ready */}
                <div
                    className="hero-scene-layer hero-sunny"
                    style={{ opacity: effectiveSunnyOpacity }}
                    aria-hidden={phase !== 'sunny' && rainLoaded}
                >
                    <img
                        src={landingSunny}
                        alt="Cảnh ban ngày yên bình"
                        className="pixel-img"
                        loading="eager"
                        decoding="async"
                    />
                </div>

                {/* Rain layer */}
                <div
                    className="hero-scene-layer hero-rain"
                    style={{ opacity: rainOpacity }}
                    aria-hidden={phase === 'sunny'}
                >
                    <img
                        src={landingRain}
                        alt="Cảnh mưa nhẹ nhàng"
                        className="pixel-img"
                        loading="eager"
                        decoding="async"
                        onLoad={() => setRainLoaded(true)}
                    />
                </div>

                {/* Dark overlay */}
                <div className="hero-overlay" />

                {/* Bird accent */}
                <img
                    src={birdGif}
                    alt=""
                    aria-hidden="true"
                    className="hero-bird pixel-img"
                />

                {/* Content */}
                <div className="hero-content">
                    <span className="section-label" style={{ 
                        marginBottom: '1rem',
                        textShadow: '2px 2px 0 #020812, -1px -1px 0 #020812, 1px -1px 0 #020812, -1px 1px 0 #020812, 1px 1px 0 #020812'
                    }}>
                        SereneAI·Người bạn đồng hành sức khoẻ tâm thần
                    </span>

                    <h1
                        className="pixel-headline"
                        style={{
                            fontSize: 'clamp(4.5rem, 2.5vw, 2.5rem)',
                            maxWidth: '820px',
                            marginBottom: '1.5rem',
                            fontWeight: '700',
                            textShadow: '3px 3px 0 #020812, -1px -1px 0 #020812, 1px -1px 0 #020812, -1px 1px 0 #020812, 1px 1px 0 #020812'
                        }}
                    >
                        Nơi an toàn để<br />
                        bạn nói thật.
                    </h1>

                    <p
                        className="vn-body-bright"
                        style={{
                            maxWidth: '560px',
                            fontSize: '1.05rem',
                            marginBottom: '2.5rem',
                            transition: 'opacity 0.5s ease',
                            color: 'rgba(237,247,255,0.92)',
                            letterSpacing: '0.05rem',
                            textShadow: '2px 1px 2px rgba(0,0,0,0.8)'
                        }}
                    >
                        {subtitleMap[phase]}
                    </p>

                    {/* CTA — only show on sunny/rain phases */}
                    <div
                        style={{
                            display: 'flex',
                            gap: '1rem',
                            flexWrap: 'wrap',
                            justifyContent: 'center',
                            opacity: phase === 'done' ? 0 : 1,
                            transition: 'opacity 0.4s ease',
                            fontWeight: '600',
                        }}
                    >
                        <Link to="/serene" className="pixel-btn">
                            Bắt đầu ngay →
                        </Link>

                    </div>
                </div>

                {/* Scroll hint — only on sunny */}
                {phase === 'sunny' && (
                    <div className="hero-scroll-hint text-white font-bold" aria-hidden="true">
                        <span
                            style={{
                                fontFamily: 'var(--font-pixel)',
                                fontSize: '1.5rem',
                               
                                letterSpacing: '0.2em',
                            }}
                        >
                            cuộn xuống
                        </span>
                        <svg
                            width="16"
                            height="16"
                            viewBox="0 0 16 16"
                            fill="none"
                          
                        >
                            <path
                                d="M8 2L8 14M8 14L3 9M8 14L13 9"
                                stroke="currentColor"
                                strokeWidth="1.5"
                                strokeLinecap="square"
                            />
                        </svg>
                    </div>
                )}
            </div>
        </div>
    )
}
