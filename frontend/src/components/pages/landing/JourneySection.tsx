import { motion } from 'framer-motion'
import miniPicture from '../../../assets/motion/mini-picture.gif'
import catHouse from '../../../assets/motion/cat-house.gif'
import catAndPond from '../../../assets/motion/cat-and-pond.gif'
import fishing from '../../../assets/motion/fishing.gif'
import fishGif from '../../../assets/motion/fish.gif'

const STEPS = [
    {
        num: '01',
        enLabel: 'Talk',
        vnLabel: 'Nói Ra',
        desc: 'Chia sẻ điều bạn đang cảm thấy — ẩn danh, an toàn, không áp lực.',
        color: 'var(--mint)',
        image: catHouse,
    },
    {
        num: '02',
        enLabel: 'Understand',
        vnLabel: 'Thấu Hiểu',
        desc: 'Serene nhẹ nhàng phân tích cảm xúc và giúp bạn nhìn rõ hơn về bản thân.',
        color: 'var(--leaf-green)',
        image: catAndPond,
    },
    {
        num: '03',
        enLabel: 'Act',
        vnLabel: 'Hành Động',
        desc: 'Các bước nhỏ cụ thể để cân bằng lại — phù hợp với từng ngày của bạn.',
        color: 'var(--yellow)',
        image: fishing,
    },
    {
        num: '04',
        enLabel: 'Reflect',
        vnLabel: 'Nhìn Lại',
        desc: 'Theo dõi hành trình cảm xúc cá nhân — hiểu mình hơn qua từng ngày.',
        color: 'var(--rain-blue)',
        image: miniPicture,
    },
]

export default function JourneySection() {
    return (
        <section id="cach-hoat-dong" aria-labelledby="journey-heading">
            <div className="section-inner">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, amount: 0.2 }}
                    transition={{ duration: 0.55 }}
                    style={{ textAlign: 'center', marginBottom: '3.5rem' }}
                >
                    <span className="section-label">Cách hoạt động</span>
                    <h2
                        id="journey-heading"
                        className="pixel-headline"
                        style={{ fontSize: '2.5rem' }}
                    >
                        Hành trình 4 bước đồng hành cùng bạn.
                    </h2>
                </motion.div>

                {/* Steps grid */}
                <div className="journey-steps">
                    {STEPS.map((step, i) => (
                        <motion.div
                            key={step.num}
                            initial={{ opacity: 0, y: 24 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, amount: 0.25 }}
                            transition={{ duration: 0.55, delay: i * 0.1, ease: 'easeOut' }}
                            style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
                        >
                            {/* Step number */}
                            <div className="journey-step-num" style={{ borderColor: step.color, color: step.color }}>
                                {step.num}
                            </div>

                            {/* Card */}
                            <div
                                className="pixel-card"
                                style={{
                                    padding: '1.5rem',
                                    borderColor: step.color,
                                    flex: 1,
                                    display: 'flex',
                                    flexDirection: 'column',
                                    gap: '0.75rem',
                                    position: 'relative',
                                }}
                            >
                                <span
                                    style={{
                                        fontFamily: 'var(--font-pixel)',
                                        fontSize: '1.7rem',
                                        color: step.color,
                                        letterSpacing: '0.1em',
                                    }}
                                >
                                    {step.enLabel}
                                </span>

                                <h3
                                    className="pixel-headline-sm"
                                    style={{
                                        fontSize: 'clamp(1.5rem, 1.2vw, 0.75rem)',
                                        color: step.color,
                                        margin: 0,
                                    }}
                                >
                                    {step.vnLabel}
                                </h3>

                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                    <p className="vn-body" style={{ margin: 0, fontSize: '0.9rem' }}>
                                        {step.desc}
                                    </p>
                                    <div
                                        style={{
                                            border: `2px solid ${step.color}`,
                                            borderRadius: 2,
                                            overflow: 'hidden',
                                            padding: 4,
                                            background: 'rgba(255,255,255,0.02)',
                                        }}
                                    >
                                        <img
                                            src={step.image}
                                            alt={`${step.vnLabel} illustration`}
                                            className="pixel-img"
                                            style={{ display: 'block', width: '100%', borderRadius: 1 }}
                                            loading="lazy"
                                        />
                                    </div>
                                </div>

                                {/* Decoration fish for step 2 */}
                                {step.num === '02' && (
                                    <img
                                        src={fishGif}
                                        alt=""
                                        aria-hidden="true"
                                        className="pixel-img"
                                        style={{
                                            position: 'absolute',
                                            bottom: '-20px',
                                            right: '-20px',
                                            width: '50px',
                                            height: 'auto',
                                            zIndex: 2,
                                        }}
                                    />
                                )}
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    )
}
