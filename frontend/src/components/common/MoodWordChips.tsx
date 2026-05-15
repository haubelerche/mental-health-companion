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
    'Khác',
]

export function MoodWordChips({ words = DEFAULT_WORDS, selected, onChange, className }: Props) {
    const toggle = (word: string) => {
        onChange(
            selected.includes(word)
                ? selected.filter((w) => w !== word)
                : [...selected, word],
        )
    }

    return (
        <div className={`flex shrink-0 overflow-x-auto scrollbar-hide  gap-2 ${className ?? ''}`}>
            {words.map((word) => (
                <button
                    key={word}
                    type="button"
                    onClick={() => toggle(word)}
                    className={[
                        'rounded-full px-4 py-2 text-xs font-medium cursor-pointer hover:underline',
                        selected.includes(word)
                            ? 'bg-theme-accent text-white'
                            : 'text-theme-text-primary border border-theme-border bg-theme-surface',
                    ].join(' ')}
                >
                    {word}
                </button>
            ))}
        </div>
    )
}
