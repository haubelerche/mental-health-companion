import { Link } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
const navItems = [
    { label: 'Bình yên', id: 'hero' },
    { label: 'Về chúng tôi', id: 'about-ai' },
    { label: 'Âm thanh', id: 'ocean-sound' },
    { label: 'Hít thở', id: 'breath-space' },
]
export default function Header() {
    const { user, isLoading } = useAuth()
    const [activeSection, setActiveSection] = useState('')

    useEffect(() => {
        const sections = document.querySelectorAll('section[id]')

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        setActiveSection(entry.target.id)
                    }
                })
            },
            {
                root: null,
                rootMargin: '-40% 0px -40% 0px',
                threshold: 0,
            }
        )

        sections.forEach((section) => observer.observe(section))

        return () => observer.disconnect()
    }, [])
    const scrollToSection = (id: string) => {
        const el = document.getElementById(id)
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
    }
    return (
        <header className="sticky top-0 z-40 border-b border-white/10 bg-black/15 backdrop-blur-xl">
            <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4">
                <a href="/" className="font-display text-3xl italic tracking-wide text-white">Serene</a>
                <div className="flex gap-6">
                    {navItems.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => scrollToSection(item.id)}
                            className={`relative transition-colors ${activeSection === item.id
                                ? 'text-white'
                                : 'text-white/70 hover:text-white'
                                }`}
                        >
                            {item.label}

                            {/* underline animation */}
                            <motion.div
                                layoutId="nav-underline"
                                className="absolute -bottom-1 left-0 h-px w-full bg-white"
                                style={{
                                    opacity: activeSection === item.id ? 1 : 0,
                                }}
                            />
                        </button>
                    ))}
                </div>
                {isLoading ? (
                    <span className="font-display tracking-wide italic">
                        Xin chào
                    </span>
                ) : user ? (
                    <span className="font-display tracking-wide italic">
                        Xin chào <strong>{user.displayName}</strong>
                    </span>
                ) : (
                    <Link to="/login" className="rounded-full bg-white px-5 py-2 font-semibold text-serene-ink transition hover:bg-white/90">
                        Đăng nhập
                    </Link>
                )}
            </div>
        </header>
    )
}