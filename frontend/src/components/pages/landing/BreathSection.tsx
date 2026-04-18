export default function BreathSection() {
    return (
        <section className="px-6 py-30" id="breath-space">
            <div className="max-w-4xl mx-auto text-center space-y-20 px-6">
                <div className="space-y-4">
                    <h2 className="text-6xl font-display text-white italic">Hãy để tâm trí được nghỉ ngơi</h2>
                    <p className=" text-white/70 text-lg">Hít thở sâu theo nhịp điệu của đại dương</p>
                </div>
                <div className="flex justify-center">
                    <div className="relative flex items-center justify-center">
                        <div className="w-80 h-80 rounded-full border border-white/10 animate-[ping_4s_linear_infinite] opacity-20"></div>
                        <div className="absolute w-64 h-64 rounded-full glass-panel border border-white/20 flex items-center justify-center editorial-shadow">
                            <div className="w-40 h-40 rounded-full bg-white/10 backdrop-blur-xl border border-white/30 flex items-center justify-center">
                                <span className="material-symbols-outlined text-white text-5xl animate-pulse">waves</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="grid grid-cols-3 gap-12 max-w-xl mx-auto font-display">
                    <div className="space-y-2">
                        <span className="block text-4xl text-white italic">4s</span>
                        <span className=" font-label uppercase tracking-widest ">Hít vào</span>
                    </div>
                    <div className="space-y-2 border-x border-white/10">
                        <span className="block text-4xl text-white italic">7s</span>
                        <span className=" font-label uppercase tracking-widest ">Tĩnh lặng</span>
                    </div>
                    <div className="space-y-2">
                        <span className="block text-4xl text-white italic">8s</span>
                        <span className=" font-label uppercase tracking-widest ">Buông lỏng</span>
                    </div>
                </div>
            </div>
        </section>
    )
}
