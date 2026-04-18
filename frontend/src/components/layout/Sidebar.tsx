import type { ReactNode } from 'react'

type NavItem = {
    icon: ReactNode
    label: string
    active?: boolean
}

type SidebarProps = {
    navItems: NavItem[]
    isOpen: boolean
}

export default function Sidebar({ navItems, isOpen }: SidebarProps) {
    return (
        <>
            <aside
                className={[
                    'fixed left-0 top-0 z-40 hidden h-full w-72 flex-col rounded-r-[32px] border-r border-white/35 bg-white/55 p-8 backdrop-blur-3xl transition-transform duration-300 lg:flex',
                    isOpen ? 'translate-x-0' : '-translate-x-[110%]',
                ].join(' ')}
            >
                <div className="mb-10">
                    <h1 className="font-display text-5xl italic text-serene-ink">Serene</h1>
                    <p className="mt-2 text-[11px] uppercase tracking-[0.28em] text-serene-muted/85">
                        Digital Sanctuary
                    </p>
                </div>

                <nav className="flex flex-1 flex-col gap-3">
                    {navItems.map((item) => (
                        <button
                            key={item.label}
                            type="button"
                            className={[
                                'flex items-center gap-3 rounded-2xl px-3 py-3 text-left transition',
                                item.active
                                    ? 'border-l-4 border-serene-primary bg-white/70 text-serene-primary shadow-sm'
                                    : 'text-serene-muted hover:bg-white/60 hover:text-serene-ink',
                            ].join(' ')}
                        >
                            {item.icon}
                            <span className="font-display text-xl">{item.label}</span>
                        </button>
                    ))}
                </nav>

                <button
                    type="button"
                    className="mt-8 rounded-2xl bg-serene-primary py-4 font-display text-xl italic text-serene-on-primary shadow-[0_14px_34px_rgba(47,52,46,0.24)] transition hover:brightness-105"
                >
                    Breathe Now
                </button>
            </aside>

            {isOpen && (
                <nav className="fixed bottom-4 left-1/2 z-50 flex w-[min(94vw,560px)] -translate-x-1/2 items-center justify-between rounded-3xl border border-white/45 bg-white/70 px-4 py-2 backdrop-blur-xl lg:hidden">
                    {navItems.map((item) => (
                        <button
                            key={item.label}
                            type="button"
                            className={[
                                'flex flex-1 flex-col items-center gap-1 rounded-2xl py-2 text-[11px] transition',
                                item.active ? 'bg-white text-serene-primary' : 'text-serene-muted',
                            ].join(' ')}
                        >
                            {item.icon}
                            <span>{item.label}</span>
                        </button>
                    ))}
                </nav>
            )}
        </>
    )
}
