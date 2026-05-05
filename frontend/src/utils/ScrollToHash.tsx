import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export default function ScrollToHash() {
    const { hash } = useLocation();

    useEffect(() => {
        if (!hash) return
        try {
            // Prefer getElementById to avoid CSS selector parsing errors
            const id = hash.startsWith('#') ? decodeURIComponent(hash.slice(1)) : decodeURIComponent(hash)
            if (!id) return
            const el = document.getElementById(id)
            if (el) {
                setTimeout(() => {
                    el.scrollIntoView({ behavior: 'smooth' })
                }, 0)
            }
        } catch (err) {
            // Ignore invalid hash selector (e.g. Facebook adds "#_=_")
            // Prevents uncaught exceptions from breaking the app
            return
        }
    }, [hash]);

    return null;
}