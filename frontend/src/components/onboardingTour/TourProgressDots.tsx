type Props = {
    total: number
    activeIndex: number
}

export default function TourProgressDots({ total, activeIndex }: Props) {
    return (
        <div className="flex items-center gap-1.5" aria-label={`Bước ${activeIndex + 1} trên ${total}`}>
            {Array.from({ length: total }).map((_, index) => (
                <span
                    key={index}
                    className={[
                        'h-1.5 rounded-full transition-all',
                        index === activeIndex ? 'w-6 bg-serene-primary' : 'w-1.5 bg-serene-primary/25',
                    ].join(' ')}
                />
            ))}
        </div>
    )
}
