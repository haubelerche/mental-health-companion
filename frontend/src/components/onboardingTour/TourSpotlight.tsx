type Props = {
    rect: DOMRect | null
}

export default function TourSpotlight({ rect }: Props) {
    if (!rect) return null

    const pad = 8
    const top = Math.max(8, rect.top - pad)
    const left = Math.max(8, rect.left - pad)
    const width = Math.min(window.innerWidth - left - 8, rect.width + pad * 2)
    const height = Math.min(window.innerHeight - top - 8, rect.height + pad * 2)

    return (
        <div className="pointer-events-none fixed inset-0 z-[9999]">
            <div
                className="absolute rounded-2xl border-[3px] border-sky-400/95 bg-transparent shadow-[0_0_0_2px_rgba(255,255,255,0.75),0_0_26px_rgba(14,165,233,0.55)]"
                style={{ top, left, width, height }}
            />
        </div>
    )
}
