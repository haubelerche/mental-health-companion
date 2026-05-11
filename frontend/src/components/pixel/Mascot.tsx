import { pixelAssets } from '../../assets/pixel-sanctuary'

export type MascotVariant =
    | 'main'
    | 'idle'
    | 'quiet'
    | 'eat'
    | 'sunflower'
    | 'rock'
    | 'bucket'

export type MascotSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

type MascotProps = {
    variant?: MascotVariant
    size?: MascotSize
    alt?: string
    decorative?: boolean
    className?: string
}

const VARIANT_SRC: Record<MascotVariant, string> = {
    main: pixelAssets.mascotMain,
    idle: pixelAssets.mascotIdle,
    quiet: pixelAssets.mascotQuiet,
    eat: pixelAssets.mascotEat,
    sunflower: pixelAssets.mascotSunflower,
    rock: pixelAssets.mascotRock,
    bucket: pixelAssets.mascotBucket,
}

const SIZE_CLASS: Record<MascotSize, string> = {
    xs: 'h-[60px] w-[60px]',
    sm: 'h-[63px] w-[63px]',
    md: 'h-[79px] w-[79px]',
    lg: 'h-[111px] w-[111px]',
    xl: 'h-[143px] w-[143px]',
}

export function Mascot({
    variant = 'main',
    size = 'md',
    alt,
    decorative = false,
    className = '',
}: MascotProps) {
    return (
        <img
            src={VARIANT_SRC[variant]}
            alt={decorative ? '' : alt ?? 'Serene mascot'}
            aria-hidden={decorative ? true : undefined}
            loading="lazy"
            decoding="async"
            className={[
                'pixel-mascot shrink-0 object-contain',
                SIZE_CLASS[size],
                className,
            ].filter(Boolean).join(' ')}
        />
    )
}

export default Mascot
