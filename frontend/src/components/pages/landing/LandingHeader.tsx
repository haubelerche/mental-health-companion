import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../../hooks/useAuth'
import { AnimatePresence, motion } from 'framer-motion'


const NAV_ITEMS = [
    { label: 'Vì sao', href: '#vi-sao' },
    { label: 'Làm được gì', href: '#lam-duoc-gi' },
    { label: 'Cách hoạt động', href: '#cach-hoat-dong' },
    { label: 'Bắt đầu', href: '#loi-nhan' },
]

function scrollToId(id: string) {
    const el = document.querySelector(id)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

export default function LandingHeader() {
    const { user, isLoading } = useAuth()
    const [scrolled, setScrolled] = useState(false)
    const [mobileOpen, setMobileOpen] = useState(false)

    useEffect(() => {
        const onScroll = () => setScrolled(window.scrollY > 80)
        window.addEventListener('scroll', onScroll, { passive: true })
        return () => window.removeEventListener('scroll', onScroll)
    }, [])

    return (
        <header
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                zIndex: 50,
                background: scrolled
                    ? 'rgba(7,17,31,0.85)'
                    : 'transparent',
                backdropFilter: scrolled ? 'blur(16px)' : 'none',
                borderBottom: scrolled ? '1px solid var(--border-soft)' : '1px solid transparent',
                transition: 'background 0.35s ease, border-color 0.35s ease, backdrop-filter 0.35s ease',
            }}
        >
            <div
                style={{
                    maxWidth: 1120,
                    margin: '0 auto',
                    padding: '0.85rem 1.5rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '1rem',
                }}
            >
                {/* Logo */}
                <Link
                    to="/"
                    style={{
                        fontFamily: 'var(--font-pixel)',
                        fontSize: 'clamp(2rem, 3vw, 2.5rem)',
                        color: 'var(--yellow)',
                        textDecoration: 'none',
                        textShadow: '2px 2px 0 rgba(2,8,18,0.8)',
                        flexShrink: 0,
                    }}
                >
                    SereneAI
                </Link>

                {/* Desktop nav */}
                <nav
                    aria-label="Main navigation"
                    style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}
                    className="landing-nav-desktop"
                >
                    {NAV_ITEMS.map((item) => (
                        <button
                            key={item.label}
                            onClick={() => scrollToId(item.href)}
                                style={{
                                background: 'none',
                                border: 'none',
                                cursor: 'pointer',
                                fontFamily: 'var(--font-pixel)',
                                fontSize: '1.5rem',
                                padding: '4px 0',
                                transition: 'color 0.2s',
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--mint)')}
                            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-main)')}
                        >
                            {item.label}
                        </button>
                    ))}
                </nav>

                {/* Right section */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexShrink: 0 }}>
                    {!isLoading && (
                        user ? (
                            <Link
                                to="/serene"
                                className="pixel-btn"
                                style={{ padding: '10px 20px', fontSize: '1.55rem' }}
                            >
                                Vào ứng dụng →
                            </Link>
                        ) : (
                            <>
                                <Link
                                    to="/login"
                                    className="pixel-btn"
                                    style={{ padding: '5px  20px', fontSize: '1.25rem' }}
                                >
                                    Đăng nhập →
                                </Link>
                            </>
                        )
                    )}

                    {/* Mobile hamburger */}
                    <button
                        aria-label={mobileOpen ? 'Đóng menu' : 'Mở menu'}
                        aria-expanded={mobileOpen}
                        onClick={() => setMobileOpen(!mobileOpen)}
                        style={{
                            background: 'none',
                            border: '1px solid var(--border-soft)',
                            borderRadius: 2,
                            padding: '6px 8px',
                            cursor: 'pointer',
                            color: 'var(--text-main)',
                            display: 'none',
                        }}
                        className="landing-hamburger"
                    >
                        <svg width="18" height="14" viewBox="0 0 18 14" fill="none">
                            {mobileOpen ? (
                                <path d="M1 1L17 13M17 1L1 13" stroke="currentColor" strokeWidth="2" strokeLinecap="square" />
                            ) : (
                                <>
                                    <line y1="1" x2="18" y2="1" stroke="currentColor" strokeWidth="2" />
                                    <line y1="7" x2="18" y2="7" stroke="currentColor" strokeWidth="2" />
                                    <line y1="13" x2="18" y2="13" stroke="currentColor" strokeWidth="2" />
                                </>
                            )}
                        </svg>
                    </button>
                </div>
            </div>

            {/* Mobile menu */}
            <AnimatePresence>
                {mobileOpen && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        style={{
                            overflow: 'hidden',
                            background: 'rgba(7,17,31,0.97)',
                            borderTop: '1px solid var(--border-soft)',
                        }}
                    >
                        <nav style={{ padding: '1rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            {NAV_ITEMS.map((item) => (
                                <button
                                    key={item.label}
                                    onClick={() => { scrollToId(item.href); setMobileOpen(false) }}
                                    style={{
                                        background: 'none',
                                        border: 'none',
                                        cursor: 'pointer',
                                        fontFamily: 'var(--font-vn)',
                                        fontSize: '1rem',
                                        color: 'var(--text-muted)',
                                        padding: '0.75rem 0.5rem',
                                        textAlign: 'left',
                                        borderBottom: '1px solid var(--border-soft)',
                                        transition: 'color 0.2s',
                                    }}
                                >
                                    {item.label}
                                </button>
                            ))}
                        </nav>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Inline responsive style */}
            <style>{`
                @media (max-width: 768px) {
                    .landing-nav-desktop { display: none !important; }
                    .landing-hamburger { display: block !important; }
                }
            `}</style>
        </header>
    )
}
