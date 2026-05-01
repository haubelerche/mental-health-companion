import type { ReactNode } from 'react'
import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'

type VariantType =
    | 'fade-up'
    | 'fade-left'
    | 'fade-right'
    | 'zoom'
    | 'blur'
    | 'soft'

type RevealSectionProps = {
    id?: string
    className?: string
    delay?: number
    variant?: VariantType
    children: ReactNode
}

const variantsMap = {
    'fade-up': {
        hidden: { opacity: 0, y: 32 },
        visible: { opacity: 1, y: 0 },
    },
    'fade-left': {
        hidden: { opacity: 0, x: -40 },
        visible: { opacity: 1, x: 0 },
    },
    'fade-right': {
        hidden: { opacity: 0, x: 40 },
        visible: { opacity: 1, x: 0 },
    },
    zoom: {
        hidden: { opacity: 0, scale: 0.94 },
        visible: { opacity: 1, scale: 1 },
    },
    blur: {
        hidden: { opacity: 0, filter: 'blur(8px)' },
        visible: { opacity: 1, filter: 'blur(0px)' },
    },
    soft: {
        hidden: { opacity: 0, y: 24, scale: 0.98 },
        visible: { opacity: 1, y: 0, scale: 1 },
    },
}

export default function RevealSection({
    id,
    className = '',
    delay = 0,
    variant = 'fade-up',
    children,
}: RevealSectionProps) {
    const ref = useRef(null)
    const isInView = useInView(ref, { amount: 0.25 })

    const selected = variantsMap[variant]

    return (
        <motion.section
            ref={ref}
            id={id}
            className={className}
            initial={selected.hidden}
            animate={isInView ? selected.visible : selected.hidden}
            transition={{
                duration: 0.65,
                delay,
                ease: 'easeInOut',
            }}
        >
            {children}
        </motion.section>
    )
}