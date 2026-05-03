import { httpClient } from '../api/httpClient'
import bg from '../assets/bg.png'
import bg2 from '../assets/bg2.png'
import bg3 from '../assets/bg3.png'
import forest from '../assets/forest.png'
import healing from '../assets/healing.jpg'

export type ResourceCategory = { id: string; label: string; icon: string }
export type ResourceItem = {
    id: string
    category: string
    title: string
    description?: string | null
    duration_sec: number
    format: string
    url: string
    thumbnail?: string | null
    bookmarked: boolean
    tags?: string[]
}

export const FALLBACK_RESOURCE_CATEGORIES: ResourceCategory[] = [
    { id: 'all', label: 'Tất cả', icon: '✦' },
    { id: 'meditate', label: 'Meditate', icon: '♧' },
    { id: 'sleep', label: 'Sleep', icon: '☾' },
    { id: 'music', label: 'Music', icon: '♪' },
    { id: 'wisdom', label: 'Wisdom', icon: '◌' },
    { id: 'movement', label: 'Movement', icon: '↟' },
]

export const FALLBACK_RESOURCES: ResourceItem[] = [
    {
        id: 'forest-anxiety',
        category: 'meditate',
        title: 'Xoa dịu lo âu',
        description: 'Một phiên âm thanh trong rừng để hạ nhịp suy nghĩ và quay về hơi thở.',
        duration_sec: 900,
        format: 'guided_audio',
        url: '/serene/exercises?exercise=breath_478',
        thumbnail: forest,
        bookmarked: false,
        tags: ['hot_session', 'nature_sounds'],
    },
    {
        id: 'inner-calm',
        category: 'meditate',
        title: 'Tự tin nội tại',
        description: 'Giọng dẫn ngắn giúp neo lại cảm giác đủ đầy và vững vàng.',
        duration_sec: 600,
        format: 'guided_voice',
        url: '/serene/exercises?exercise=grounding_54321',
        thumbnail: bg2,
        bookmarked: false,
        tags: ['guided_voice'],
    },
    {
        id: 'focus-shift',
        category: 'meditate',
        title: 'Sự tập trung tuyệt đối',
        description: 'Âm nền biển dịu để tập trung lại sau khi tâm trí bị kéo đi.',
        duration_sec: 1200,
        format: 'ambient_zen',
        url: '/serene/exercises?exercise=body_scan',
        thumbnail: bg,
        bookmarked: false,
        tags: ['ambient_zen'],
    },
    {
        id: 'self-connection',
        category: 'wisdom',
        title: 'Kết nối bản thân',
        description: 'Một bài nghe ngắn về cách quan sát suy nghĩ mà không đồng nhất với nó.',
        duration_sec: 660,
        format: 'binaural_beats',
        url: '/serene/resources',
        thumbnail: healing,
        bookmarked: false,
        tags: ['reflection'],
    },
    {
        id: 'midnight-woods',
        category: 'sleep',
        title: 'The Midnight Woods of Norfolk',
        description: 'Sleep story chậm rãi để chuyển cơ thể sang trạng thái nghỉ.',
        duration_sec: 2280,
        format: 'sleep_story',
        url: '/serene/exercises?exercise=body_scan',
        thumbnail: forest,
        bookmarked: false,
        tags: ['audio_38_min'],
    },
    {
        id: 'sleep-meditation-video',
        category: 'sleep',
        title: 'Video thiền ngủ 10 phút',
        description: 'Một phiên hướng dẫn nhẹ trước khi ngủ, phù hợp khi đầu óc còn nhiều suy nghĩ.',
        duration_sec: 600,
        format: 'guided_video',
        url: '/serene/exercises?exercise=body_scan',
        thumbnail: bg2,
        bookmarked: false,
        tags: ['thiền ngủ', 'sleep', 'video'],
    },
    {
        id: 'midnight-tides',
        category: 'sleep',
        title: 'Midnight Tides',
        description: 'Sóng biển lặp mềm, phù hợp khi khó ngủ hoặc thức giấc giữa đêm.',
        duration_sec: 3600,
        format: 'soundscape',
        url: '/serene/exercises?exercise=breath_478',
        thumbnail: bg3,
        bookmarked: false,
        tags: ['alpha_waves'],
    },
]

export function getFallbackResources(category = 'all'): ResourceItem[] {
    if (category === 'all') return FALLBACK_RESOURCES
    return FALLBACK_RESOURCES.filter((item) => item.category === category)
}

export const resourceService = {
    getCategories: () => httpClient.get<{ categories: ResourceCategory[] }>('/resources/categories'),
    list: (category: string, limit = 20, offset = 0) =>
        httpClient.get<{ items: ResourceItem[]; total: number; has_more: boolean }>(
            `/resources?category=${encodeURIComponent(category === 'all' ? 'meditate' : category)}&limit=${limit}&offset=${offset}`,
        ),
    listExercises: () => httpClient.get<{ items: unknown[] }>('/resources/exercises'),
}
