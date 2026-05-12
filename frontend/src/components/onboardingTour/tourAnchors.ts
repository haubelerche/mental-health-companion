export const TOUR_ANCHORS = {
    homeTodayCard: 'home-today-card',
    moodCheckinCard: 'mood-checkin-card',
    chatInput: 'chat-input',
    chatPersonaOptions: 'sidebar-chat',
    memoryTab: 'chat-memory-tab',
    rewardsNav: 'sidebar-rewards',
    heartBalance: 'heart-balance',
    resourcesNav: 'sidebar-resources',
    resourcesMain: 'resources-main',
    helpEntry: 'sidebar-help',
} as const

export function queryTourAnchor(anchorId: string): HTMLElement | null {
    if (typeof document === 'undefined') return null
    return document.querySelector<HTMLElement>(`[data-tour-id="${anchorId}"]`)
}
