import { X } from 'lucide-react'

export type PixelDialogueBoxProps = {
    speakerName: string
    portraitSrc: string
    text: string
    title?: string
    primaryLabel: string
    secondaryLabel?: string
    skipLabel?: string
    onPrimary?: () => void
    onSecondary?: () => void
    onSkip?: () => void
    onClose?: () => void
    className?: string
    pixelChat?: boolean
}

export default function PixelDialogueBox({
    speakerName,
    portraitSrc,
    text,
    title,
    primaryLabel,
    secondaryLabel,
    skipLabel = 'Bỏ qua',
    onPrimary,
    onSecondary,
    onSkip,
    onClose,
    className = '',
    pixelChat = false,
}: PixelDialogueBoxProps) {
    return (
        <section
            className={[
                'hau-tour-dialog-group pointer-events-auto relative isolate text-[#3d2b1b]',
                'font-sans',
                className,
            ].join(' ')}
            role="dialog"
            aria-live="polite"
        >
            <img
                src={portraitSrc}
                alt={speakerName}
                className="pixel-dialogue-portrait pointer-events-none absolute bottom-[calc(100%-34px)] right-10 z-30 h-36 w-36 object-contain sm:bottom-[calc(100%-42px)] sm:right-14 sm:h-44 sm:w-44"
                decoding="async"
                style={{ imageRendering: 'pixelated' }}
            />
            <div className="pixel-dialogue-nameplate relative z-20 ml-5 inline-flex border-[3px] border-[#5c3b24] bg-[#8a6040] px-7 py-2 text-lg font-black text-[#fff6d5] shadow-[4px_4px_0_rgba(55,38,20,0.32)]">
                {speakerName}
            </div>
            <div
                className={[
                    'pixel-dialogue-box relative z-10 -mt-1 max-h-[min(58vh,440px)] overflow-auto border-4 bg-[#f8e7b8] p-5 shadow-[0_7px_0_rgba(55,38,20,0.35)]',
                    pixelChat ? 'border-[#1a1008] bg-[#fff4dc]' : 'border-[#6b4b2a]',
                ].join(' ')}
            >
                {onClose ? (
                    <button
                        type="button"
                        onClick={onClose}
                        className="absolute right-3 top-3 inline-flex h-9 w-9 items-center justify-center border-2 border-[#6b4b2a] bg-[#fff6d5] text-[#5c3b24] shadow-[2px_2px_0_rgba(55,38,20,0.25)] transition hover:translate-y-0.5 hover:shadow-none"
                        aria-label="Đóng hướng dẫn"
                    >
                        <X className="h-4 w-4" />
                    </button>
                ) : null}
                {title ? <h2 className={onClose ? 'pr-12 text-xl font-black leading-snug' : 'text-xl font-black leading-snug'}>{title}</h2> : null}
                <p className="mt-3 max-w-3xl text-base font-semibold leading-relaxed text-[#5f5140]">{text}</p>
                {(onSkip || (secondaryLabel && onSecondary) || onPrimary) ? (
                    <div className="mt-5 flex flex-wrap items-center justify-end gap-3">
                        {onSkip ? (
                            <button
                                type="button"
                                onClick={onSkip}
                                className="border-2 border-[#7c5936] bg-[#fff6d5] px-5 py-2 text-sm font-black text-[#6b4b2a] shadow-[3px_3px_0_rgba(55,38,20,0.24)] transition hover:translate-y-0.5 hover:shadow-none"
                            >
                                {skipLabel}
                            </button>
                        ) : null}
                        {secondaryLabel && onSecondary ? (
                            <button
                                type="button"
                                onClick={onSecondary}
                                className="border-2 border-[#7c5936] bg-[#fff6d5] px-5 py-2 text-sm font-black text-[#6b4b2a] shadow-[3px_3px_0_rgba(55,38,20,0.24)] transition hover:translate-y-0.5 hover:shadow-none"
                            >
                                {secondaryLabel}
                            </button>
                        ) : null}
                        {onPrimary ? (
                            <button
                                type="button"
                                onClick={onPrimary}
                                className="border-2 border-[#4f3320] bg-[#8a6040] px-6 py-2 text-sm font-black text-[#fff6d5] shadow-[3px_3px_0_rgba(55,38,20,0.35)] transition hover:translate-y-0.5 hover:shadow-none"
                            >
                                {primaryLabel}
                            </button>
                        ) : null}
                    </div>
                ) : null}
            </div>
        </section>
    )
}
