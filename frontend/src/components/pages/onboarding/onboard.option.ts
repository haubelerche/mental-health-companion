import type { LucideIcon } from 'lucide-react'
import {
    Activity,
    BarChart2,
    BookOpen,
    Brain,
    CloudFog,
    CloudRain,
    CloudSun,
    Feather,
    Flame,
    Heart,
    HeartCrack,
    HeartHandshake,
    Moon,
    NotebookPen,
    PenLine,
    Stethoscope,
    Target,
    Wind,
} from 'lucide-react'

import type { EmotionalState, SupportLevel } from '../../../services/onboardingService'

type OnboardingDraft = {
    disclaimerAccepted: boolean
    nickname: string
    ageGroup: string
    emotionalState: EmotionalState | ''
    primaryConcern: string
    supportLevel: SupportLevel | ''
    stressLevel: number
    wakeTime: string
    bedTime: string
    practiceIds: string[]
}

type EmotionalOption = { id: EmotionalState; label: string; desc: string; Icon: LucideIcon }
type ChoiceOption = { id: string; label: string; Icon?: LucideIcon; desc?: string }
type PracticeOption = { id: string; label: string; Icon: LucideIcon }

const EMOTIONAL_OPTIONS: EmotionalOption[] = [
    { id: 'difficult_recently', label: 'Đang gặp khó khăn gần đây', desc: 'Nhiều thứ khiến mình bị quá tải.', Icon: CloudRain },
    { id: 'ongoing_challenges', label: 'Đang có thử thách tâm lý kéo dài', desc: 'Mình cần một nhịp hỗ trợ đều đặn.', Icon: HeartHandshake },
    { id: 'doing_okay', label: 'Mình đang khá ổn', desc: 'Mình muốn duy trì và chăm sóc tốt hơn.', Icon: CloudSun },
]

const PRIMARY_CONCERN_OPTIONS: ChoiceOption[] = [
    { id: 'breakup', label: 'Áp lực từ mối quan hệ', Icon: HeartCrack },
    { id: 'career_study', label: 'Áp lực học tập/công việc', Icon: BookOpen },
    { id: 'health', label: 'Lo lắng về sức khỏe', Icon: Stethoscope },
    { id: 'burnout', label: 'Kiệt sức kéo dài', Icon: Flame },
    { id: 'loneliness', label: 'Cảm giác cô đơn', Icon: CloudFog },
    { id: 'loss', label: 'Mất mát gần đây', Icon: Feather },
    { id: 'other', label: 'Điều khác', Icon: PenLine },
]

const SUPPORT_OPTIONS: ChoiceOption[] = [
    { id: 'excellent', label: 'Rất tốt', desc: 'Mình có nhiều người luôn ở bên.' },
    { id: 'good', label: 'Tốt', desc: 'Mình có người để chia sẻ khi cần.' },
    { id: 'limited', label: 'Hạn chế', desc: 'Có vài người nhưng chưa thật sự gần.' },
    { id: 'poor', label: 'Rất ít', desc: 'Mình thường tự xoay xở một mình.' },
]

const AGE_OPTIONS: ChoiceOption[] = [
    { id: 'under_18', label: 'Dưới 18' },
    { id: '18_24', label: '18-24' },
    { id: '25_34', label: '25-34' },
    { id: '35_plus', label: '35 trở lên' },
    { id: 'prefer_not', label: 'Không muốn trả lời' },
]

const PRACTICE_OPTIONS: PracticeOption[] = [
    { id: 'breathing', label: 'Bài thở', Icon: Wind },
    { id: 'journaling', label: 'Journaling', Icon: NotebookPen },
    { id: 'meditation', label: 'Thiền', Icon: Brain },
    { id: 'mood_tracking', label: 'Theo dõi cảm xúc', Icon: BarChart2 },
    { id: 'gratitude', label: 'Biết ơn', Icon: Heart },
    { id: 'physical_activity', label: 'Vận động', Icon: Activity },
    { id: 'better_sleep', label: 'Ngủ tốt hơn', Icon: Moon },
    { id: 'productivity', label: 'Tập trung học tập', Icon: Target },
]

const STRESS_LABELS = ['Rất tốt', 'Tạm ổn', 'Có lúc chao đảo', 'Khá khó khăn', 'Rất quá tải']

export type { OnboardingDraft, EmotionalOption, ChoiceOption, PracticeOption }
export { EMOTIONAL_OPTIONS, PRIMARY_CONCERN_OPTIONS, SUPPORT_OPTIONS, AGE_OPTIONS, PRACTICE_OPTIONS, STRESS_LABELS }
