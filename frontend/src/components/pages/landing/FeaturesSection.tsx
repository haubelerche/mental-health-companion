import { motion } from 'framer-motion'
import pageSereneChat from '../../../assets/motion/page-serene-chat.gif'
import calmness from '../../../assets/motion/calmness.gif'
import pageSereneLanding from '../../../assets/motion/page-serene-landing.gif'
import miniPicture from '../../../assets/motion/mini-picture.gif'
import fishing from '../../../assets/motion/fishing.gif'
import support from '../../../assets/motion/support.gif'

const FEATURES = [
    {
        id: 'chat',
        icon: pageSereneChat,
        title: 'Trò chuyện cảm xúc an toàn',
        desc: 'Một không gian riêng tư để bạn trút bầu tâm sự mà không sợ bị đánh giá.',
        accent: 'var(--mint)',
        accentBg: 'rgba(85,221,161,0.04)',
    },
    {
        id: 'checkin',
        icon: calmness,
        title: 'Check-in ngắn mỗi ngày',
        desc: 'Theo dõi cảm xúc hàng ngày bằng những câu hỏi nhẹ nhàng.',
        accent: 'var(--leaf-green)',
        accentBg: 'rgba(52,211,153,0.04)',
    },
    {
        id: 'dashboard',
        icon: pageSereneLanding,
        title: 'Dashboard hiểu mình',
        desc: 'Nhìn lại hành trình cảm xúc qua các biểu đồ đơn giản, dễ hiểu.',
        accent: 'var(--yellow)',
        accentBg: 'rgba(250,204,21,0.04)',
    },
    {
        id: 'memory',
        icon: miniPicture,
        title: 'Ký ức có kiểm soát',
        desc: 'Bạn có toàn quyền quyết định những gì Serene ghi nhớ.',
        accent: 'var(--rain-blue)',
        accentBg: 'rgba(93,143,175,0.04)',
    },
    {
        id: 'action',
        icon: fishing,
        title: 'Một bước nhỏ để đi tiếp',
        desc: 'Gợi ý những hành động nhỏ gọn để bạn dần tìm lại sự cân bằng.',
        accent: 'var(--mint)',
        accentBg: 'rgba(85,221,161,0.04)',
    },
    {
        id: 'support',
        icon: support,
        title: 'An toàn khi cần hỗ trợ thật',
        desc: 'Kết nối nhanh chóng với các số điện thoại khẩn cấp khi cần thiết.',
        accent: 'var(--leaf-green)',
        accentBg: 'rgba(52,211,153,0.04)',
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
                        style={{ fontSize: 'clamp(2.8rem, 1.8vw, 2.15rem)' }}
                    >
                        Đồng hành từng ngày,<br />
                        theo cách riêng của bạn.
                    </h2>
                </motion.div>

                <div
                    style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                        gap: '1.5rem',
                    }}
                >
                    {FEATURES.map((f, i) => (
                        <motion.div
                            key={f.id}
                            initial={{ opacity: 0, y: 24 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, amount: 0.3 }}
                            transition={{ duration: 0.5, delay: i * 0.08, ease: 'easeOut' }}
                        >
                            <div
                                className="pixel-card"
                                style={{
                                    padding: '1.5rem',
                                    background: f.accentBg,
                                    borderColor: 'rgba(255,255,255,0.1)', // Subtle border
                                    display: 'flex',
                                    flexDirection: 'column',
                                    gap: '1rem',
                                    height: '100%',
                                    transition: 'border-color 0.3s ease',
                                }}
                                onMouseEnter={(e) => (e.currentTarget.style.borderColor = f.accent)}
                                onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)')}
                            >
                                {/* Icon / Decoration */}
                                <div
                                    style={{
                                        height: 150,
                                        border: `1px solid ${f.accent}`,
                                        borderRadius: 2,
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        padding: 2,
                                        flexShrink: 0,
                                        background: 'rgba(255,255,255,0.02)',
                                    }}
                                >
                                    <img
                                        src={f.icon}
                                        alt=""
                                        className="pixel-img"
                                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                        loading="lazy"
                                    />
                                </div>

                                <h3
                                    className="pixel-headline-sm"
                                    style={{
                                        fontSize: '1.5rem',
                                        color: 'var(--yellow)',
                                        margin: 0,
                                    }}
                                >
                                    {f.title}
                                </h3>

                                <p className="vn-body" style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-muted)' }}>
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
