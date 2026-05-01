import { Link } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { LogOut } from "lucide-react";
const navItems = [
    { label: 'Bình yên', id: 'hero' },
    { label: 'Về chúng tôi', id: 'about-ai' },
    { label: 'Âm thanh', id: 'ocean-sound' },
    { label: 'Hít thở', id: 'breath-space' },
]
export default function Header() {
    const { user, isLoading } = useAuth()
    const [activeSection, setActiveSection] = useState('')
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

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
        setMobileMenuOpen(false)
    }
    return (
        <header className="sticky top-0 z-40 border-b border-white/10 bg-black/15 backdrop-blur-xl">
            <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-4 sm:px-6 py-3 sm:py-4">
                {/* Logo */}
                <a href="/" className="font-display text-2xl sm:text-3xl italic tracking-wide text-white shrink-0">
                    Serene
                </a>

                {/* Desktop Navigation */}
                <div className="hidden md:flex gap-4 lg:gap-6 flex-1 justify-center">
                    {navItems.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => scrollToSection(item.id)}
                            className={`relative text-sm lg:text-base transition-colors ${activeSection === item.id
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

                {/* Right Section: Auth & Mobile Menu Button */}
                <div className="flex items-center gap-3 sm:gap-4">
                    {isLoading ? (
                        <span className="font-display tracking-wide italic text-sm sm:text-base hidden md:block">
                            Xin chào
                        </span>
                    ) : user ? (
                        <div className="inline-flex items-center gap-3">
                            <span className="font-display tracking-wide italic text-sm sm:text-base hidden md:block">
                                Xin chào <strong>{user.displayName}</strong>
                            </span>
                            <button className="hover:text-red-400 cursor-pointer mb-1">
                                <LogOut className="w-5 h-5" />
                            </button>
                        </div>
                    ) : (
                        <Link to="/login" className="hidden sm:block rounded-full bg-white px-4 py-2 text-sm font-semibold text-serene-ink transition hover:bg-white/90">
                            Đăng nhập
                        </Link>
                    )}

                    {/* Mobile Menu Button */}
                    <button
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                        className="md:hidden p-2 rounded-lg hover:bg-white/10 transition"
                        aria-label="Toggle menu"
                    >
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            {mobileMenuOpen ? (
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            ) : (
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                            )}
                        </svg>
                    </button>
                </div>
            </div>

            {/* Mobile Menu */}
            <AnimatePresence>
                {mobileMenuOpen && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="md:hidden border-t border-white/10 bg-black/40 backdrop-blur-md overflow-hidden"
                    >
                        <div className="px-4 py-3 space-y-2">
                            {navItems.map((item) => (
                                <button
                                    key={item.id}
                                    onClick={() => scrollToSection(item.id)}
                                    className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${activeSection === item.id
                                        ? 'text-white bg-white/10'
                                        : 'text-white/70 hover:text-white hover:bg-white/5'
                                        }`}
                                >
                                    {item.label}
                                </button>
                            ))}
                            {!user && !isLoading && (
                                <Link
                                    to="/login"
                                    onClick={() => setMobileMenuOpen(false)}
                                    className="block w-full mt-3 rounded-full bg-white px-4 py-3 text-center text-sm font-semibold text-serene-ink transition hover:bg-white/90"
                                >
                                    Đăng nhập
                                </Link>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </header>
    )
}