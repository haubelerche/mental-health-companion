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
                    className={`flex items-center gap-2 self-start rounded-3xl border border-theme-border/30 bg-theme-bg-secondary/90 px-5 py-3 backdrop-blur-sm ${className ?? ''}`}
                >
                    {[0, 1, 2].map((i) => (
                        <motion.span
                            key={i}
                            className="h-2.5 w-2.5 rounded-full bg-theme-text-secondary/55"
                            animate={{ y: [0, -2, 0], opacity: [0.4, 1, 0.4] }}
                            transition={{
                                duration: 0.9,
                                repeat: Infinity,
                                delay: i * 0.16,
                                ease: 'easeInOut',
                            }}
                        />
                    ))}
                </motion.div>
            )}
        </AnimatePresence>
    )
}
