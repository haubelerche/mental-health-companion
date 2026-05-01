import { Droplets, Waves, Wind } from 'lucide-react'
import bg from '../../../assets/healing.jpg'
import RevealSection from '../../../utils/RevealSection'

export default function MindfulSoundSection() {
    return (
        <RevealSection id="ocean-sound" className="relative min-h-screen px-6 py-20" delay={0.2}>
            <div className="mx-auto w-full max-w-7xl flex gap-5 flex-col lg:items-center lg:justify-between lg:flex-row">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.35em] text-white/75">Trở về bên trong</p>
                    <h4 className="mt-6 font-display text-4xl italic leading-tight text-white sm:text-6xl">
                        Chiều sâu của
                        <br />
                        sự tĩnh lặng
                    </h4>
                    <p className="mt-6 max-w-xl text-base leading-relaxed text-white/85 sm:text-lg">
                        Không gian này được thiết kế để tách biệt bạn khỏi những rào cản thông tin. Bằng cách tập trung vào các dao động âm thanh và duy trì nhịp độ hô hấp, bạn đang kích hoạt cơ chế tự phục hồi tự nhiên của tâm trí.
                    </p>

                    <div className="mt-10 space-y-5">
                        <article className="flex gap-3 items-center rounded-3xl border border-white/20 backdrop p-5">
                            {/* Icon Waves được hiểu là Sóng âm/Tần số */}
                            <Waves size={40} className="text-white/50" />
                            <div>
                                <h5 className="font-display text-2xl italic text-white">Tần số chữa lành</h5>
                                <p className="text-white/80 mt-1">Những dao động âm thanh có chủ đích giúp đưa trạng thái não bộ từ sóng Beta căng thẳng sang sóng Alpha thư giãn.</p>
                            </div>
                        </article>
                        <article className="flex gap-3 items-center rounded-3xl border border-white/20 backdrop p-5">
                            {/* Icon Wind được hiểu là Luồng khí/Hơi thở */}
                            <Wind size={40} className="text-white/50" />
                            <div>
                                <h5 className="font-display text-2xl italic text-white">Dòng chảy hơi thở</h5>
                                <p className="text-white/80 mt-1">Nhận biết sự chuyển động của không khí. Mỗi nhịp hít vào là sự kiến tạo năng lượng, mỗi nhịp thở ra là sự buông bỏ áp lực.</p>
                            </div>
                        </article>
                    </div>
                </div>

                <div className="relative">
                    <div className="aspect-3/4 overflow-hidden rounded-4xl border border-white/15">
                        <img src={bg} alt="Mindfulness state detail" height={540} width={480} className="object-cover" />
                        <div className="absolute inset-0 bg-linear-to-t from-black/75 via-transparent to-transparent border border-white/10 rounded-4xl" />
                        <div className="absolute inset-0 bg-linear-to-b from-black/45 via-transparent to-transparent border border-white/10 rounded-4xl" />
                    </div>
                    <div className="flex items-center gap-3 absolute bottom-8 left-8 right-8 rounded-3xl border border-white/20 backdrop p-5">
                        {/* Icon Droplets được hiểu là Sự thuần khiết/Mạch lạc */}
                        <Droplets className="text-white/80" />
                        <div>
                            <p className="font-display text-2xl italic text-white">Tâm trí vô ngã</p>
                            <p className="text-sm text-white/90 font-display italic mt-1">
                                "Sự bình yên thực sự không nằm ở nơi vắng bóng tiếng ồn, mà là sự vững chãi của nội tâm giữa vạn vật xao động."
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </RevealSection>
    )
}