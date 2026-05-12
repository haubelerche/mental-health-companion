import { motion, useReducedMotion } from 'framer-motion'

interface BackgroundLayerProps {
  src: string
  mode: 'light' | 'dark'
}

export default function BackgroundLayer({ src, mode }: BackgroundLayerProps) {
  const reduceMotion = useReducedMotion()
  const overlayClass = mode === 'dark'
    ? 'bg-gradient-to-br from-[#10231F]/78 via-[#0A1410]/50 to-transparent'
    : 'bg-gradient-to-br from-[#10231F]/70 via-[#10231F]/35 to-[#F4E8C8]/10'

  return (
    <div className="pointer-events-none fixed inset-0 z-0">
      <img src={src} alt="" aria-hidden className="h-full w-full object-cover" />
      <div className={`absolute inset-0 ${overlayClass}`} />
      <div className={`absolute inset-0 ${mode === 'dark' ? 'bg-black/10' : 'bg-black/5'}`} />

      {!reduceMotion && (
        <>
          <motion.div
            aria-hidden
            className="absolute left-[12%] top-[14%] hidden h-10 w-10 rounded-full border border-white/20 bg-white/10 backdrop-blur-sm md:block"
            animate={{ y: [0, -10, 0], opacity: [0.45, 0.7, 0.45] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
          />
          <motion.div
            aria-hidden
            className="absolute right-[16%] top-[22%] hidden h-8 w-8 rounded-full border border-white/20 bg-white/10 backdrop-blur-sm md:block"
            animate={{ y: [0, 8, 0], x: [0, -4, 0], opacity: [0.35, 0.6, 0.35] }}
            transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
          />
          <motion.div
            aria-hidden
            className="absolute bottom-[18%] left-[18%] hidden h-6 w-6 rounded-full border border-white/20 bg-white/10 backdrop-blur-sm lg:block"
            animate={{ y: [0, -8, 0], opacity: [0.25, 0.5, 0.25] }}
            transition={{ duration: 5.5, repeat: Infinity, ease: 'easeInOut' }}
          />
        </>
      )}
    </div>
  )
}
