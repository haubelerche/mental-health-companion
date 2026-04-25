import { httpClient } from '../api/httpClient'

export type ExercisePattern = {
    inhale: number
    hold: number
    exhale: number
    hold2?: number
}

export type ExerciseItem = {
    id: string
    type: string
    title: string
    description: string
    duration_sec: number
    route: string
    pattern: ExercisePattern | null
    steps: string[]
    thumbnail: string | null
}

export const FALLBACK_EXERCISES: ExerciseItem[] = [
    {
        id: 'box_breath',
        type: 'breathing_exercise',
        title: 'Box',
        description: 'Nhịp thở 4-4-4-4 giúp ổn định hệ thần kinh và thư giãn nhanh.',
        duration_sec: 300,
        route: '/serene/exercises?exercise=box_breath',
        pattern: { inhale: 4, hold: 4, exhale: 4, hold2: 4 },
        steps: [
            'Hít vào bằng mũi trong 4 giây.',
            'Giữ hơi thở trong 4 giây.',
            'Thở ra thật chậm trong 4 giây.',
            'Giữ nhẹ thêm 4 giây rồi lặp lại.',
        ],
        thumbnail: null,
    },
    {
        id: 'breath_478',
        type: 'breathing_exercise',
        title: 'Hơi thở bình yên',
        description: 'Bài thở 4-7-8 trong 2 phút để hạ nhịp căng thẳng.',
        duration_sec: 120,
        route: '/serene/exercises?exercise=breath_478',
        pattern: { inhale: 4, hold: 7, exhale: 8 },
        steps: [
            'Đặt một tay lên ngực, một tay lên bụng.',
            'Hít vào bằng mũi trong 4 giây.',
            'Giữ hơi thở trong 7 giây.',
            'Thở ra thật chậm trong 8 giây.',
        ],
        thumbnail: null,
    },
    {
        id: 'equal_breath',
        type: 'breathing_exercise',
        title: 'Equal',
        description: 'Nhịp 5-0-5 giúp cân bằng hơi thở và tăng tập trung.',
        duration_sec: 300,
        route: '/serene/exercises?exercise=equal_breath',
        pattern: { inhale: 5, hold: 0, exhale: 5 },
        steps: [
            'Hít vào đều qua mũi 5 giây.',
            'Thở ra đều 5 giây.',
            'Giữ nhịp mềm và thả lỏng vai gáy.',
        ],
        thumbnail: null,
    },
    {
        id: 'custom_breath',
        type: 'breathing_exercise',
        title: 'Custom',
        description: 'Tùy chỉnh nhịp thở theo cảm giác hiện tại của bạn.',
        duration_sec: 300,
        route: '/serene/exercises?exercise=custom_breath',
        pattern: null,
        steps: [
            'Bắt đầu với một nhịp hít vào thoải mái.',
            'Giữ ngắn hoặc bỏ qua nếu thấy khó chịu.',
            'Thở ra dài hơn một chút so với hít vào.',
            'Duy trì nhịp cá nhân trong 5 phút.',
        ],
        thumbnail: null,
    },
    {
        id: 'grounding_54321',
        type: 'grounding_exercise',
        title: 'Neo lại hiện tại',
        description: 'Grounding 5-4-3-2-1 để kéo sự chú ý về môi trường an toàn quanh bạn.',
        duration_sec: 180,
        route: '/serene/exercises?exercise=grounding_54321',
        pattern: null,
        steps: [
            'Nhìn quanh và gọi tên 5 thứ bạn thấy.',
            'Chạm vào 4 bề mặt khác nhau.',
            'Lắng nghe 3 âm thanh đang có mặt.',
            'Nhận ra 2 mùi hương hoặc cảm giác trong hơi thở.',
            'Gọi tên 1 điều nhỏ đang giúp bạn an toàn hơn.',
        ],
        thumbnail: null,
    },
    {
        id: 'body_scan',
        type: 'body_scan',
        title: 'Quét cơ thể dịu lại',
        description: 'Năm phút buông lỏng từng vùng cơ thể sau một ngày quá tải.',
        duration_sec: 300,
        route: '/serene/exercises?exercise=body_scan',
        pattern: null,
        steps: [
            'Ngồi hoặc nằm ở tư thế bạn thấy vững.',
            'Đưa sự chú ý xuống bàn chân và thả lỏng các ngón chân.',
            'Di chuyển dần lên bắp chân, đùi, bụng và vai.',
            'Thả lỏng hàm, trán và vùng quanh mắt.',
            'Kết thúc bằng một hơi thở sâu, chậm và mềm.',
        ],
        thumbnail: null,
    },
]

export function findFallbackExercise(exerciseId: string | null): ExerciseItem {
    return FALLBACK_EXERCISES.find((item) => item.id === exerciseId) ?? FALLBACK_EXERCISES[0]
}

export const exerciseService = {
    list: () => httpClient.get<{ items: ExerciseItem[] }>('/resources/exercises'),
    detail: (exerciseId: string) => httpClient.get<ExerciseItem>(`/resources/exercises/${encodeURIComponent(exerciseId)}`),
}
