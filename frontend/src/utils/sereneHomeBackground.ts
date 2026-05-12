/**
 * Background for the exact `/serene` route (local clock).
 * - 05:00–12:59 → morning
 * - 13:00–17:59 → noon
 * - 18:00–04:59 → night
 */
export function resolveSereneHomeBackground(
    morningUrl: string,
    noonUrl: string,
    nightUrl: string,
    now: Date = new Date(),
): string {
    const minutesSinceMidnight = now.getHours() * 60 + now.getMinutes()
    const morningStart = 5 * 60
    const noonStart = 13 * 60
    const nightStart = 18 * 60
    if (minutesSinceMidnight >= morningStart && minutesSinceMidnight < noonStart) {
        return morningUrl
    }
    if (minutesSinceMidnight >= noonStart && minutesSinceMidnight < nightStart) {
        return noonUrl
    }
    return nightUrl
}
