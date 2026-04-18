export default function Footer() {
    return (
        <footer className="hidden border-t border-white/30 bg-white/35 px-12 py-8 text-[11px] uppercase tracking-[0.22em] text-serene-muted/85 backdrop-blur-xl lg:flex lg:items-center lg:justify-between">
            <span>© 2026 Serene</span>
            <div className="flex items-center gap-10">
                <button type="button" className="transition hover:text-serene-primary">
                    Trợ giúp
                </button>
                <button type="button" className="transition hover:text-serene-primary">
                    Privacy Policy
                </button>
                <button type="button" className="transition hover:text-serene-primary">
                    Terms of Peace
                </button>
            </div>
        </footer>
    )
}