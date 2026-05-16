import type { ReactNode } from 'react'
import Mascot, { type MascotVariant } from './Mascot'

type PixelEmptyStateProps = {
    mascot?: MascotVariant
    title: string
    description?: string
    action?: ReactNode
}

export function PixelEmptyState({
    mascot = 'main',
    title,
    description,
    action,
}: PixelEmptyStateProps) {
    return (
        <div className="flex min-h-48 flex-col items-center justify-center px-5 py-8 text-center">
            <Mascot
                variant={mascot}
                size="xl"
                alt="Serene mascot"
                className="mb-4 max-sm:h-20 max-sm:w-20"
            />
            <h2 className="font-display text-xl font-semibold text-theme-text-primary">{title}</h2>
            {description && (
                <p className="mt-2 max-w-md text-sm leading-relaxed text-theme-text-secondary">
                    {description}
                </p>
            )}
            {action && <div className="mt-5">{action}</div>}
        </div>
    )
}

export default PixelEmptyState
