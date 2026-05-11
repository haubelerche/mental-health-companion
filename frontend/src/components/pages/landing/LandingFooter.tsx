import { Link } from 'react-router-dom'
import pageSerene from '../../../assets/motion/page-serene-landing.gif'
import birdGif from '../../../assets/motion/bird.gif'

const LINKS = [
    { label: 'Về chúng tôi', href: '#vi-sao' },
    { label: 'Chính sách bảo mật', href: '/privacy' },
    { label: 'Điều khoản dịch vụ', href: '/terms' },
    { label: 'Liên hệ', href: 'mailto:hello@sereneai.vn' },
]

export default function LandingFooter() {
    return (
        <footer className="landing-footer" aria-label="Footer">
            {/* Background GIF */}
            <img
                src={pageSerene}
                alt=""
                aria-hidden="true"
                className="footer-bg pixel-img"
            />
            {/* Gradient overlay */}
            <div className="footer-overlay" />

            {/* Content */}
            <div
                style={{
                    position: 'relative',
                    zIndex: 1,
                    maxWidth: 1120,
                    margin: '0 auto',
                    padding: '4rem 1.5rem 2.5rem',
                }}
            >
                {/* Brand row */}
                <div
                    style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        justifyContent: 'space-between',
                        flexWrap: 'wrap',
                        gap: '2.5rem',
                        marginBottom: '3rem',
                        borderBottom: '1px solid var(--border-soft)',
                        paddingBottom: '3rem',
                    }}
                >
                    {/* Brand */}
                    <div style={{ maxWidth: 340 }}>
                        <Link
                            to="/landing"
                            style={{
                                fontFamily: 'var(--font-pixel)',
                                fontSize: 'clamp(2.7rem, 1.3vw, 0.9rem)',
                                color: 'var(--yellow)',
                                textDecoration: 'none',
                                textShadow: '2px 2px 0 var(--pixel-shadow)',
                                display: 'block',
                                marginBottom: '1rem',
                            }}
                        >
                            SereneAI
                        </Link>
                        <p
                            className="vn-body"
                            style={{ fontSize: '0.88rem', margin: 0 }}
                        >
                            Người bạn đồng hành AI sức khoẻ tâm thần bằng tiếng Việt.
                            Luôn lắng nghe, không phán xét.
                        </p>
                    </div>
   <img
                    src={birdGif}
                    alt=""
                    aria-hidden="true"
                    className="pixel-img"
                    style={{
                        width: '100px',
                        height: 'auto',
                        opacity: 0.9,
                    }}
                />
                    {/* Links */}
                    <nav aria-label="Footer navigation">
                        <p
                            style={{
                                fontFamily: 'var(--font-pixel)',
                                fontSize: '1.5rem',
                                color: 'var(--mint)',
                                letterSpacing: '0.2em',
                                textTransform: 'uppercase',
                                marginBottom: '1rem',
                            }}
                        >
                            Liên kết
                        </p>
                        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            {LINKS.map((l) => (
                                <li key={l.label}>
                                    {l.href.startsWith('http') || l.href.startsWith('mailto') ? (
                                        <a
                                            href={l.href}
                                            style={{
                                                fontFamily: 'var(--font-vn)',
                                                fontSize: '0.9rem',
                                                color: 'var(--text-muted)',
                                                textDecoration: 'none',
                                                transition: 'color 0.2s',
                                            }}
                                            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--mint)')}
                                            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
                                        >
                                            {l.label}
                                        </a>
                                    ) : (
                                        <Link
                                            to={l.href}
                                            style={{
                                                fontFamily: 'var(--font-vn)',
                                                fontSize: '0.9rem',
                                                color: 'var(--text-muted)',
                                                textDecoration: 'none',
                                                transition: 'color 0.2s',
                                            }}
                                            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--mint)')}
                                            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
                                        >
                                            {l.label}
                                        </Link>
                                    )}
                                </li>
                            ))}
                        </ul>
                    </nav>
                </div>

                {/* Copyright */}
                <p
                    style={{
                        fontFamily: 'var(--font-pixel)',
                        fontSize: '1.05rem',
                        color: 'var(--text-muted)',
                        letterSpacing: '0.15em',
                        opacity: 0.6,
                        margin: 0,
                        lineHeight: 2.2,
                        textAlign: 'center'
                    }}
                >
                    © 2026 SereneAI · Made by Team 039 with ❤️
                </p>
            </div>
        </footer>
    )
}
