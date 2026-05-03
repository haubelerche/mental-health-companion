const REWARD_STORAGE_KEY = 'serene_reward_progress_v1'
export const REWARD_UPDATED_EVENT = 'serene:reward-updated'

type RewardProgress = {
    hearts: number
    streakDays: number
    lastClaimedAt?: string
}

const DEFAULT_PROGRESS: RewardProgress = {
    hearts: 0,
    streakDays: 0,
}

function readProgress(): RewardProgress {
    try {
        const raw = localStorage.getItem(REWARD_STORAGE_KEY)
        if (!raw) return DEFAULT_PROGRESS
        const parsed = JSON.parse(raw) as Partial<RewardProgress>
        return {
            hearts: Number(parsed.hearts) || 0,
            streakDays: Number(parsed.streakDays) || 0,
            lastClaimedAt: typeof parsed.lastClaimedAt === 'string' ? parsed.lastClaimedAt : undefined,
        }
    } catch {
        return DEFAULT_PROGRESS
    }
}

function writeProgress(progress: RewardProgress): void {
    localStorage.setItem(REWARD_STORAGE_KEY, JSON.stringify(progress))
    window.dispatchEvent(new CustomEvent<RewardProgress>(REWARD_UPDATED_EVENT, { detail: progress }))
}

export function getRewardProgress(): RewardProgress {
    return readProgress()
}

/**
 * @deprecated Do not call from production flows. Wallet mutations belong on the backend.
 * Kept for legacy event listeners; do not add new callers.
 */
export function grantCheckinReward(heartsEarned: number, streakDays: number): RewardProgress {
    const current = readProgress()
    const next: RewardProgress = {
        hearts: Math.max(0, current.hearts + Math.max(0, heartsEarned)),
        streakDays: Math.max(current.streakDays, Math.max(0, streakDays)),
        lastClaimedAt: new Date().toISOString(),
    }
    writeProgress(next)
    return next
}

/**
 * @deprecated Do not call from production flows. Streak is authoritative on the backend.
 * Kept for legacy compatibility; do not add new callers.
 */
export function syncRewardStreak(streakDays: number): RewardProgress {
    const current = readProgress()
    if (streakDays <= current.streakDays) return current
    const next = { ...current, streakDays }
    writeProgress(next)
    return next
}
