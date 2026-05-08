import { motion, AnimatePresence } from 'framer-motion'

type Props = {
    visible: boolean
    className?: string
}

export function TypingIndicator({ visible, className }: Props) {
    return (
        <AnimatePresence>
            {visible && (
                <motion.div
                    initial={{ opacity: 0, y: 8, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 4, scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                    className={`flex items-center gap-2 self-start rounded-3xl border border-theme-secondary/20 bg-theme-surface px-5 py-3 ${className ?? ''}`}
                >
                    {[0, 1, 2].map((i) => (
                        <motion.span
                            key={i}
                            className="h-2 w-2 rounded-full bg-theme-accent"
                            animate={{ y: [0, -6, 0] }}
                            transition={{
                                duration: 0.6,
                                repeat: Infinity,
                                delay: i * 0.12,
                                ease: 'easeInOut',
                            }}
                        />
                    ))}
                </motion.div>
            )}
        </AnimatePresence>
    )
}
