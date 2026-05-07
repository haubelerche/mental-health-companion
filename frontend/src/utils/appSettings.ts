export type ThemeOption = 'sunset' | 'ocean' | 'dawn' | 'night'
export type AppearanceMode = 'light' | 'dark'

export type AppSettings = {
    theme: ThemeOption
    mode: AppearanceMode
    /** Client-only display preference. Must not be treated as clinical, reward, profile, or backend consent state. */
    maskIdentity: boolean
    /** Client-only UI preference for local sharing affordances; backend data-sharing consent must use an API contract. */
    shareData: boolean
    /** Client-only notification display preference; persisted notification history lives on the backend. */
    reminder: boolean
    /** Client-only summary display preference; analytical summaries must be fetched from the backend. */
    weeklySummary: boolean
}

export const APP_SETTINGS_STORAGE_KEY = 'serene:app-settings'
export const APP_SETTINGS_UPDATED_EVENT = 'serene:app-settings-updated'

export const DEFAULT_APP_SETTINGS: AppSettings = {
    theme: 'night',
    mode: 'dark',
    maskIdentity: false,
    shareData: false,
    reminder: true,
    weeklySummary: true,
}

function isThemeOption(value: unknown): value is ThemeOption {
    return value === 'sunset' || value === 'ocean' || value === 'dawn' || value === 'night'
}

function isAppearanceMode(value: unknown): value is AppearanceMode {
    return value === 'light' || value === 'dark'
}

export function readAppSettings(): AppSettings {
    if (typeof window === 'undefined') {
        return DEFAULT_APP_SETTINGS
    }

    try {
        const raw = window.localStorage.getItem(APP_SETTINGS_STORAGE_KEY)
        if (!raw) {
            return DEFAULT_APP_SETTINGS
        }

        const parsed = JSON.parse(raw) as Partial<AppSettings>

        return {
            theme: isThemeOption(parsed.theme) ? parsed.theme : DEFAULT_APP_SETTINGS.theme,
            mode: isAppearanceMode(parsed.mode)
                ? parsed.mode
                : (isThemeOption(parsed.theme) && parsed.theme === 'night' ? 'dark' : 'light'),
            maskIdentity: typeof parsed.maskIdentity === 'boolean' ? parsed.maskIdentity : DEFAULT_APP_SETTINGS.maskIdentity,
            shareData: typeof parsed.shareData === 'boolean' ? parsed.shareData : DEFAULT_APP_SETTINGS.shareData,
            reminder: typeof parsed.reminder === 'boolean' ? parsed.reminder : DEFAULT_APP_SETTINGS.reminder,
            weeklySummary: typeof parsed.weeklySummary === 'boolean' ? parsed.weeklySummary : DEFAULT_APP_SETTINGS.weeklySummary,
        }
    } catch {
        return DEFAULT_APP_SETTINGS
    }
}

export function saveAppSettings(settings: AppSettings) {
    if (typeof window === 'undefined') {
        return
    }

    const uiOnlySettings: AppSettings = {
        theme: settings.theme,
        mode: settings.mode,
        maskIdentity: settings.maskIdentity,
        shareData: settings.shareData,
        reminder: settings.reminder,
        weeklySummary: settings.weeklySummary,
    }

    window.localStorage.setItem(APP_SETTINGS_STORAGE_KEY, JSON.stringify(uiOnlySettings))
    window.dispatchEvent(
        new CustomEvent<AppSettings>(APP_SETTINGS_UPDATED_EVENT, {
            detail: uiOnlySettings,
        }),
    )
}

export function updateAppMode(mode: AppearanceMode) {
    const current = readAppSettings()
    saveAppSettings({
        ...current,
        mode,
    })
}
