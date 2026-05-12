import { createPortal } from 'react-dom'
import { useEffect, type CSSProperties } from 'react'
import hauLuongPortrait from '../../assets/assistants/hau-luong.png'
import { useOnboardingTour } from './useOnboardingTour'

const GUIDE_CHARACTER_NAME = 'Hau Luong'

const popupStyle: CSSProperties = {
    position: 'fixed',
    right: '24px',
    bottom: '32px',
    width: 'min(400px, calc(100vw - 24px))',
    zIndex: 10000,
}

export default function SereneGuideOverlay() {
    const {
        loading,
        state,
        currentStep,
        activeIndex,
        shouldRender,
        farewellVisible,
        primary,
        skip,
    } = useOnboardingTour()

    const isVisible = Boolean(!loading && state && currentStep && (shouldRender || farewellVisible))

    useEffect(() => {
        if (!isVisible) return
        document.body.dataset.personaSpeakerLock = 'hau_luong'
        return () => {
            if (document.body.dataset.personaSpeakerLock === 'hau_luong') {
                delete document.body.dataset.personaSpeakerLock
            }
        }
    }, [isVisible])

    if (!isVisible || !state || !currentStep) return null

    const total = state.steps.length
    const title = farewellVisible ? 'Hẹn gặp lại' : currentStep.title
    const body = farewellVisible ? 'Chúc bạn có trải nghiệm vui vẻ với SereneAI.' : currentStep.body

    const overlay = (
        <div className="pointer-events-none fixed inset-0 z-[9999]">
            <aside className="pointer-events-auto pt-32 text-[#3d2b1b]" style={popupStyle}>
                <img
                    src={hauLuongPortrait}
                    alt={GUIDE_CHARACTER_NAME}
                    className="pointer-events-none absolute right-4 top-0 h-40 w-40 translate-y-5 object-contain"
                    decoding="async"
                    style={{ imageRendering: 'pixelated' }}
                />
                <div className="relative">
                    <div className="relative z-20 ml-3 inline-flex border-[4px] border-[#5c3b24] bg-[#8a6040] px-6 py-2.5 text-lg font-black text-[#fff6d5] shadow-[4px_4px_0_rgba(55,38,20,0.28)]">
                        {GUIDE_CHARACTER_NAME}
                    </div>
                    <div className="relative z-10 -mt-1 border-4 border-[#6b4b2a] bg-[#f8e7b8] p-6 shadow-[0_7px_0_rgba(55,38,20,0.35)]">
                        <h2 className="pr-2 text-lg font-black leading-snug">{title}</h2>
                        <p className="mt-3 text-[15px] font-bold leading-relaxed text-[#5f5140]">{body}</p>
                        {!farewellVisible ? (
                            <div className="mt-5 flex flex-wrap items-center justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() => void skip()}
                                    className="border-2 border-[#7c5936] bg-[#fff6d5] px-5 py-2 text-sm font-black text-[#6b4b2a] shadow-[3px_3px_0_rgba(55,38,20,0.24)] transition hover:translate-y-0.5 hover:shadow-none"
                                >
                                    Bỏ qua
                                </button>
                                <button
                                    type="button"
                                    onClick={() => void primary()}
                                    className="border-2 border-[#4f3320] bg-[#8a6040] px-6 py-2 text-sm font-black text-[#fff6d5] shadow-[3px_3px_0_rgba(55,38,20,0.35)] transition hover:translate-y-0.5 hover:shadow-none"
                                >
                                    Tiếp theo
                                </button>
                            </div>
                        ) : null}
                    </div>
                </div>
            </aside>
            <span className="sr-only">Bước {activeIndex + 1} trên {total}</span>
        </div>
    )

    return createPortal(overlay, document.body)
}
