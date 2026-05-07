export const REWARD_UPDATED_EVENT = 'serene:reward-updated'

/** Dispatch after a backend operation that changes the user's heart balance. */
export function dispatchRewardUpdate(newBalance: number): void {
    window.dispatchEvent(new CustomEvent(REWARD_UPDATED_EVENT, { detail: { balance: newBalance } }))
}
