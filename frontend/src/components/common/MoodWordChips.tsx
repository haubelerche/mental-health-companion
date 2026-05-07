import { useThemeContext } from '../../contexts/ThemeContext'
type Props = {
    words?: string[]
    selected: string[]
    onChange: (selected: string[]) => void
    className?: string
}

const DEFAULT_WORDS = [
    'Bình yên', 'Hứng khởi', 'Biết ơn', 'Tự tin',
    'Mệt mỏi', 'Lo âu', 'Buồn rầu', 'Căng thẳng',
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
                            ? 'bg-theme-accent text-white'
                            : 'text-theme-text-secondary border border-theme-border',
                    ].join(' ')}
                >
                    {word}
                </button>
            ))}
        </div>
    )
}
