import { httpClient } from '../api/httpClient'

export type LetterInboxItem = {
  id: string
  content: string
  sender_id: string
  received_at: string
  forward_count: number
  has_reply: boolean
  is_reported: boolean
  status?: string
  reply?: InboxLetterReply | null
}

export type InboxLetterReply = {
  reply_id: string
  content: string
  anonymous_name?: string | null
  replier_id: string
  received_at: string
  reaction_type?: string | null
  has_reaction?: boolean
}

export type SentLetterReply = {
  reply_id: string
  content: string
  anonymous_name?: string | null
  replier_id: string
  received_at: string
  reaction_type?: string | null
  has_reaction?: boolean
}

export type SentLetterItem = {
  id: string
  content: string
  sent_at: string
  forward_count: number
  has_reply: boolean
  is_reported: boolean
  reply?: SentLetterReply | null
}

export type ReplyArchiveItem = {
  reply_id: string
  content: string
  anonymous_name?: string | null
  original_content?: string | null
  sent_at: string
  reaction_type?: string | null
  has_reaction?: boolean
}

export type SendLetterPayload = {
  content: string
}

export type SendLetterResponse = {
  letter_id: string
  receiver_id: string
  forward_count: number
  has_reply: boolean
  is_reported: boolean
}

export type ReportCategory = 'spam' | 'abuse' | 'inappropriate' | 'self_harm' | 'other'

export type LetterInboxResponse = {
  letters: LetterInboxItem[]
  total: number
  has_more?: boolean
}

export type SentLettersResponse = {
  letters: SentLetterItem[]
  reply_letters?: ReplyArchiveItem[]
  total: number
  has_more?: boolean
}

function normalizeInboxLetter(letter: Record<string, unknown>): LetterInboxItem {
  return {
    id: String(letter.letter_id ?? letter.id ?? `let_${Date.now()}`),
    content: String(letter.content ?? ''),
    sender_id: String(letter.sender_id ?? ''),
    received_at: String(letter.received_at ?? new Date().toISOString()),
    forward_count: typeof letter.forward_count === 'number' ? letter.forward_count : 0,
    has_reply: Boolean(letter.has_reply),
    is_reported: Boolean(letter.is_reported),
    status: typeof letter.status === 'string' ? letter.status : undefined,
    reply:
      letter.reply && typeof letter.reply === 'object'
        ? normalizeInboxReply(letter.reply as Record<string, unknown>)
        : null,
  }
}

function normalizeInboxReply(reply: Record<string, unknown>): InboxLetterReply {
  return {
    reply_id: String(reply.reply_id ?? `rep_${Date.now()}`),
    content: String(reply.content ?? ''),
    anonymous_name: typeof reply.anonymous_name === 'string' ? reply.anonymous_name : null,
    replier_id: String(reply.replier_id ?? ''),
    received_at: String(reply.received_at ?? new Date().toISOString()),
    reaction_type: typeof reply.reaction_type === 'string' ? reply.reaction_type : null,
    has_reaction: Boolean(reply.has_reaction),
  }
}

function normalizeSentReply(reply: Record<string, unknown>): SentLetterReply {
  return {
    reply_id: String(reply.reply_id ?? `rep_${Date.now()}`),
    content: String(reply.content ?? ''),
    anonymous_name: typeof reply.anonymous_name === 'string' ? reply.anonymous_name : null,
    replier_id: String(reply.replier_id ?? ''),
    received_at: String(reply.received_at ?? new Date().toISOString()),
    reaction_type: typeof reply.reaction_type === 'string' ? reply.reaction_type : null,
    has_reaction: Boolean(reply.has_reaction),
  }
}

function normalizeSentLetter(letter: Record<string, unknown>): SentLetterItem {
  return {
    id: String(letter.letter_id ?? letter.id ?? `let_${Date.now()}`),
    content: String(letter.content ?? ''),
    sent_at: String(letter.sent_at ?? new Date().toISOString()),
    forward_count: typeof letter.forward_count === 'number' ? letter.forward_count : 0,
    has_reply: Boolean(letter.has_reply),
    is_reported: Boolean(letter.is_reported),
    reply:
      letter.reply && typeof letter.reply === 'object'
        ? normalizeSentReply(letter.reply as Record<string, unknown>)
        : null,
  }
}

function normalizeReplyArchiveItem(reply: Record<string, unknown>): ReplyArchiveItem {
  return {
    reply_id: String(reply.reply_id ?? `rep_${Date.now()}`),
    content: String(reply.content ?? ''),
    anonymous_name: typeof reply.anonymous_name === 'string' ? reply.anonymous_name : null,
    original_content: typeof reply.original_content === 'string' ? reply.original_content : null,
    sent_at: String(reply.sent_at ?? new Date().toISOString()),
    reaction_type: typeof reply.reaction_type === 'string' ? reply.reaction_type : null,
    has_reaction: Boolean(reply.has_reaction),
  }
}

export const anonymousShareService = {
  async send(payload: SendLetterPayload): Promise<SendLetterResponse> {
    return httpClient.postWithCsrf<SendLetterResponse>('/letters', payload)
  },

  async getInbox(): Promise<LetterInboxResponse> {
    const data = await httpClient.get<{ letters: Record<string, unknown>[]; total: number; has_more?: boolean }>(
      '/letters/inbox',
    )
    return {
      letters: data.letters.map(normalizeInboxLetter),
      total: data.total,
      has_more: data.has_more,
    }
  },

  async reply(letterId: string, content: string): Promise<{ reply_id: string }> {
    return httpClient.postWithCsrf<{ reply_id: string }>(`/letters/${encodeURIComponent(letterId)}/reply`, {
      content,
    })
  },

  async passItOn(letterId: string): Promise<void> {
    await httpClient.postWithCsrf(`/letters/${encodeURIComponent(letterId)}/forward`)
  },

  async getSentLetters(): Promise<SentLettersResponse> {
    const data = await httpClient.get<{ letters: Record<string, unknown>[]; total: number; has_more?: boolean }>(
      '/letters/sent',
    )
    return {
      letters: data.letters.map(normalizeSentLetter),
      reply_letters: Array.isArray((data as Record<string, unknown>).reply_letters)
        ? ((data as Record<string, unknown>).reply_letters as Record<string, unknown>[]).map(normalizeReplyArchiveItem)
        : [],
      total: data.total,
      has_more: data.has_more,
    }
  },

  async reactToReply(replyId: string, reactionType = 'heart'): Promise<void> {
    await httpClient.postWithCsrf(`/replies/${encodeURIComponent(replyId)}/react`, {
      reaction_type: reactionType,
    })
  },

  async reportLetter(
    letterId: string,
    reportCategory: ReportCategory,
    reason?: string,
    description?: string,
  ): Promise<void> {
    await httpClient.postWithCsrf('/reports', {
      letter_id: letterId,
      report_category: reportCategory,
      reason,
      description,
    })
  },
}
