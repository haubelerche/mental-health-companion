import { AirVent, History, Image, Mic, MoreVertical, Send, Smile } from 'lucide-react'
import bg from '../../assets/bg2.png'

const suggestedExercise = {
  icon: <AirVent className="h-8 w-8" />,
  title: 'BÀI TẬP: Thở 4-7-8',
  description: 'Bài tập đề xuất',
  cta: 'Bắt đầu',
}

export default function Chat() {
  return (
    <div className="relative min-h-screen text-serene-ink">
      <div className="fixed inset-0 -z-20">
        <img src={bg} alt="Biển hoàng hôn" className="h-full w-full object-cover opacity-85" />
        <div className="absolute inset-0 bg-white/20" />
      </div>

      <main className="relative z-10 flex min-h-screen items-center justify-center p-4 sm:p-6 ">
        <section className="flex h-[calc(100vh-2rem)] w-full max-w-4xl flex-col overflow-hidden rounded-[28px] border border-white/40 bg-white/65 shadow-[0_40px_100px_-20px_rgba(0,0,0,0.16)] backdrop-blur-3xl sm:h-[calc(100vh-3rem)] lg:max-h-[870px]">
          <header className="flex items-center justify-between px-5 py-5 sm:px-8 sm:py-7">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-container text-primary shadow-sm">
                <span className="material-symbols-outlined text-2xl font-normal" style={{ fontVariationSettings: `'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24` }}>
                  spa
                </span>
              </div>
              <div>
                <h2 className="font-display text-2xl font-semibold text-on-surface sm:text-3xl">
                  Serene
                </h2>
                <div className="mt-1 flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  <span className="text-[10px] uppercase tracking-[0.26em] text-on-surface-variant">
                    Đang lắng nghe
                  </span>
                </div>
              </div>
            </div>

            <div className="flex gap-2 sm:gap-3">
              <button
                type="button"
                className="flex h-10 w-10 items-center justify-center rounded-full text-on-surface-variant transition hover:bg-surface-variant/35 hover:text-primary"
                aria-label="Lịch sử"
              >
                <History className="h-5 w-5" />
              </button>
              <button
                type="button"
                className="flex h-10 w-10 items-center justify-center rounded-full text-on-surface-variant transition hover:bg-surface-variant/35 hover:text-primary"
                aria-label="Tùy chọn"
              >
                <MoreVertical className="h-5 w-5" />
              </button>
            </div>
          </header>

          <div className="flex flex-1 flex-col overflow-hidden px-4 pb-4 sm:px-8">
            <div className="flex flex-1 flex-col gap-8 overflow-y-auto px-1 py-2 sm:px-2">
              <div className="flex justify-center">
                <span className="rounded-full bg-white/45 px-4 py-1 text-[10px] uppercase tracking-[0.2em] text-on-surface-variant/70 shadow-sm backdrop-blur-md">
                  Hôm nay, 5:30 chiều
                </span>
              </div>

              <div className="flex justify-end">
                <div className="max-w-[78%] rounded-3xl rounded-tr-none border border-white/20 bg-white/45 px-5 py-4 shadow-sm backdrop-blur-md sm:max-w-[70%] sm:px-6">
                  <p className="text-sm leading-relaxed italic text-on-surface sm:text-base">
                    Cảm thấy hơi ngộp vì bài vở quá nhiều...
                  </p>
                </div>
              </div>

              <div className="flex justify-start gap-3 sm:gap-4">
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary-fixed text-primary-dim shadow-sm sm:h-9 sm:w-9">
                  <span className="material-symbols-outlined text-sm font-normal" style={{ fontVariationSettings: `'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24` }}>
                    spa
                  </span>
                </div>

                <div className="flex max-w-[82%] flex-col gap-4 sm:max-w-[75%]">
                  <div className="rounded-3xl rounded-tl-none border border-primary/10 bg-primary/5 px-5 py-4 shadow-sm sm:px-6">
                    <p className="text-sm leading-relaxed text-on-surface sm:text-base">
                      Mình hiểu mà. Đôi khi mọi thứ dồn dập khiến ta thấy khó thở. Cậu thử dành 2 phút
                      làm bài tập này cùng mình nhé?
                    </p>
                  </div>

                  <div className="group flex items-center gap-4 rounded-[24px] border border-white/40 bg-white/65 p-4 shadow-sm backdrop-blur-xl transition hover:shadow-md sm:gap-5 sm:p-6">
                    <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl bg-secondary-container text-on-secondary-container shadow-sm sm:h-16 sm:w-16">
                      {suggestedExercise.icon}
                    </div>

                    <div className="min-w-0 flex-1">
                      <p className="mb-1 text-[10px] uppercase tracking-[0.24em] text-on-surface-variant/75">
                        {suggestedExercise.description}
                      </p>
                      <h3 className="font-display text-lg font-semibold text-on-surface sm:text-xl">
                        {suggestedExercise.title}
                      </h3>
                    </div>

                    <button
                      type="button"
                      className="rounded-full bg-primary px-4 py-2.5 text-xs font-semibold tracking-wide text-on-primary shadow-lg transition active:scale-95 hover:brightness-105 sm:px-6 sm:text-sm"
                    >
                      {suggestedExercise.cta}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <footer className="mt-4 border-t border-white/25 pt-4 sm:mt-6 sm:pt-6">
              <div className="flex items-end gap-3 sm:gap-4">
                <div className="relative flex-1">
                  <input
                    type="text"
                    placeholder="Chia sẻ cùng Serene..."
                    className="w-full rounded-full border-none bg-surface-container-low/70 px-5 py-4 pr-24 text-sm text-on-surface shadow-sm outline-none ring-0 placeholder:text-on-surface-variant/50 focus:bg-surface-container-low/85 focus:ring-0 sm:px-8 sm:py-5 sm:text-lg"
                  />

                  <div className="absolute right-3 top-1/2 flex -translate-y-1/2 items-center gap-1 sm:gap-2">
                    <button
                      type="button"
                      className="flex h-9 w-9 items-center justify-center rounded-full text-on-surface-variant transition hover:text-primary"
                      aria-label="Ghi âm"
                    >
                      <Mic className="h-5 w-5" />
                    </button>
                    <button
                      type="button"
                      className="flex h-9 w-9 items-center justify-center rounded-full text-on-surface-variant transition hover:text-primary"
                      aria-label="Biểu cảm"
                    >
                      <Smile className="h-5 w-5" />
                    </button>
                  </div>
                </div>

                <button
                  type="button"
                  className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full bg-primary text-on-primary shadow-[0_18px_35px_rgba(77,99,89,0.28)] transition hover:scale-105 active:scale-95 sm:h-16 sm:w-16"
                  aria-label="Gửi"
                >
                  <Send className="h-6 w-6 fill-current sm:h-7 sm:w-7" />
                </button>
              </div>

              <div className="mt-4 flex flex-wrap justify-center gap-4 sm:mt-5 sm:gap-8">
                <button
                  type="button"
                  className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-on-surface-variant/70 transition hover:text-primary sm:text-xs"
                >
                  <span className="material-symbols-outlined text-sm font-normal">sentiment_satisfied</span>
                  Tâm trạng hiện tại
                </button>
                <button
                  type="button"
                  className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-on-surface-variant/70 transition hover:text-primary sm:text-xs"
                >
                  <Image className="h-4 w-4" />
                  Gửi ảnh bình yên
                </button>
              </div>
            </footer>
          </div>
        </section>
      </main>

      <div className="fixed right-0 top-0 z-0 h-1/3 w-1/3 translate-x-1/2 -translate-y-1/2 rounded-full bg-primary-fixed/20 blur-[120px]" />
      <div className="fixed bottom-0 left-0 z-0 h-1/4 w-1/4 -translate-x-1/2 translate-y-1/2 rounded-full bg-secondary-fixed/20 blur-[100px]" />
    </div>
  )
}