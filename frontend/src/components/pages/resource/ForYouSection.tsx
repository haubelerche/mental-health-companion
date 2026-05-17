import { Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'
import { type ResourceItem } from '../../../services/resourceService'
import { ResourceGrid } from './ResourceGrid'

interface ForYouSectionProps {
    items: ResourceItem[]
    reason: string
    onOpen: (item: ResourceItem) => void
}

export function ForYouSection({ items, reason, onOpen }: ForYouSectionProps) {
    if (items.length === 0) {
        return null
    }

    return (
        <motion.section
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="mb-8 rounded-3xl border border-serene-primary/15 bg-theme-surface/70 p-4 shadow-sm sm:p-5"
        >
            <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
                <div>
                    <div className="flex items-center gap-2">
                        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-serene-primary/10 text-serene-primary">
                            <Sparkles className="h-4 w-4" />
                        </span>
                        <h2 className="font-display text-2xl font-semibold text-theme-text-secondary">
                            Dành cho bạn hôm nay
                        </h2>
                    </div>
                    <p className="mt-1 text-sm text-theme-text-primary/70">{reason}</p>
                </div>
            </div>
            <ResourceGrid items={items.slice(0, 3)} onOpen={onOpen} compact />
        </motion.section>
    )
}
