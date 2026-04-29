import { httpClient } from '../api/httpClient'

export type BambooCategory = 'encouragement' | 'sharing' | 'question'

export type BambooMessage = {
  id: string
  content: string
  anonymous_name: string
  received_at: string
  topic?: string | null
  tone?: string | null
  reply_count?: number
  pass_count?: number
}

export type StoredLetter = {
  id: string
  content: string
  anonymous_name?: string
  direction: 'sent' | 'received'
  timestamp: string
  pass_count?: number
  reply_count?: number
  topic?: string | null
  tone?: string | null
}

export type SendBambooPayload = {
  content: string
  topic?: string
  tone?: string
}

export type SendBambooResponse = {
  message_id: string
  status?: string
  sent_at: string
  moderation_mode?: string
  anonymous_name?: string
}

export type BambooInboxResponse = {
  messages: BambooMessage[]
  total: number
  has_more?: boolean
}

export type BambooStorageResponse = {
  letters: StoredLetter[]
}

// ── Mock inbox ─────────────────────────────────────────────────────────────────
const MOCK_MESSAGES: BambooMessage[] = [
  {
    id: 'mock_1',
    content: 'Bạn đang làm rất tốt rồi. Dù hôm nay khó khăn thế nào, chỉ cần tiếp tục hiện diện là đủ.',
    anonymous_name: 'Một người vô danh',
    received_at: new Date(Date.now() - 1000 * 60 * 47).toISOString(),
  },
  {
    id: 'mock_2',
    content: 'Hôm nay mình cũng cảm thấy mệt. Nhưng nhìn lại, mỗi ngày mình đều vượt qua được. Bạn cũng sẽ làm được.',
    anonymous_name: 'Người lữ hành',
    received_at: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
  },
  {
    id: 'mock_3',
    content: 'Có ai thấy việc ngồi một mình với cảm xúc của mình vừa đáng sợ vừa cần thiết không? Mình đang học cách làm điều đó.',
    anonymous_name: 'Ẩn danh từ biển',
    received_at: new Date(Date.now() - 1000 * 60 * 60 * 11).toISOString(),
  },
]

const DAILY_MESSAGE_POOL: Array<{ content: string; category: BambooCategory }> = [
  { content: 'Bạn không cần hoàn hảo để xứng đáng được yêu thương. Chỉ cần là chính mình hôm nay.', category: 'encouragement' },
  { content: 'Mình vừa có một ngày chậm lại, không hiệu quả lắm, nhưng mình thấy lòng nhẹ hơn.', category: 'sharing' },
  { content: 'Có ai có cách để ngủ ngon hơn khi đầu óc cứ suy nghĩ liên tục không?', category: 'question' },
  { content: 'Nếu hôm nay mệt, bạn có thể nghỉ. Nghỉ ngơi cũng là một cách tiến lên.', category: 'encouragement' },
  { content: 'Mình đang học cách nói “không” mà không thấy tội lỗi. Khó nhưng đáng.', category: 'sharing' },
  { content: 'Khi thấy lạc lõng, bạn thường làm gì để quay về với bản thân?', category: 'question' },
  { content: 'Chỉ muốn nhắc bạn rằng: bạn đã đi qua rất nhiều điều khó khăn rồi.', category: 'encouragement' },
  { content: 'Hôm nay mình thử viết ra cảm xúc thay vì kìm nén. Kết quả ổn hơn mình nghĩ.', category: 'sharing' },
]

const SENT_KEY = 'serene_bamboo_sent'
const SENT_FULL_KEY = 'serene_bamboo_sent_full'
const LOCAL_INBOX_KEY = 'serene_bamboo_inbox'
const DAILY_INBOX_DAY_KEY = 'serene_bamboo_inbox_day'

/**
 * Set VITE_BAMBOO_API=true in .env when the backend implements /bamboo/* endpoints.
 * Until then all calls short-circuit to local fallback — no 404 noise in the console.
 */
const BAMBOO_API_ENABLED = import.meta.env.VITE_BAMBOO_API !== 'false'

function normalizeInboxMessage(message: Record<string, unknown>): BambooMessage {
  return {
    id: String(message.message_id ?? message.id ?? `msg_${Date.now()}`),
    content: String(message.content ?? ''),
    anonymous_name: String(message.anonymous_name ?? 'Một người vô danh'),
    received_at: String(message.received_at ?? message.sent_at ?? new Date().toISOString()),
    topic: (message.topic as string | null | undefined) ?? null,
    tone: (message.tone as string | null | undefined) ?? null,
    reply_count: typeof message.reply_count === 'number' ? message.reply_count : 0,
    pass_count: typeof message.pass_count === 'number' ? message.pass_count : 0,
  }
}

function normalizeStorageLetter(letter: Record<string, unknown>): StoredLetter {
  return {
    id: String(letter.message_id ?? letter.id ?? `msg_${Date.now()}`),
    content: String(letter.content ?? ''),
    anonymous_name: letter.anonymous_name ? String(letter.anonymous_name) : undefined,
    direction: String(letter.direction ?? 'received') === 'sent' ? 'sent' : 'received',
    timestamp: String(letter.created_at ?? letter.timestamp ?? new Date().toISOString()),
    pass_count: typeof letter.pass_count === 'number' ? letter.pass_count : 0,
    reply_count: typeof letter.reply_count === 'number' ? letter.reply_count : 0,
    topic: (letter.topic as string | null | undefined) ?? null,
    tone: (letter.tone as string | null | undefined) ?? null,
  }
}

function loadSentFull(): StoredLetter[] {
  try {
    return JSON.parse(localStorage.getItem(SENT_FULL_KEY) ?? '[]') as StoredLetter[]
  } catch {
    return []
  }
}

function saveSentFull(letter: StoredLetter) {
  const prev = loadSentFull()
  try {
    localStorage.setItem(SENT_FULL_KEY, JSON.stringify([letter, ...prev].slice(0, 50)))
  } catch {
    // ignore storage errors
  }
}

function loadLocalSent(): string[] {
  try {
    return JSON.parse(localStorage.getItem(SENT_KEY) ?? '[]') as string[]
  } catch {
    return []
  }
}

function saveSentLocally(content: string) {
  const prev = loadLocalSent()
  try {
    localStorage.setItem(SENT_KEY, JSON.stringify([...prev, content]))
  } catch {
    // ignore storage errors
  }
}

function getTodayKey(): string {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function pickRandomMessages(): BambooMessage[] {
  const count = 2 + Math.floor(Math.random() * 4) // 2..5 messages/day
  const shuffled = [...DAILY_MESSAGE_POOL].sort(() => Math.random() - 0.5)
  const picked = shuffled.slice(0, count)
  const now = Date.now()
  return picked.map((item, index) => ({
    id: `daily_${getTodayKey()}_${index}`,
    content: item.content,
    anonymous_name: 'Một người vô danh',
    received_at: new Date(now - (index + 1) * 1000 * 60 * 43).toISOString(),
  }))
}

function ensureDailyInbox(): BambooMessage[] {
  const today = getTodayKey()
  const storedDay = localStorage.getItem(DAILY_INBOX_DAY_KEY)
  const hasToday = storedDay === today

  if (hasToday) {
    try {
      const saved = JSON.parse(localStorage.getItem(LOCAL_INBOX_KEY) ?? '[]') as BambooMessage[]
      if (Array.isArray(saved) && saved.length > 0) {
        return saved
      }
    } catch {
      // regenerate if malformed
    }
  }

  const generated = [...pickRandomMessages(), ...MOCK_MESSAGES].slice(0, 20)
  try {
    localStorage.setItem(LOCAL_INBOX_KEY, JSON.stringify(generated))
    localStorage.setItem(DAILY_INBOX_DAY_KEY, today)
  } catch {
    // ignore storage errors
  }
  return generated
}

export const anonymousShareService = {
  async send(payload: SendBambooPayload): Promise<SendBambooResponse> {
    if (!BAMBOO_API_ENABLED) {
      saveSentLocally(payload.content)
      const sentAt = new Date().toISOString()
      const messageId = `local_${Date.now()}`
      saveSentFull({
        id: messageId,
        content: payload.content,
        anonymous_name: 'Một người vô danh',
        direction: 'sent',
        timestamp: sentAt,
        pass_count: 0,
      })
      return { message_id: messageId, sent_at: sentAt, status: 'pending', anonymous_name: 'Một người vô danh', moderation_mode: 'local' }
    }
    try {
      const res = await httpClient.postWithCsrf<SendBambooResponse>('/bamboo/send', payload)
      saveSentFull({
        id: res.message_id,
        content: payload.content,
        anonymous_name: res.anonymous_name ?? 'Một người vô danh',
        direction: 'sent',
        timestamp: res.sent_at,
        pass_count: 0,
      })
      return res
    } catch {
      saveSentLocally(payload.content)
      const sentAt = new Date().toISOString()
      const messageId = `local_${Date.now()}`
      saveSentFull({
        id: messageId,
        content: payload.content,
        anonymous_name: 'Một người vô danh',
        direction: 'sent',
        timestamp: sentAt,
        pass_count: 0,
      })
      return { message_id: messageId, sent_at: sentAt, status: 'pending', anonymous_name: 'Một người vô danh', moderation_mode: 'fallback' }
    }
  },

  async getInbox(): Promise<BambooInboxResponse> {
    const localFallback = (): BambooInboxResponse => {
      const dailyMessages = ensureDailyInbox()
      return { messages: dailyMessages, total: dailyMessages.length }
    }

    if (!BAMBOO_API_ENABLED) return localFallback()

    try {
      const data = await httpClient.get<{ messages: Record<string, unknown>[]; total: number; has_more?: boolean }>('/bamboo/inbox')
      return {
        messages: data.messages.map(normalizeInboxMessage),
        total: data.total,
        has_more: data.has_more,
      }
    } catch {
      return localFallback()
    }
  },

  async reply(messageId: string, content: string): Promise<void> {
    if (!BAMBOO_API_ENABLED) {
      saveSentFull({
        id: `reply_${Date.now()}`,
        content,
        anonymous_name: 'Một người vô danh',
        direction: 'sent',
        timestamp: new Date().toISOString(),
        pass_count: 0,
      })
      return
    }
    try {
      await httpClient.postWithCsrf('/bamboo/reply', { message_id: messageId, content })
    } catch {
      // fallback: store locally
      saveSentFull({
        id: `reply_${Date.now()}`,
        content,
        anonymous_name: 'Một người vô danh',
        direction: 'sent',
        timestamp: new Date().toISOString(),
        pass_count: 0,
      })
    }
  },

  async passItOn(messageId: string): Promise<void> {
    if (!BAMBOO_API_ENABLED) return
    try {
      await httpClient.postWithCsrf('/bamboo/pass', { message_id: messageId })
    } catch {
      // ignore — pass-it-on is best-effort
    }
  },

  async getStorage(): Promise<BambooStorageResponse> {
    if (!BAMBOO_API_ENABLED) {
      const sent = loadSentFull()
      const received: StoredLetter[] = MOCK_MESSAGES.map((m) => ({
        id: m.id,
        content: m.content,
        anonymous_name: m.anonymous_name,
        direction: 'received',
        timestamp: m.received_at,
      }))
      const combined = [...sent, ...received].sort(
        (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      )
      return { letters: combined }
    }
    try {
      const data = await httpClient.get<{ letters: Record<string, unknown>[] }>('/bamboo/storage')
      return { letters: data.letters.map(normalizeStorageLetter) }
    } catch {
      return { letters: loadSentFull() }
    }
  },
}
