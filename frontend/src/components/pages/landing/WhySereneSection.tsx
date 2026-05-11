import { motion } from 'framer-motion'
import catFriend from '../../../assets/motion/cat-and-friend.gif'

const fadeUp = {
    hidden: { opacity: 0, y: 28 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.65, ease: 'easeOut' } },
}

export default function WhySereneSection() {
    return (
        <section id="vi-sao" aria-labelledby="why-serene-heading">
            {/* ambient glow */}
            <div
                className="ambient-dot"
                style={{
                    width: 500,
                    height: 500,
                    background: 'var(--mint)',
                    top: -100,
                    left: -100,
                }}
            />

            <div className="section-inner">
                <div
                    style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                        gap: '4rem',
                        alignItems: 'center',
                    }}
                >
                    {/* Text */}
                    <motion.div
                        initial="hidden"
                        whileInView="visible"
                        viewport={{ once: true, amount: 0.35 }}
                        variants={fadeUp}
                    >
                        <span className="section-label">Vì sao có SereneAI</span>
                        <h2
                            id="why-serene-heading"
                            className="pixel-headline"
                            style={{ fontSize: 'clamp(2.85rem, 2vw, 1.25rem)', marginBottom: '1.75rem' }}
                        >
                            Không cần phải ổn<br />
                            mới bắt đầu.
                        </h2>
                        <p className="vn-body" style={{ marginBottom: '1.25rem', maxWidth: 480 }}>
                            Đôi khi bạn chỉ cần một nơi để nói — không phán xét, không chẩn đoán, không yêu cầu bạn phải hiểu chính mình ngay lập tức.
                        </p>
                        <p className="vn-body" style={{ maxWidth: 480 }}>
                            SereneAI được tạo ra bằng tiếng Việt, cho người Việt — một người bạn đồng hành AI hiểu ngữ cảnh, cảm xúc và cách người mình nói chuyện.
                        </p>

                        <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem', flexWrap: 'wrap' }}>
                            {['Không phán xét', 'Không chẩn đoán', 'Bằng tiếng Việt'].map((tag) => (
                                <span
                                    key={tag}
                                    style={{
                                        fontFamily: 'var(--font-pixel)',
                                        fontSize: '1rem',
                                        padding: '6px 12px',
                                        border: '1px solid var(--mint)',
                                        color: 'var(--mint)',
                                        background: 'rgba(85,221,161,0.06)',
                                        borderRadius: 2,
                                        letterSpacing: '0.05em',
                                    }}
                                >
                                    {tag}
                                </span>
                            ))}
                        </div>
                    </motion.div>

                    {/* Cat-and-friend illustration card */}
                    <motion.div
                        initial="hidden"
                        whileInView="visible"
                        viewport={{ once: true, amount: 0.35 }}
                        variants={{ ...fadeUp, visible: { opacity: 1, y: 0, transition: { duration: 0.65, ease: 'easeOut', delay: 0.15 } } }}
                    >
                        <div
                            className="pixel-card glow-mint"
                            style={{
                                padding: '2rem',
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                gap: '1.25rem',
                            }}
                        >
                            <img
                                src={catFriend}
                                alt="Mèo và người bạn — cảm giác được đồng hành"
                                className="pixel-img"
                                style={{ width: '100%', maxWidth: 280, borderRadius: 2 }}
                                loading="lazy"
                            />
                            <p
                                className="vn-body"
                                style={{
                                    textAlign: 'center',
                                    fontSize: '0.9rem',
                                    fontStyle: 'italic',
                                    color: 'var(--text-muted)',
                                }}
                            >
                                "Không phải cô đơn — Serene ở đây cùng bạn."
                            </p>
                        </div>
                    </motion.div>
                </div>
            </div>
        </section>
    )
}
