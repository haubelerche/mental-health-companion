import paperBoatImage from '../../../assets/scenes/thuyen.png'
import beachBackgroundImage from '../../../assets/scenes/beach-message-bg.png'

export function CinematicBg({ dark: _dark }: { dark: boolean }) {
    void _dark
    return (
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div
                className={`fixed inset-0 transition-all duration-500 brightness-80`}
                style={{
                    backgroundImage: `url(${beachBackgroundImage})`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                }}
            />
            <div
                className={`fixed bottom-0 left-0 right-0 h-2/5 transition-all duration-1000 bg-linear-to-b from-transparent via-slate-900/50 to-slate-950/80`}
            />
        </div>
    )
}

export function FloatingBottle({ dark, onClick, isClicked }: { dark: boolean; onClick: () => void; isClicked: boolean }) {
    const rippleColor = dark ? 'rgba(110,170,205,' : 'rgba(70,140,175,'

    return (
        <div onClick={onClick} className="relative flex flex-col items-center cursor-pointer select-none">
            <svg
                viewBox="0 0 340 70"
                className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-96 h-20 overflow-visible pointer-events-none z-0"
            >
                <ellipse
                    cx="170"
                    cy="38"
                    rx="90"
                    ry="12"
                    fill={dark ? 'rgba(0,0,0,0.30)' : 'rgba(0,0,0,0.15)'}
                    style={{ animation: 'bottleShadow 4.4s ease-in-out infinite', transformOrigin: '170px 38px' }}
                />
                {[{ rx: 82, ry: 14, d: '0s' }, { rx: 112, ry: 19, d: '0.9s' }, { rx: 144, ry: 24, d: '1.8s' }].map((r, i) => (
                    <ellipse
                        key={i}
                        cx="170"
                        cy="38"
                        rx={r.rx}
                        ry={r.ry}
                        fill="none"
                        stroke={`${rippleColor}${0.44 - i * 0.09})`}
                        strokeWidth={1.4 - i * 0.15}
                        style={{ animation: 'rippleExpand 3.6s ease-out infinite', animationDelay: r.d, transformOrigin: '170px 38px' }}
                    />
                ))}
            </svg>
            <div
                className="relative z-10 mb-7 transition-transform duration-350 ease-out"
                style={{
                    animation: isClicked ? 'none' : 'bottleFloat 4.4s ease-in-out infinite',
                    transform: isClicked ? 'scale(0.93) translateY(5px)' : 'scale(1) translateY(0)',
                }}
            >
                <img
                    src={paperBoatImage}
                    alt="Thuyền giấy"
                    className={`w-72 h-auto display block ${dark ? 'drop-shadow-2xl brightness-92 sepia-5' : 'drop-shadow-2xl brightness-102'}`}
                />
            </div>
        </div>
    )
}
