import { motion } from 'framer-motion'
import trangNgu from '../../../assets/motion/cat-soul.gif'

export default function SleepyNightSection() {
    return (
        <section
            id="dem-kho-ngu"
            aria-labelledby="sleepy-heading"
            style={{
                background: `linear-gradient(180deg, var(--bg-midnight) 0%, var(--bg-deep) 50%, var(--bg-midnight) 100%)`,
            }}
        >
            {/* rain-blue glow */}
            <div
                className="ambient-dot"
                style={{
                    width: 600,
                    height: 600,
                    background: 'var(--rain-blue)',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    opacity: 0.15,
                }}
            />

            <div className="section-inner" style={{ textAlign: 'center' }}>
                <motion.div
                    initial={{ opacity: 0, y: 24 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, amount: 0.3 }}
                    transition={{ duration: 0.7, ease: 'easeOut' }}
                >
                    <span className="section-label">Cho những đêm khó ngủ</span>

                    {/* GIF illustration */}
                    <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '2.5rem' }}>
                        <div
                            style={{
                                border: '2px solid var(--rain-blue)',
                                borderRadius: 4,
                                padding: '1rem',
                                background: 'rgba(93,143,175,0.06)',
                                boxShadow: '0 0 48px rgba(93,143,175,0.15)',
                                display: 'inline-block',
                            }}
                        >
                            <img
                                src={trangNgu}
                                alt="Mèo ngủ ngon — cho những đêm khó ngủ"
                                className="pixel-img"
                                style={{ display: 'block', maxWidth: 320, width: '100%', borderRadius: 2 }}
                                loading="lazy"
                            />
                        </div>
                    </div>

                    <h2
                        id="sleepy-heading"
                        className="pixel-headline"
                        style={{
                            fontSize: 'clamp(1.5rem, 2vw, 2.5rem)',
                            marginBottom: '1.5rem',
                            color: 'var(--rain-blue)',
                            textShadow: '2px 2px 0 var(--pixel-shadow), 0 0 20px rgba(93,143,175,0.4)',
                        }}
                    >
                        Những lúc 2 giờ sáng<br />
                        không ai để gọi.
                    </h2>

                    <p
                        className="vn-body"
                        style={{
                            // maxWidth: 520,
                            margin: '0 auto 1rem',
                            fontSize: '1.05rem',
                        }}
                    >
                        Sự hiện diện nhẹ nhàng và riêng tư khi bạn cần một nơi an toàn để trút bỏ những suy nghĩ ngổn ngang trước khi ngủ.
                    </p>

                    <p
                        className="vn-body"
                        style={{
                            maxWidth: 480,
                            margin: '0 auto',
                            fontSize: '0.95rem',
                            fontStyle: 'italic',
                            color: 'var(--text-muted)',
                        }}
                    >
                        Serene không phán xét. Chỉ lắng nghe.
                    </p>
                </motion.div>
            </div>
        </section>
    )
}
