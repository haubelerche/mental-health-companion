import { motion } from 'framer-motion'
import fishGif from '../../../assets/motion/fish.gif'
import catSoulGif from '../../../assets/motion/cat-soul.gif'

const FEATURES = [
    {
        id: 'checkin',
        icon: fishGif,
        iconAlt: 'Biểu tượng chăm sóc bản thân',
        badge: 'Hằng ngày',
        title: 'Thói quen nhẹ nhàng',
        desc: 'Check-in cảm xúc và gợi ý các hành động chăm sóc bản thân nhỏ bé mỗi ngày — không áp lực, không phức tạp.',
        accent: 'var(--mint)',
        accentBg: 'rgba(85,221,161,0.06)',
    },
    {
        id: 'reflect',
        icon: catSoulGif,
        iconAlt: 'Mèo suy ngẫm — nhìn lại bản thân',
        badge: 'Hành trình',
        title: 'Nhìn lại bản thân',
        desc: 'Dashboard trực quan giúp bạn theo dõi hành trình cảm xúc và hiểu mình hơn qua từng ngày.',
        accent: 'var(--rain-blue)',
        accentBg: 'rgba(93,143,175,0.06)',
    },
]

export default function FeaturesSection() {
    return (
        <section id="lam-duoc-gi" aria-labelledby="features-heading">
            <div className="section-inner">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, amount: 0.2 }}
                    transition={{ duration: 0.55 }}
                    style={{ textAlign: 'center', marginBottom: '3.5rem' }}
                >
                    <span className="section-label">SereneAI làm được gì</span>
                    <h2
                        id="features-heading"
                        className="pixel-headline"
                        style={{ fontSize: 'clamp(1.8rem, 1.8vw, 2.15rem)' }}
                    >
                        Đồng hành từng ngày,<br />
                        theo cách riêng của bạn.
                    </h2>
                </motion.div>

                <div
                    style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                        gap: '2rem',
                    }}
                >
                    {FEATURES.map((f, i) => (
                        <motion.div
                            key={f.id}
                            initial={{ opacity: 0, y: 28 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, amount: 0.3 }}
                            transition={{ duration: 0.6, delay: i * 0.12, ease: 'easeOut' }}
                        >
                            <div
                                className="pixel-card"
                                style={{
                                    padding: '2rem',
                                    background: f.accentBg,
                                    borderColor: f.accent,
                                    display: 'flex',
                                    flexDirection: 'column',
                                    gap: '1.25rem',
                                    height: '100%',
                                }}
                            >
                                {/* Icon */}
                                <div
                                    style={{
                                        width: 64,
                                        height: 64,
                                        border: `2px solid ${f.accent}`,
                                        borderRadius: 2,
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        padding: 4,
                                        flexShrink: 0,
                                    }}
                                >
                                    <img
                                        src={f.icon}
                                        alt={f.iconAlt}
                                        className="pixel-img"
                                        style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                                        loading="lazy"
                                    />
                                </div>

                                {/* Badge */}
                                <span
                                    style={{
                                        fontFamily: 'var(--font-pixel)',
                                        fontSize: '1.7rem',
                                        color: f.accent,
                                        letterSpacing: '0.15em',
                                        textTransform: 'uppercase',
                                    }}
                                >
                                    {f.badge}
                                </span>

                                <h3
                                    className="pixel-headline-sm"
                                    style={{
                                        fontSize: 'clamp(1.5rem, 1.4vw, 1rem)',
                                        color: 'var(--yellow)',
                                        margin: 0,
                                    }}
                                >
                                    {f.title}
                                </h3>

                                <p className="vn-body" style={{ margin: 0, fontSize: '0.95rem' }}>
                                    {f.desc}
                                </p>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    )
}
