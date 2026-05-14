import { ArrowLeft, Sparkles, Wind, Focus, Accessibility } from 'lucide-react'
import { useThemeContext } from '../../../contexts/ThemeContext'
import { motion } from 'framer-motion'

interface ExerciseHeroProps {
  onBack: () => void
  title: string
  subtitle: string
}

export default function ExerciseHero({ onBack, title, subtitle }: ExerciseHeroProps) {
  const { effectiveTheme } = useThemeContext()
  const isDark = effectiveTheme === 'dark'

  return (
    <section className={`pixel-card relative overflow-hidden p-8 sm:p-12 lg:p-16 bg-theme-surface border-2`} style={{ borderRadius: '4px' }}>
      <div className="relative z-10 flex flex-col items-center text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="pixel-label mb-6 inline-flex items-center gap-2 border-2 px-4 py-1.5 text-[14px] font-bold tracking-[0.2em] bg-theme-bg-secondary"
          style={{ borderColor: 'var(--mint)', color: 'var(--mint)', borderRadius: '2px' }}
        >
          <Sparkles className="h-4 w-4" />
          Góc thư thái
        </motion.div>
        
        <motion.h1 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="pixel-headline max-w-4xl text-center"
          style={{ fontSize: 'clamp(2.5rem, 5vw, 4rem)' }}
        >
          {title}
        </motion.h1>
        
        <motion.p 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="vn-body mt-6 max-w-2xl text-base leading-relaxed sm:text-lg opacity-90"
        >
          {subtitle}
        </motion.p>

        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-10 flex flex-wrap justify-center gap-4"
        >
          <button
            type="button"
            onClick={onBack}
            className="pixel-btn-outline inline-flex h-10 items-center gap-2 px-6 text-sm font-bold transition-all hover:scale-105 active:scale-95"
            style={{ borderRadius: '4px', border: '2px solid var(--mint)', color: 'var(--mint)', background: 'transparent' }}
          >
            <ArrowLeft className="h-4 w-4" />
            Quay lại
          </button>
        </motion.div>
      </div>

      {/* Decorative elements */}
      <div className="absolute -left-10 -top-10 h-40 w-40 rounded-full bg-[#5F7F68]/10 blur-3xl opacity-50" />
      <div className="absolute -right-10 -bottom-10 h-40 w-40 rounded-full bg-[#D4AF7A]/10 blur-3xl opacity-50" />
    </section>
  )
}

