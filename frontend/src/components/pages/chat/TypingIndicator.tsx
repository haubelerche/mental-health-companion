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
                    className={`flex items-center gap-2 self-start border border-[#6e5437]/60 bg-[#fff4dc]/95 px-4 py-3 shadow-[4px_4px_0_rgba(0,0,0,0.22)] ${className ?? ''}`}
                >
                    {[0, 1, 2].map((i) => (
                        <motion.span
                            key={i}
                            className="h-2 w-2 rounded-full bg-[#486354]"
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
