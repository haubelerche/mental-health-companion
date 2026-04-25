import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ROUTE_PATHS } from '../../routes/paths'

type Exercise = {
  id: string
  title: string
  emoji: string
  description: string
  duration: string
  steps: string[]
}

const EXERCISES: Exercise[] = [
  {
    id: 'breathing_478',
    title: 'Thở 4-7-8',
    emoji: '🌬️',
    description: 'Giảm lo âu và căng thẳng chỉ trong 2 phút.',
    duration: '2 phút',
    steps: [
      'Thở ra hoàn toàn qua miệng',
      'Nhắm miệng, hít vào qua mũi đếm đến 4',
      'Nín thở, đếm đến 7',
      'Thở ra qua miệng, đếm đến 8',
      'Lặp lại 3–4 lần. Xong rồi — bạn làm tốt lắm!',
    ],
  },
  {
    id: 'grounding_54321',
    title: 'Grounding 5-4-3-2-1',
    emoji: '🌱',
    description: 'Đưa bản thân về khoảnh khắc hiện tại bằng các giác quan.',
    duration: '3 phút',
    steps: [
      '👀 Nhìn: kể tên 5 thứ bạn đang thấy',
      '🖐 Chạm: 4 thứ bạn đang cảm nhận được',
      '👂 Nghe: 3 âm thanh bạn đang nghe',
      '👃 Ngửi: 2 mùi bạn nhận ra',
      '👅 Nếm: 1 vị trong miệng bạn',
    ],
  },
  {
    id: 'body_scan',
    title: 'Body Scan',
    emoji: '🧘',
    description: 'Thả lỏng từng vùng cơ thể, giải phóng căng thẳng tích tụ.',
    duration: '5 phút',
    steps: [
      'Nằm hoặc ngồi thoải mái, nhắm mắt và hít thở sâu',
      'Chú ý đến đôi bàn chân — thả lỏng các ngón chân',
      'Di chuyển lên bắp chân, đùi — buông lơi cơ bắp',
      'Thả lỏng bụng, ngực, và vai',
      'Cuối cùng, buông lơi cơ mặt và đầu. Hít thở sâu thêm lần nữa.',
    ],
  },
]

export function ExercisesPage() {
  const navigate = useNavigate()
  const [activeId, setActiveId] = useState<string | null>(null)
  const [stepIdx, setStepIdx] = useState(0)

  const exercise = EXERCISES.find(e => e.id === activeId) ?? null

  const startExercise = (id: string) => {
    setActiveId(id)
    setStepIdx(0)
  }

  const exitExercise = () => {
    setActiveId(null)
    setStepIdx(0)
  }

  if (exercise) {
    const isDone = stepIdx >= exercise.steps.length
    return (
      <div className="min-h-screen bg-[var(--color-lua-bg)] px-5 pt-10 pb-28 flex flex-col">
        <button
          type="button"
          onClick={exitExercise}
          className="text-sm text-[var(--color-serene-muted)] mb-6 text-left w-fit hover:text-[var(--color-serene-ink)] transition"
        >
          ← Quay lại
        </button>

        <div className="text-4xl text-center mb-2" aria-hidden="true">{exercise.emoji}</div>
        <h1 className="font-[var(--font-display)] text-2xl text-[var(--color-serene-ink)] text-center mb-8">
          {exercise.title}
        </h1>

        <AnimatePresence mode="wait">
          {!isDone ? (
            <motion.div
              key={stepIdx}
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex-1 flex flex-col justify-center"
            >
              <div className="bg-white rounded-3xl p-8 shadow-sm text-center mb-8">
                <p className="text-[10px] text-[var(--color-serene-muted)] mb-3 uppercase tracking-widest">
                  Bước {stepIdx + 1} / {exercise.steps.length}
                </p>
                <p className="font-[var(--font-display)] text-xl text-[var(--color-serene-ink)] leading-snug">
                  {exercise.steps[stepIdx]}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setStepIdx(i => i + 1)}
                className="w-full py-4 rounded-2xl font-semibold text-sm text-white transition-all active:scale-[0.97]"
                style={{ backgroundColor: 'var(--color-lua)' }}
              >
                {stepIdx < exercise.steps.length - 1 ? 'Tiếp →' : 'Hoàn thành ✓'}
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="done"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex-1 flex flex-col justify-center items-center text-center"
            >
              <div className="text-6xl mb-4" aria-hidden="true">🌟</div>
              <h2 className="font-[var(--font-display)] text-2xl text-[var(--color-serene-ink)] mb-3">
                Tốt lắm!
              </h2>
              <p className="text-[var(--color-serene-muted)] mb-10 text-sm">
                Bạn vừa hoàn thành {exercise.title}.
              </p>
              <div className="flex flex-col gap-3 w-full max-w-xs">
                <button
                  type="button"
                  onClick={exitExercise}
                  className="bg-[var(--color-serene-primary)] text-[var(--color-serene-on-primary)] px-8 py-3.5 rounded-2xl font-semibold text-sm"
                >
                  Thử bài khác
                </button>
                <button
                  type="button"
                  onClick={() => navigate(ROUTE_PATHS.home)}
                  className="bg-[var(--color-serene-surface)] text-[var(--color-serene-ink)] py-3.5 rounded-2xl font-medium text-sm"
                >
                  Về trang chính
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[var(--color-lua-bg)] px-5 pt-10 pb-28">
      <p className="text-[10px] uppercase tracking-widest text-[var(--color-serene-muted)] mb-1">Lửa</p>
      <h1 className="font-[var(--font-display)] text-3xl text-[var(--color-serene-ink)] mb-2">Bài tập ngắn</h1>
      <p className="text-sm text-[var(--color-serene-muted)] mb-8">Thở · Grounding · Body scan</p>
      <div className="flex flex-col gap-4">
        {EXERCISES.map((ex, i) => (
          <motion.button
            key={ex.id}
            type="button"
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            onClick={() => startExercise(ex.id)}
            className="bg-white rounded-3xl p-5 text-left shadow-sm hover:shadow-md active:scale-[0.98] transition-all"
          >
            <div className="flex items-center gap-3 mb-2">
              <span className="text-3xl" aria-hidden="true">{ex.emoji}</span>
              <div>
                <div className="font-semibold text-[var(--color-serene-ink)]">{ex.title}</div>
                <div className="text-xs text-[var(--color-serene-muted)]">{ex.duration} · {ex.steps.length} bước</div>
              </div>
            </div>
            <p className="text-sm text-[var(--color-serene-muted)]">{ex.description}</p>
          </motion.button>
        ))}
      </div>
    </div>
  )
}
