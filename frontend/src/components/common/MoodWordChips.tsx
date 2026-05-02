import { useEffect, useState } from 'react'
import { useThemeContext } from '../../contexts/ThemeContext'
type Props = {
    words?: string[]
    selected: string[]
    onChange: (selected: string[]) => void
    className?: string
}

const DEFAULT_WORDS = [
    'Bình yên', 'Hứng khởi', 'Biết ơn', 'Tự tin',
    'Mệt mỏi', 'Lo âu', 'Buồn', 'Căng thẳng',
    'Vui vẻ', 'Trống rỗng', 'Cô đơn', 'Bối rối',
]

export function MoodWordChips({ words = DEFAULT_WORDS, selected, onChange, className }: Props) {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const toggle = (word: string) => {
        onChange(
            selected.includes(word)
                ? selected.filter((w) => w !== word)
                : [...selected, word],
        )
    }

    return (
        <div className={`flex flex-wrap gap-2 ${className ?? ''}`}>
            {words.map((word) => (
                <button
                    key={word}
                    type="button"
                    onClick={() => toggle(word)}
                    className={[
                        'rounded-full px-4 py-2 text-sm font-medium transition-all active:scale-95 cursor-pointer',
                        selected.includes(word)
                            ? (isDark ? 'bg-theme-bgprimary text-white shadow-sm' : 'bg-serene-primary text-serene-on-primary shadow-sm')
                            : `${isDark ? 'border-white/10 bg-white/15 hover:bg-white/10 text-white/70' : 'border border-gray-300 bg-white/70 hover:bg-serene-on-primary text-serene-ink'}`,
                    ].join(' ')}
                >
                    {word}
                </button>
            ))}
        </div>
    )
}
