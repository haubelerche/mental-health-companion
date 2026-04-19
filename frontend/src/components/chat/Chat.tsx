import { Heart, History, Image, Leaf, Mic, MoreVertical, Send, Smile, Wind } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import bg from '../../assets/bg2.png'

const suggestedExercise = {
  icon: <Wind className="h-8 w-8" />,
  title: 'BÀI TẬP: Thở 4-7-8',
  description: 'Bài tập đề xuất',
  cta: 'Bắt đầu',
}

type Message = {
  id: string
  type: 'user' | 'serene'
  content?: string
  icon?: React.ReactNode
  timestamp: Date
}

const mockMessages: Message[] = [
  {
    id: '1',
    type: 'serene',
    content: 'Xin chào! Mình là Serene. Hôm nay bạn cảm thấy thế nào?',
    timestamp: new Date(Date.now() - 5 * 60000),
  },
  {
    id: '2',
    type: 'user',
    content: 'Cảm thấy hơi ngộp vì bài vở quá nhiều...',
    timestamp: new Date(Date.now() - 4 * 60000),
  },
  {
    id: '3',
    type: 'serene',
    content: 'Mình hiểu mà. Đôi khi mọi thứ dồn dập khiến ta thấy khó thở. Cậu thử dành 2 phút làm bài tập này cùng mình nhé?',
    timestamp: new Date(Date.now() - 3 * 60000),
  },
]

const moodIcons = [
  { id: 'happy', icon: <Smile className="h-6 w-6" />, label: 'Vui' },
  { id: 'love', icon: <Heart className="h-6 w-6" />, label: 'Yêu thích' },
  { id: 'wind', icon: <Wind className="h-6 w-6" />, label: 'Thư thái' },
  { id: 'leaf', icon: <Leaf className="h-6 w-6" />, label: 'Bình yên' },
]

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>(mockMessages)
  const [inputValue, setInputValue] = useState('')
  const [showMoodEmojis, setShowMoodEmojis] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = () => {
    if (!inputValue.trim()) return

    const newMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, newMessage])
    setInputValue('')

    // Mock response sau 1 giây
    setTimeout(() => {
      const responses = [
        'Cảm ơn bạn đã chia sẻ. Mình lắng nghe bạn đây.',
        'Điều đó rất bình thường. Hãy thở sâu và từ từ.',
        'Bạn làm rất tốt khi chia sẻ với mình.',
        'Mình hiểu. Cùng nhau vượt qua nhé!',
      ]
      const randomResponse = responses[Math.floor(Math.random() * responses.length)]
      const sereneMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'serene',
        content: randomResponse,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, sereneMessage])
    }, 1000)
  }

  const handleSendIcon = (icon: React.ReactNode, label: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      icon,
      content: label,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, newMessage])
    setShowMoodEmojis(false)

    // Mock response
    setTimeout(() => {
      const sereneMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'serene',
        content: `Tuyệt vời! Tâm trạng "${label}" của bạn rất đẹp.`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, sereneMessage])
    }, 800)
  }
  return (
    <div className="relative min-h-screen text-serene-ink">
      <div className="fixed inset-0 -z-20">
        <img src={bg} alt="Biển hoàng hôn" className="h-full w-full object-cover " />
        <div className="absolute inset-0 bg-white/20" />
      </div>

      <main className="relative z-10 flex min-h-screen items-center justify-center p-4 sm:p-6 ">
        <section className="flex h-[calc(100vh-2rem)] w-full max-w-4xl flex-col overflow-hidden rounded-[28px] border border-white/40 bg-white/65  backdrop-blur-3xl sm:h-[calc(100vh-3rem)] lg:max-h-[870px]">
          <header className="flex items-center justify-between px-5 py-5 sm:px-8 sm:py-7">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-serene-on-primary text-primary shadow-sm">
                <Leaf />
              </div>
              <div>
                <h2 className="font-display text-2xl font-semibold text-on-surface sm:text-3xl">
                  Serene
                </h2>
                <div className="mt-1 flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  <span className="text-sm uppercase  text-on-surface-variant">
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
            <div
              ref={messagesContainerRef}
              className="flex flex-1 flex-col gap-6 overflow-y-auto px-1 py-2 sm:px-2"
            >
              {messages.map((msg, idx) => (
                <div key={msg.id} className={`flex gap-3 sm:gap-4 ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.type === 'serene' && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-serene-on-primary text-primary shadow-sm">
                      <Leaf className="h-4 w-4" />
                    </div>
                  )}

                  <div className={`flex max-w-[82%] flex-col gap-2 ${msg.type === 'user' ? 'items-end' : 'items-start'} sm:max-w-[70%]`}>
                    {msg.type === 'serene' && idx === messages.length - 2 && msg.id === messages[messages.length - 2]?.id && (
                      <div className="group mb-2 flex w-full items-center gap-3 rounded-2xl border border-white/40 bg-white/65 p-4 shadow-sm backdrop-blur-xl transition hover:shadow-md sm:gap-4 sm:p-5">
                        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-serene-primary shadow-sm sm:h-14 sm:w-14">
                          {suggestedExercise.icon}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-[9px] uppercase tracking-wide text-on-surface-variant/75 sm:text-[10px]">
                            {suggestedExercise.description}
                          </p>
                          <h3 className="font-display text-sm font-semibold text-on-surface sm:text-base">
                            {suggestedExercise.title}
                          </h3>
                        </div>
                        <button
                          type="button"
                          className="whitespace-nowrap rounded-full bg-serene-primary px-3 py-2 text-xs font-semibold text-serene-on-primary shadow-md transition hover:brightness-105 active:scale-95 sm:px-4 sm:py-2.5 sm:text-sm"
                        >
                          {suggestedExercise.cta}
                        </button>
                      </div>
                    )}

                    {msg.icon ? (
                      <div className={`flex h-12 w-12 items-center justify-center rounded-3xl ${msg.type === 'user' ? 'bg-serene-primary text-serene-on-primary' : 'bg-white/45 text-serene-primary'} shadow-md sm:h-14 sm:w-14`}>
                        {msg.icon}
                      </div>
                    ) : (
                      <div
                        className={`rounded-3xl ${msg.type === 'user'
                          ? 'rounded-tr-none border border-white/20 bg-white/45 text-on-surface'
                          : 'rounded-tl-none border border-serene-ink/10 bg-serene-primary/5 text-on-surface'
                          } px-5 py-3 shadow-sm sm:px-6 sm:py-4`}
                      >
                        <p className="text-sm leading-relaxed sm:text-base">
                          {msg.content}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <footer className="mt-4 border-t border-white/25 pt-4 sm:mt-6 sm:pt-6">
              <div className="flex items-end gap-3 sm:gap-4">
                <div className="relative flex-1">
                  <input
                    type="text"
                    placeholder="Chia sẻ cùng Serene..."
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleSendMessage()
                      }
                    }}
                    className="w-full rounded-full border-none bg-white/70 px-5 py-4 pr-24 text-sm shadow-sm outline-none ring-0 placeholder:text-on-surface-variant/50 focus:bg-surface-container-low/85 focus:ring-0 sm:px-8 sm:py-5 sm:text-lg"
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
                  onClick={handleSendMessage}
                  className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary bg-serene-primary text-serene-bg shadow-md transition hover:scale-105 active:scale-95 sm:h-16 sm:w-16"
                  aria-label="Gửi"
                >
                  <Send className="h-6 w-6 fill-current sm:h-7 sm:w-7" />
                </button>
              </div>

              {showMoodEmojis && (
                <div className="mt-3 flex flex-wrap justify-center gap-2 sm:gap-3">
                  {moodIcons.map((mood) => (
                    <button
                      key={mood.id}
                      type="button"
                      onClick={() => handleSendIcon(mood.icon, mood.label)}
                      className="flex flex-col items-center gap-1 rounded-lg bg-white/50 p-2 text-center transition hover:bg-white/70 active:scale-95 sm:p-3"
                      title={mood.label}
                    >
                      <span className="text-serene-primary">
                        {mood.icon}
                      </span>
                      <span className="text-[8px] uppercase tracking-wide text-on-surface-variant/70 sm:text-[9px]">
                        {mood.label}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              <div className="mt-3 flex flex-wrap justify-center gap-4 sm:mt-4 sm:gap-8">
                <button
                  type="button"
                  onClick={() => setShowMoodEmojis(!showMoodEmojis)}
                  className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-serene-muted transition hover:text-primary sm:gap-2 sm:text-xs"
                >
                  <Smile className="h-4 w-4" />
                  Tâm trạng hiện tại
                </button>
                <button
                  type="button"
                  className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-serene-muted transition hover:text-primary sm:gap-2 sm:text-xs"
                >
                  <Image className="h-4 w-4" />
                  Gửi ảnh bình yên
                </button>
              </div>
            </footer>
          </div>
        </section>
      </main>


    </div>
  )
}