import { useCallback, useEffect, useState } from 'react'

export type ThemeMode = 'light' | 'dark' | 'system'

const THEME_STORAGE_KEY = 'serene:theme-mode'
const THEME_ATTRIBUTE = 'data-theme'

/**
 * Gets the effective theme based on stored preference and system fallback
 */
function getEffectiveTheme(stored: ThemeMode): 'light' | 'dark' {
  if (stored === 'system') {
    if (typeof window === 'undefined') return 'light'
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return stored
}

/**
 * Applies theme attribute to document root and returns effective theme
 */
function applyTheme(mode: ThemeMode): 'light' | 'dark' {
  if (typeof document === 'undefined') return 'light'
  
  const effectiveTheme = getEffectiveTheme(mode)
  if (effectiveTheme === 'dark') {
    document.documentElement.setAttribute(THEME_ATTRIBUTE, 'dark')
  } else {
    document.documentElement.removeAttribute(THEME_ATTRIBUTE)
  }
  return effectiveTheme
}

/**
 * Hook to manage theme (light/dark/system) with localStorage persistence and system fallback
 */
export function useTheme() {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(() => {
    if (typeof window === 'undefined') return 'system'
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY) as ThemeMode | null
    return (stored && ['light', 'dark', 'system'].includes(stored)) ? stored : 'system'
  })

  const [effectiveTheme, setEffectiveTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window === 'undefined') return 'light'
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY) as ThemeMode | null
    const mode = (stored && ['light', 'dark', 'system'].includes(stored)) ? stored : 'system'
    return getEffectiveTheme(mode)
  })

  // Apply theme on mount and when themeMode changes
  useEffect(() => {
    const effective = applyTheme(themeMode)
    setEffectiveTheme(effective)
  }, [themeMode])

  // Listen for system theme changes (only relevant when mode === 'system')
  useEffect(() => {
    if (themeMode !== 'system') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      const effective = applyTheme(themeMode)
      setEffectiveTheme(effective)
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [themeMode])

  const setTheme = useCallback((mode: ThemeMode) => {
    setThemeModeState(mode)
    window.localStorage.setItem(THEME_STORAGE_KEY, mode)
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme(effectiveTheme === 'dark' ? 'light' : 'dark')
  }, [effectiveTheme, setTheme])

  return {
    themeMode,
    effectiveTheme,
    setTheme,
    toggleTheme,
  }
}
