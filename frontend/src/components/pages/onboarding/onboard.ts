import type { EmotionalState, SupportLevel } from "../../../services/onboardingService"


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

type EmotionalOption = { id: EmotionalState; label: string; desc: string; icon: string }
type ChoiceOption = { id: string; label: string; icon?: string; desc?: string }
type PracticeOption = { id: string; label: string; icon: string }

const EMOTIONAL_OPTIONS: EmotionalOption[] = [
    { id: 'difficult_recently', label: 'Đang gặp khó khăn gần đây', desc: 'Nhiều thứ khiến mình bị quá tải.', icon: '🌧️' },
    { id: 'ongoing_challenges', label: 'Đang có thử thách tâm lý kéo dài', desc: 'Mình cần một nhịp hỗ trợ đều đặn.', icon: '🫶' },
    { id: 'doing_okay', label: 'Mình đang khá ổn', desc: 'Mình muốn duy trì và chăm sóc tốt hơn.', icon: '🌤️' },
]

const PRIMARY_CONCERN_OPTIONS: ChoiceOption[] = [
    { id: 'breakup', label: 'Áp lực từ mối quan hệ', icon: '💔' },
    { id: 'career_study', label: 'Áp lực học tập/công việc', icon: '📚' },
    { id: 'health', label: 'Lo lắng về sức khỏe', icon: '🩺' },
    { id: 'burnout', label: 'Kiệt sức kéo dài', icon: '🔥' },
    { id: 'loneliness', label: 'Cảm giác cô đơn', icon: '🌫️' },
    { id: 'loss', label: 'Mất mát gần đây', icon: '🕊️' },
    { id: 'other', label: 'Điều khác', icon: '📝' },
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
    { id: 'breathing', label: 'Bài thở', icon: '☁️' },
    { id: 'journaling', label: 'Journaling', icon: '📝' },
    { id: 'meditation', label: 'Thiền', icon: '🧘' },
    { id: 'mood_tracking', label: 'Theo dõi cảm xúc', icon: '💙' },
    { id: 'gratitude', label: 'Biết ơn', icon: '✨' },
    { id: 'physical_activity', label: 'Vận động', icon: '🏃' },
    { id: 'better_sleep', label: 'Ngủ tốt hơn', icon: '🌙' },
    { id: 'productivity', label: 'Tập trung học tập', icon: '🎯' },
]

const STRESS_LABELS = ['Rất tốt', 'Tạm ổn', 'Có lúc chao đảo', 'Khá khó khăn', 'Rất quá tải']

export type { OnboardingDraft, EmotionalOption, ChoiceOption, PracticeOption }
export { EMOTIONAL_OPTIONS, PRIMARY_CONCERN_OPTIONS, SUPPORT_OPTIONS, AGE_OPTIONS, PRACTICE_OPTIONS, STRESS_LABELS }