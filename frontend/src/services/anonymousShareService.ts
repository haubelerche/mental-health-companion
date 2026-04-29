import { httpClient } from '../api/httpClient'

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

const SENT_FULL_KEY = 'serene_bamboo_sent_full'

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

export const anonymousShareService = {
  async send(payload: SendBambooPayload): Promise<SendBambooResponse> {
    const res = await httpClient.postWithCsrf<SendBambooResponse>('/bamboo/send', payload)
    saveSentFull({
      id: res.message_id,
      content: payload.content,
      anonymous_name: res.anonymous_name ?? 'Một người vô danh',
      direction: 'sent',
      timestamp: res.sent_at,
      pass_count: 0,
      topic: payload.topic ?? null,
      tone: payload.tone ?? null,
    })
    return res
  },

  async getInbox(): Promise<BambooInboxResponse> {
    const data = await httpClient.get<{ messages: Record<string, unknown>[]; total: number; has_more?: boolean }>('/bamboo/inbox')
    return {
      messages: data.messages.map(normalizeInboxMessage),
      total: data.total,
      has_more: data.has_more,
    }
  },

  async reply(messageId: string, content: string): Promise<void> {
    await httpClient.postWithCsrf('/bamboo/reply', { message_id: messageId, content })
  },

  async passItOn(messageId: string): Promise<void> {
    await httpClient.postWithCsrf('/bamboo/pass', { message_id: messageId })
  },

  async getStorage(): Promise<BambooStorageResponse> {
    const data = await httpClient.get<{ letters: Record<string, unknown>[] }>('/bamboo/storage')
    return { letters: data.letters.map(normalizeStorageLetter) }
  },
}
