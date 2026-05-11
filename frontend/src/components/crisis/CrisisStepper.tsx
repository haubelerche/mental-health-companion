import { CrisisActionCard, type CrisisAction } from './CrisisActionCard'

type CrisisPlan = {
    action_cards?: CrisisAction[]
    follow_up_question?: string
}

type Props = {
    crisisPlan?: CrisisPlan | null
    onAction: (card: CrisisAction) => void
}

export function CrisisStepper({ crisisPlan, onAction }: Props) {
    if (!crisisPlan) return null
    const cards = [...(crisisPlan.action_cards ?? [])]
        .filter((card) => card.action !== 'play_voice_grounding')
        .sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0))
        .slice(0, 3)

    return (
        <section className="mt-2 w-full max-w-[360px] border border-[#8a6a3f]/50 bg-[#0b1810]/92 p-3 shadow-[3px_3px_0_rgba(0,0,0,0.38)]">
            <div className="space-y-3">
                {cards.length > 0 && (
                    <div className="space-y-2">
                        {cards.map((card) => (
                            <CrisisActionCard key={card.id} card={card} onAction={onAction} />
                        ))}
                    </div>
                )}

                {crisisPlan.follow_up_question && (
                    <div className="border border-[#3a6040]/55 bg-[#09130d] px-3 py-2 text-sm leading-relaxed text-[#fff4dc]/88">
                        {crisisPlan.follow_up_question}
                    </div>
                )}
            </div>
        </section>
    )
}
