import { httpClient } from '../api/httpClient'

export type BambooMessage = {
  id: string
  content: string
  anonymous_name: string
  received_at: string
  status?: string
  reply_to_message_id?: string | null
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
  status?: string
  reply_to_message_id?: string | null
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

export type BambooInboxSummary = {
  id: string
  display_name: string
  last_message_preview: string
  last_message_at: string
  last_direction: 'sent' | 'received'
  unread_count: number
  message_count: number
}

export type BambooInboxThreadMessage = {
  id: string
  content: string
  anonymous_name: string
  sent_at: string
  status?: string
  direction: 'sent' | 'received'
  reply_to_message_id?: string | null
  topic?: string | null
  tone?: string | null
  reply_count?: number
  pass_count?: number
}

export type BambooInboxesResponse = {
  inboxes: BambooInboxSummary[]
  total: number
  has_more?: boolean
}

export type BambooInboxMessagesResponse = {
  inbox: {
    id: string
    display_name: string
  }
  messages: BambooInboxThreadMessage[]
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
    status: typeof message.status === 'string' ? message.status : 'approved',
    reply_to_message_id: (message.reply_to_message_id as string | null | undefined) ?? null,
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
    status: typeof letter.status === 'string' ? letter.status : undefined,
    reply_to_message_id: (letter.reply_to_message_id as string | null | undefined) ?? null,
    timestamp: String(letter.created_at ?? letter.timestamp ?? new Date().toISOString()),
    pass_count: typeof letter.pass_count === 'number' ? letter.pass_count : 0,
    reply_count: typeof letter.reply_count === 'number' ? letter.reply_count : 0,
    topic: (letter.topic as string | null | undefined) ?? null,
    tone: (letter.tone as string | null | undefined) ?? null,
  }
}

function normalizeInboxSummary(inbox: Record<string, unknown>): BambooInboxSummary {
  return {
    id: String(inbox.inbox_id ?? inbox.id ?? `inbox_${Date.now()}`),
    display_name: String(inbox.display_name ?? 'Người dùng ẩn danh'),
    last_message_preview: String(inbox.last_message_preview ?? ''),
    last_message_at: String(inbox.last_message_at ?? new Date().toISOString()),
    last_direction: String(inbox.last_direction ?? 'received') === 'sent' ? 'sent' : 'received',
    unread_count: typeof inbox.unread_count === 'number' ? inbox.unread_count : 0,
    message_count: typeof inbox.message_count === 'number' ? inbox.message_count : 0,
  }
}

function normalizeInboxThreadMessage(message: Record<string, unknown>): BambooInboxThreadMessage {
  return {
    id: String(message.message_id ?? message.id ?? `msg_${Date.now()}`),
    content: String(message.content ?? ''),
    anonymous_name: String(message.anonymous_name ?? 'Một người vô danh'),
    sent_at: String(message.sent_at ?? message.received_at ?? new Date().toISOString()),
    status: typeof message.status === 'string' ? message.status : 'approved',
    direction: String(message.direction ?? 'received') === 'sent' ? 'sent' : 'received',
    reply_to_message_id: (message.reply_to_message_id as string | null | undefined) ?? null,
    topic: (message.topic as string | null | undefined) ?? null,
    tone: (message.tone as string | null | undefined) ?? null,
    reply_count: typeof message.reply_count === 'number' ? message.reply_count : 0,
    pass_count: typeof message.pass_count === 'number' ? message.pass_count : 0,
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
      status: res.status ?? 'pending',
      reply_to_message_id: null,
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

  async getInboxes(): Promise<BambooInboxesResponse> {
    const data = await httpClient.get<{ inboxes: Record<string, unknown>[]; total: number; has_more?: boolean }>('/bamboo/inboxes')
    return {
      inboxes: data.inboxes.map(normalizeInboxSummary),
      total: data.total,
      has_more: data.has_more,
    }
  },

  async getInboxMessages(inboxId: string): Promise<BambooInboxMessagesResponse> {
    const data = await httpClient.get<{
      inbox: { inbox_id?: string; id?: string; display_name?: string }
      messages: Record<string, unknown>[]
      total: number
      has_more?: boolean
    }>(`/bamboo/inboxes/${encodeURIComponent(inboxId)}/messages`)
    return {
      inbox: {
        id: String(data.inbox.inbox_id ?? data.inbox.id ?? inboxId),
        display_name: String(data.inbox.display_name ?? 'Người dùng ẩn danh'),
      },
      messages: data.messages.map(normalizeInboxThreadMessage),
      total: data.total,
      has_more: data.has_more,
    }
  },

  async reply(messageId: string, content: string): Promise<void> {
    await httpClient.postWithCsrf('/bamboo/reply', { message_id: messageId, content })
  },

  async sendToInbox(inboxId: string, payload: SendBambooPayload): Promise<SendBambooResponse> {
    const res = await httpClient.postWithCsrf<SendBambooResponse>(`/bamboo/inboxes/${encodeURIComponent(inboxId)}/messages`, payload)
    return res
  },

  async passItOn(messageId: string): Promise<void> {
    await httpClient.postWithCsrf('/bamboo/pass', { message_id: messageId })
  },

  async getStorage(): Promise<BambooStorageResponse> {
    const data = await httpClient.get<{ letters: Record<string, unknown>[] }>('/bamboo/storage')
    return { letters: data.letters.map(normalizeStorageLetter) }
  },
}
