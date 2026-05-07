import type { ReactNode } from 'react'
import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'

type VariantType = 'fade-up' | 'fade-left' | 'fade-right' | 'zoom'

const variantsMap = {
    'fade-up': {
        hidden: { opacity: 0, y: 24 },
        visible: { opacity: 1, y: 0 },
    },
    'fade-left': {
        hidden: { opacity: 0, x: -24 },
        visible: { opacity: 1, x: 0 },
    },
    'fade-right': {
        hidden: { opacity: 0, x: 24 },
        visible: { opacity: 1, x: 0 },
    },
    zoom: {
        hidden: { opacity: 0, scale: 0.96 },
        visible: { opacity: 1, scale: 1 },
    },
}

export default function RevealSection({
    id,
    className = '',
    delay = 0,
    variant = 'fade-up',
    children,
}: {
    id?: string
    className?: string
    delay?: number
    variant?: VariantType
    children: ReactNode
}) {
    const ref = useRef(null)

    const isInView = useInView(ref, {
        once: true,
        amount: 0.3,
    })

    const selected = variantsMap[variant]

    return (
        <motion.section
            ref={ref}
            id={id}
            className={className}
            initial={selected.hidden}
            animate={isInView ? selected.visible : undefined}
            transition={{
                duration: 0.6,
                delay,
                ease: 'easeOut',
            }}
            style={{ willChange: 'transform, opacity' }}
        >
            {children}
        </motion.section>
    )
}