import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import starGif from '../../../assets/motion/star.gif'
import plan from '../../../assets/motion/plan.png'


export default function FinalCTASection() {
    return (
        <section
            id="loi-nhan"
            aria-labelledby="cta-heading"
            style={{
                background: `linear-gradient(180deg, var(--bg-deep) 0%, var(--bg-midnight) 100%)`,
                textAlign: 'center',
            }}
        >
            {/* Yellow ambient glow */}
            <div
                className="ambient-dot"
                style={{
                    width: 700,
                    height: 400,
                    background: 'var(--yellow)',
                    top: '30%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    opacity: 0.06,
                }}
            />

            <div className="section-inner" style={{ position: 'relative', zIndex: 1 }}>
                <motion.div
                    initial={{ opacity: 0, y: 28 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, amount: 0.3 }}
                    transition={{ duration: 0.7, ease: 'easeOut' }}
                    style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2rem' }}
                >
                    <img
                        src={plan}
                        alt="Mèo ấm áp — một bước nhỏ để đi tiếp"
                        className="pixel-img"
                        style={{ width: 250, height: 'auto', opacity: 0.9 }}
                        loading="lazy"
                    />

                    {/* Star accent + Headline */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                        <img
                            src={starGif}
                            alt=""
                            aria-hidden="true"
                            className="pixel-img"
                            style={{ width: 40, height: 40 }}
                        />
                        <h2
                            id="cta-heading"
                            className="pixel-headline"
                            style={{
                                fontSize: 'clamp(2.75rem, 1.8vw, 2rem)',
                                textAlign: 'center',
                            }}
                        >
                            Bắt đầu bằng một câu
                        </h2>
                        <img
                            src={starGif}
                            alt=""
                            aria-hidden="true"
                            className="pixel-img"
                            style={{ width: 40, height: 40 }}
                        />
                    </div>

                    <p
                        className="pixel-headline-sm"
                        style={{
                            fontSize: 'clamp(1.65rem, 1.3vw, 0.85rem)',
                            color: 'var(--text-muted)',
                            marginTop: '-0.5rem',
                        }}
                    >
                        rất nhỏ cũng được.
                    </p>

                    <p className="vn-body" style={{ maxWidth: 480, fontSize: '1rem' }}>
                        SereneAI không yêu cầu bạn phải sẵn sàng. Chỉ cần một câu — bất cứ điều gì bạn đang cảm thấy lúc này.
                    </p>

                    {/* CTA Buttons */}
                    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center', marginTop: '0.5rem' }}>
                        <Link to="/serene" className="pixel-btn">
                            <span>Bắt đầu miễn phí</span>
                            <span aria-hidden="true">→</span>
                        </Link>
                        <Link to="/login" className="pixel-btn pixel-btn-outline">
                            Đã có tài khoản
                        </Link>
                    </div>

                    {/* Disclaimer */}
                    <p
                        className="vn-body"
                        style={{
                            maxWidth: 520,
                            fontSize: '0.8rem',
                            color: 'var(--text-muted)',
                            marginTop: '1rem',
                            lineHeight: 1.7,
                            opacity: 0.7,
                        }}
                    >
                        Lưu ý: SereneAI không thay thế các liệu pháp tâm lý chuyên nghiệp.
                        Trong trường hợp khẩn cấp, vui lòng liên hệ cơ sở y tế gần nhất.
                    </p>
                </motion.div>
            </div>
        </section>
    )
}
