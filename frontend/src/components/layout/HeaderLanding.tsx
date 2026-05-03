import { Link } from "react-router-dom";

export default function Header() {
    return (
        <header className="sticky top-0 z-40 border-b border-white/10 bg-black/10 backdrop-blur-xl">
            <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4">
                <a href="/" className="font-display text-3xl italic tracking-tight text-white">Serene</a>
                <nav className="hidden items-center gap-8 md:flex">
                    <Link to="/landing/#hero" className="text-sm tracking-wide text-white/85 hover:text-white">Sanctuary</Link>
                    <Link to="/landing/#about-ai" className="text-sm tracking-wide text-white/85 hover:text-white">About</Link>
                    <Link to="/landing/#ocean-sound" className="text-sm tracking-wide text-white/85 hover:text-white">Ocean Sound</Link>
                    <Link to="/landing/#breath-space" className="text-sm tracking-wide text-white/85 hover:text-white">Breath</Link>
                </nav>
                <Link to="/login" className="rounded-full bg-white px-5 py-2 text-sm font-semibold text-serene-ink transition hover:bg-white/90">
                    Đăng nhập
                </Link>
            </div>
        </header>
    )
}