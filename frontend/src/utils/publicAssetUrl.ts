/** Absolute URL for a file in `frontend/public/` (respects Vite `base`). */
export function publicAssetUrl(filename: string): string {
    const base = import.meta.env.BASE_URL || '/'
    const normalizedBase = base.endsWith('/') ? base : `${base}/`
    const path = filename.startsWith('/') ? filename.slice(1) : filename
    return new URL(path, window.location.origin + normalizedBase).href
}
