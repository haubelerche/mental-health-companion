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
                    className={`flex items-center gap-1.5 self-start rounded-2xl rounded-bl-sm border border-white/45 bg-white/70 px-4 py-3 backdrop-blur-sm ${className ?? ''}`}
                >
                    {[0, 1, 2].map((i) => (
                        <motion.span
                            key={i}
                            className="h-2 w-2 rounded-full bg-serene-muted/60"
                            animate={{ y: [0, -5, 0] }}
                            transition={{
                                duration: 0.75,
                                repeat: Infinity,
                                delay: i * 0.14,
                                ease: 'easeInOut',
                            }}
                        />
                    ))}
                </motion.div>
            )}
        </AnimatePresence>
    )
}
