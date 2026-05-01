import type { TabId } from './shared'

export function BeachMessageTabs({
    tab,
    dark,
    onChange,
}: {
    tab: TabId
    dark: boolean
    onChange: (tab: TabId) => void
}) {
    return (
        <nav className="relative z-10 flex items-center justify-center px-8 py-4.5 border-b border-stone-950/18 backdrop-blur-md">
            <div className="flex gap-24">
                {[
                    { id: 'beach', label: 'Bến thư' },
                    { id: 'community', label: 'Kho thư' },
                ].map((item) => (
                    <button
                        type="button"
                        key={item.id}
                        onClick={() => onChange(item.id as TabId)}
                        style={{
                            background: 'none',
                            border: 'none',
                            borderBottom: `2px solid ${tab === item.id ? (dark ? 'rgb(255,255,255)' : 'rgb(15,23,42)') : dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.45)'}`,
                            color: tab === item.id ? (dark ? 'rgb(255,255,255)' : 'rgb(15,23,42)') : dark ? 'rgba(242,235,224,0.45)' : 'rgba(20,26,33,0.45)',
                            marginBottom: '-1px',
                        }}
                        className="py-1.5 px-4 text-lg font-display font-semibold tracking-wide cursor-pointer transition-all"
                    >
                        {item.label}
                    </button>
                ))}
            </div>
        </nav>
    )
}
