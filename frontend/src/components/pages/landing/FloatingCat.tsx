import { useEffect, useState } from 'react'
import catDay from '../../../assets/motion/cat-soul-2.gif'
import catNight from '../../../assets/motion/cat-soul.gif'
import catSunset from '../../../assets/motion/evening-sunset.gif'

/**
 * FloatingCat — fixed bottom-right corner.
 * Cross-fades day cat → sunset cat → night cat based on scroll depth.
 */
export default function FloatingCat() {
    const [stage, setStage] = useState<'day' | 'sunset' | 'night'>('day')

    useEffect(() => {
        const updateTheme = () => {
            const scrollY = window.scrollY
            const docHeight = document.documentElement.scrollHeight - window.innerHeight
            if (docHeight <= 0) return
            
            const progress = scrollY / docHeight
            if (progress < 0.33) {
                setStage('day')
            } else if (progress < 0.66) {
                setStage('sunset')
            } else {
                setStage('night')
            }
        }

        window.addEventListener('scroll', updateTheme, { passive: true })
        updateTheme()
        return () => window.removeEventListener('scroll', updateTheme)
    }, [])

    return (
        <div
            aria-hidden="true"
            style={{
                position: 'fixed',
                bottom: 28,
                right: 24,
                zIndex: 999,
                width: 110,
                height: 110,
                pointerEvents: 'none',
            }}
        >
            {/* Day cat */}
            <img
                src={catDay}
                alt=""
                style={{
                    position: 'absolute',
                    inset: 0,
                    width: '100%',
                    height: '100%',
                    objectFit: 'contain',
                    imageRendering: 'pixelated',
                    opacity: stage === 'day' ? 1 : 0,
                    transition: 'opacity 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
                    animation: 'cat-float 4s ease-in-out infinite',
                    filter: 'drop-shadow(0 4px 12px rgba(85,221,161,0.25))',
                }}
                draggable={false}
            />
            {/* Sunset cat */}
            <img
                src={catSunset}
                alt=""
                style={{
                    position: 'absolute',
                    inset: 0,
                    width: '100%',
                    height: '100%',
                    objectFit: 'contain',
                    imageRendering: 'pixelated',
                    opacity: stage === 'sunset' ? 1 : 0,
                    transition: 'opacity 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
                    animation: 'cat-float 4s ease-in-out infinite',
                    filter: 'drop-shadow(0 4px 12px rgba(251,146,60,0.25))',
                }}
                draggable={false}
            />
            {/* Night cat */}
            <img
                src={catNight}
                alt=""
                style={{
                    position: 'absolute',
                    inset: 0,
                    width: '100%',
                    height: '100%',
                    objectFit: 'contain',
                    imageRendering: 'pixelated',
                    opacity: stage === 'night' ? 1 : 0,
                    transition: 'opacity 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
                    animation: 'cat-float 4s ease-in-out infinite',
                    filter: 'drop-shadow(0 4px 12px rgba(93,143,175,0.25))',
                }}
                draggable={false}
            />

            <style>{`
                @keyframes cat-float {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-8px); }
                }
            `}</style>
        </div>
    )
}
