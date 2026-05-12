import type { OnboardingTourStep } from '../../services/onboardingTourService'
import PixelDialogueBox from './PixelDialogueBox'
import hauLuong from '../../assets/assistants/hau-luong.png'

const GUIDE_CHARACTER_NAME = 'Hau Luong'

type Props = {
    step: OnboardingTourStep
    total: number
    activeIndex: number
    onPrimary: () => void
    onSecondary?: () => void
    onDismiss: () => void
}

export default function TourDock({ step, onPrimary, onSecondary, onDismiss }: Props) {
    return (
        <PixelDialogueBox
            speakerName={GUIDE_CHARACTER_NAME}
            portraitSrc={hauLuong}
            title={step.title}
            text={step.body}
            primaryLabel={step.primary_cta}
            secondaryLabel={step.secondary_cta ?? undefined}
            onPrimary={onPrimary}
            onSecondary={onSecondary}
            onClose={onDismiss}
            className="fixed inset-x-3 bottom-4 z-[80] mx-auto max-w-4xl"
        />
    )
}
