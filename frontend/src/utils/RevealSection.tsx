import type { ReactNode } from 'react'
import { motion } from 'framer-motion'

type RevealSectionProps = {
    id?: string
    className?: string
    delay?: number
    children: ReactNode
}

export default function RevealSection({ id, className = '', delay = 0, children }: RevealSectionProps) {
    return (
        <motion.section
            id={id}
            className={className}
            initial={{ opacity: 0, y: 48 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.5, delay, ease: 'easeOut' }}
        >
            {children}
        </motion.section>
    )
}
