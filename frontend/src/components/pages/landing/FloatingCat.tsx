import { useEffect, useState } from 'react'
import catDay from '../../../assets/motion/cat-soul-2.gif'
import catNight from '../../../assets/motion/cat-soul.gif'

/**
 * FloatingCat — fixed bottom-right corner.
 * Cross-fades day cat → night cat at 40% scroll depth.
 */
export default function FloatingCat() {
    const [isNight, setIsNight] = useState(false)

    useEffect(() => {
        const updateTheme = () => {
            const scrollY = window.scrollY
            const docHeight = document.documentElement.scrollHeight - window.innerHeight
            if (docHeight <= 0) return
            setIsNight(scrollY / docHeight > 0.4)
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
                    opacity: isNight ? 0 : 1,
                    transition: 'opacity 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
                    animation: 'cat-float 4s ease-in-out infinite',
                    filter: 'drop-shadow(0 4px 12px rgba(85,221,161,0.25))',
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
                    opacity: isNight ? 1 : 0,
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
