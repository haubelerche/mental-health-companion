import { motion } from 'framer-motion'
import banTotGif from '../../../assets/motion/ban-tot.gif'
import nguoiThayPng from '../../../assets/motion/nguoi-thay.png'

const PERSONAS = [
    {
        id: 'ban-tot',
        image: banTotGif,
        imageAlt: 'Bạn Tốt — người bạn đồng hành vui vẻ',
        badge: 'Người Bạn Cùng Tiến',
        badgeClass: 'persona-badge persona-badge-mint',
        title: 'Vui vẻ & Sát cánh',
        desc: 'Khuyến khích bạn mỗi ngày, cùng bạn vượt qua những lúc khó khăn nhỏ và ăn mừng những chiến thắng bé nhỏ.',
        accentColor: 'var(--mint)',
    },
    {
        id: 'nguoi-thay',
        image: nguoiThayPng,
        imageAlt: 'Người Thầy — người hướng dẫn bình tĩnh',
        badge: 'Người Hướng Dẫn Yên Bình',
        badgeClass: 'persona-badge persona-badge-blue',
        title: 'Lắng nghe sâu sắc',
        desc: 'Gợi mở từ tốn, không vội vã. Giúp bạn gỡ rối những suy nghĩ phức tạp và tìm ra hướng đi riêng của mình.',
        accentColor: 'var(--rain-blue)',
    },
]

export default function PersonaSection() {
    return (
        <section
            id="dong-hanh"
            aria-labelledby="persona-heading"
            style={{
                background: `linear-gradient(180deg, var(--bg-midnight) 0%, var(--bg-deep) 100%)`,
            }}
        >
            <div className="section-inner">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, amount: 0.2 }}
                    transition={{ duration: 0.55 }}
                    style={{ textAlign: 'center', marginBottom: '3.5rem' }}
                >
                    <span className="section-label">Serene đồng hành theo nhiều sắc thái</span>
                    <h2
                        id="persona-heading"
                        className="pixel-headline"
                        style={{ fontSize: 'clamp(1.8rem, 2vw, 2.5rem)' }}
                    >
                        Chọn sắc thái phù hợp<br />
                        với bạn hôm nay.
                    </h2>
                </motion.div>

                <div
                    style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                        gap: '2rem',
                    }}
                >
                    {PERSONAS.map((p, i) => (
                        <motion.div
                            key={p.id}
                            initial={{ opacity: 0, x: i === 0 ? -24 : 24 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true, amount: 0.3 }}
                            transition={{ duration: 0.65, ease: 'easeOut', delay: i * 0.1 }}
                        >
                            <div
                                className="pixel-card"
                                style={{
                                    padding: '2.5rem 2rem',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    gap: '1.5rem',
                                    textAlign: 'center',
                                    borderColor: p.accentColor,
                                    boxShadow: `4px 4px 0 var(--pixel-shadow), 0 0 32px ${p.accentColor}22`,
                                    height: '100%',
                                }}
                            >
                                {/* Character image */}
                                <div
                                    style={{
                                        width: 180,
                                        height: 180,
                                        border: `2px solid ${p.accentColor}`,
                                        borderRadius: 2,
                                        overflow: 'hidden',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        background: `${p.accentColor}0a`,
                                    }}
                                >
                                    <img
                                        src={p.image}
                                        alt={p.imageAlt}
                                        className="pixel-img"
                                        style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                                        loading="lazy"
                                    />
                                </div>

                                {/* Badge */}
                                <span className={p.badgeClass}>{p.badge}</span>

                                {/* Title */}
                                <h3
                                    className="pixel-headline-sm"
                                    style={{
                                        fontSize: 'clamp(1.65rem, 1.2vw, 1.8rem)',
                                        color: p.accentColor,
                                        margin: 0,
                                    }}
                                >
                                    {p.title}
                                </h3>

                                {/* Description */}
                                <p className="vn-body" style={{ margin: 0, fontSize: '0.95rem' }}>
                                    {p.desc}
                                </p>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    )
}
