import type { ReactNode } from 'react'
import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'

type RevealSectionProps = {
    id?: string
    className?: string
    delay?: number
    children: ReactNode
}

export default function RevealSection({
    id,
    className = '',
    delay = 0,
    children,
}: RevealSectionProps) {
    const ref = useRef(null)
    const isInView = useInView(ref, {
        amount: 0.25,
        margin: '0px 0px -10% 0px',
    })

    return (
        <motion.section
            ref={ref}
            id={id}
            className={className}
            initial={{ opacity: 0, y: 32 }}
            animate={
                isInView
                    ? { opacity: 1, y: 0 }
                    : { opacity: 0, y: 32 }
            }
            transition={{
                duration: 0.5,
                delay,
                ease: 'easeInOut',
            }}
        >
            {children}
        </motion.section>
    )
}