import { httpClient } from '../api/httpClient'

export type BambooCategory = 'encouragement' | 'sharing' | 'question'

export type BambooMessage = {
  id: string
  content: string
  category: BambooCategory
  received_at: string
}

export type SendBambooPayload = {
  content: string
  category: BambooCategory
}

export type SendBambooResponse = {
  message_id: string
  sent_at: string
}

export type BambooInboxResponse = {
  messages: BambooMessage[]
  total: number
}

// ── Mock inbox for offline/fallback ──────────────────────────────────────────
const MOCK_MESSAGES: BambooMessage[] = [
  {
    id: 'mock_1',
    content: 'Bạn đang làm rất tốt rồi. Dù hôm nay khó khăn thế nào, chỉ cần tiếp tục hiện diện là đủ.',
    category: 'encouragement',
    received_at: new Date(Date.now() - 1000 * 60 * 47).toISOString(),
  },
  {
    id: 'mock_2',
    content: 'Hôm nay mình cũng cảm thấy mệt. Nhưng nhìn lại, mỗi ngày mình đều vượt qua được. Bạn cũng sẽ làm được.',
    category: 'sharing',
    received_at: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
  },
  {
    id: 'mock_3',
    content: 'Có ai thấy việc ngồi một mình với cảm xúc của mình vừa đáng sợ vừa cần thiết không? Mình đang học cách làm điều đó.',
    category: 'question',
    received_at: new Date(Date.now() - 1000 * 60 * 60 * 11).toISOString(),
  },
]

const SENT_KEY = 'serene_bamboo_sent'
const LOCAL_INBOX_KEY = 'serene_bamboo_inbox'

/**
 * Set VITE_BAMBOO_API=true in .env when the backend implements /bamboo/* endpoints.
 * Until then all calls short-circuit to local fallback — no 404 noise in the console.
 */
const BAMBOO_API_ENABLED = import.meta.env.VITE_BAMBOO_API === 'true'

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

export const anonymousShareService = {
  /**
   * Send an anonymous message to a random user.
   * Falls back to local-only storage if backend is unavailable.
   */
  async send(payload: SendBambooPayload): Promise<SendBambooResponse> {
    if (!BAMBOO_API_ENABLED) {
      saveSentLocally(payload.content)
      return { message_id: `local_${Date.now()}`, sent_at: new Date().toISOString() }
    }
    try {
      return await httpClient.postWithCsrf<SendBambooResponse>('/bamboo/send', payload)
    } catch {
      saveSentLocally(payload.content)
      return { message_id: `local_${Date.now()}`, sent_at: new Date().toISOString() }
    }
  },

  /**
   * Fetch anonymous messages received by the current user.
   * Falls back to mock messages when backend is unavailable.
   */
  async getInbox(): Promise<BambooInboxResponse> {
    const localFallback = (): BambooInboxResponse => {
      const cached = (() => {
        try {
          return JSON.parse(localStorage.getItem(LOCAL_INBOX_KEY) ?? '[]') as BambooMessage[]
        } catch {
          return []
        }
      })()
      const combined = [...cached, ...MOCK_MESSAGES].slice(0, 20)
      return { messages: combined, total: combined.length }
    }

    if (!BAMBOO_API_ENABLED) return localFallback()

    try {
      return await httpClient.get<BambooInboxResponse>('/bamboo/inbox')
    } catch {
      return localFallback()
    }
  },
}
