/** @type {import('tailwindcss').Config} */
export default {
  // Use class-based dark mode, relying on [data-theme="dark"] attribute
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        // Theme-aware semantic colors using CSS variables
        'theme-bg-primary': 'var(--theme-bg-primary)',
        'theme-bg-secondary': 'var(--theme-bg-secondary)',
        'theme-surface': 'var(--theme-surface)',
        'theme-surface-alt': 'var(--theme-surface-alt)',
        'theme-text-primary': 'var(--theme-text-primary)',
        'theme-text-secondary': 'var(--theme-text-secondary)',
        'theme-text-tertiary': 'var(--theme-text-tertiary)',
        'theme-border': 'var(--theme-border)',
        'theme-accent': 'var(--theme-accent)',
        'theme-accent-dim': 'var(--theme-accent-dim)',
        'theme-accent-light': 'var(--theme-accent-light)',
      },
    },
  },
  plugins: [],
}
