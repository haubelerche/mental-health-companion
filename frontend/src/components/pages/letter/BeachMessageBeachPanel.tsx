import { getUi } from './shared'
import { FloatingBottle } from './BeachMessageScene'

export function BeachMessageBeachPanel({
    dark,
    loadingInbox,
    hasBottle,
    ripple,
    onBottleClick,
    onWrite,
}: {
    dark: boolean
    loadingInbox: boolean
    hasBottle: boolean
    ripple: boolean
    onBottleClick: () => void
    onWrite: () => void
}) {
    const ui = getUi(dark)

    return (
        <div className="relative z-10 flex flex-col items-center min-h-[calc(100vh-64px)] pt-20 pb-24">
            <div className="text-center mb-16" style={{ animation: 'fadeUp 1s ease 0.1s both' }}>
                <h1
                    className={`${ui.textPrimary} font-display text-5xl italic font-normal leading-snug drop-shadow-xl`}
                    style={{ textShadow: dark ? '0 2px 18px rgba(0,0,0,0.45)' : '0 2px 12px rgba(255,255,255,0.38)' }}
                >
                    {loadingInbox ? 'Đang đón thư từ biển...' : hasBottle ? 'Có một lá thư đang chờ bạn' : 'Chưa có thư mới'}
                </h1>
            </div>

            {loadingInbox ? (
                <div className="text-center" style={{ animation: 'fadeUp 1s ease 0.3s both' }}>
                    <p className={`${ui.textPrimary} font-display text-2xl italic font-normal leading-relaxed`}>Đang lắng nghe biển khơi...</p>
                </div>
            ) : hasBottle ? (
                <div className="flex flex-col items-center gap-6" style={{ animation: 'fadeUp 1s ease 0.3s both' }}>
                    <FloatingBottle dark={dark} onClick={onBottleClick} isClicked={ripple} />
                    <p className="text-theme-primary text-shadow-2xl font-display font-semibold tracking-widest uppercase mt-2 animate-pulse">Chạm để xem</p>
                </div>
            ) : (
                <div className="text-center" style={{ animation: 'fadeUp 1s ease 0.3s both' }}>
                    <p className={`${ui.textPrimary} font-display text-2xl italic font-normal leading-relaxed`} style={{ opacity: dark ? 0.78 : 0.88 }}>
                        Biển đang lặng, chưa có thư trôi đến.
                    </p>
                </div>
            )}

            <div className="flex flex-col items-center gap-4 mt-16" style={{ animation: 'fadeUp 1s ease 0.5s both' }}>
                <button
                    type="button"
                    onClick={onWrite}
                    className={`
            border rounded-full px-10 py-3 font-display text-2xl font-semibold cursor-pointer transition-all
            ${dark
                            ? 'bg-white/10 border-white/45 text-white/95 shadow-[0_10px_24px_rgba(0,0,0,0.28)]'
                            : 'bg-white/80 border-slate-900/30 text-slate-900/90 shadow-[0_8px_20px_rgba(20,40,56,0.18)]'
                        }
            hover:bg-cyan-400/25 hover:border-cyan-400/85 hover:text-white hover:shadow-[0_12px_28px_rgba(66,153,180,0.42)] hover:-translate-y-px
          `}
                >
                    Viết lá thư của bạn
                </button>
            </div>
        </div>
    )
}
