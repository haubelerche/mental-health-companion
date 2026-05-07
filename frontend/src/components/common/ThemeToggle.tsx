import { Moon, Sun } from 'lucide-react'
import { useThemeContext } from '../../contexts/ThemeContext'

export function ThemeToggle() {
  const { effectiveTheme, toggleTheme } = useThemeContext()

  return (
    <button
      onClick={toggleTheme}
      aria-label={`Switch to ${effectiveTheme === 'dark' ? 'light' : 'dark'} theme`}
      className="group inline-flex h-10 w-10 items-center justify-center rounded-full transition-all"
    >
      {effectiveTheme === 'dark' ? (
        <Sun className="h-5 w-5 transition-transform group-hover:rotate-180" />
      ) : (
        <Moon className="h-5 w-5 transition-transform group-hover:rotate-180" />
      )}
    </button>
  )
}
