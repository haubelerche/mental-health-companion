import { useCallback, useEffect, useState } from 'react'
import { readAppSettings, APP_SETTINGS_UPDATED_EVENT, APP_SETTINGS_STORAGE_KEY, saveAppSettings } from '../utils/appSettings'

export type ThemeMode = 'light' | 'dark' | 'system'

const THEME_ATTRIBUTE = 'data-theme'

/**
 * Gets the effective theme based on stored preference and system fallback
 */
function getEffectiveTheme(mode: 'light' | 'dark' | 'system'): 'light' | 'dark' {
  if (mode === 'system') {
    if (typeof window === 'undefined') return 'light'
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return mode
}

/**
 * Applies theme attribute to document root and returns effective theme
 */
function applyTheme(mode: 'light' | 'dark' | 'system'): 'light' | 'dark' {
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
 * Hook to manage theme (light/dark/system) with appSettings synchronization
 */
export function useTheme() {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(() => {
    return readAppSettings().mode as ThemeMode
  })

  const [effectiveTheme, setEffectiveTheme] = useState<'light' | 'dark'>(() => {
    return getEffectiveTheme(readAppSettings().mode as ThemeMode)
  })

  // Sync with appSettings events
  useEffect(() => {
    const sync = () => {
      const mode = readAppSettings().mode as ThemeMode
      setThemeModeState(mode)
      const effective = applyTheme(mode)
      setEffectiveTheme(effective)
    }

    const handleSettingsUpdated = () => sync()
    const handleStorageUpdated = (event: StorageEvent) => {
      if (event.key === APP_SETTINGS_STORAGE_KEY) sync()
    }

    window.addEventListener(APP_SETTINGS_UPDATED_EVENT, handleSettingsUpdated)
    window.addEventListener('storage', handleStorageUpdated)
    
    // Initial apply
    sync()

    return () => {
      window.removeEventListener(APP_SETTINGS_UPDATED_EVENT, handleSettingsUpdated)
      window.removeEventListener('storage', handleStorageUpdated)
    }
  }, [])

  // Listen for system theme changes (if we ever support 'system' mode)
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
    if (mode === 'system') {
       // fallback to light if system is requested but not fully supported in appSettings yet
       mode = 'light'
    }
    const current = readAppSettings()
    saveAppSettings({ ...current, mode: mode as 'light' | 'dark' })
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
