import { formatRelativeTime, getUi } from './shared'
import type { ReplyArchiveItem, SentLetterItem } from '../../../services/anonymousShareService'
import Loading from '../../ui/Loading'

export function BeachMessageCommunityPanel({
    dark,
    loadingSent,
    sentLetters,
    replyLetters,
    onOpenSentLetter,
    onOpenReplyLetter,
}: {
    dark?: boolean
    loadingSent: boolean
    sentLetters: SentLetterItem[]
    replyLetters: ReplyArchiveItem[]
    onOpenSentLetter: (item: SentLetterItem) => void
    onOpenReplyLetter: (item: ReplyArchiveItem) => void
}) {
    const isDark = Boolean(dark)
    const ui = getUi(isDark)

    return (
        <div className="relative z-10 max-w-2xl mx-auto px-6 py-16 pb-24" style={{ animation: 'fadeUp 0.8s ease both' }}>
            <div className="mb-10">
                <h2
                    className={`${ui.textPrimary} font-display text-4xl italic font-normal`}
                    style={{ textShadow: isDark ? '0 2px 16px rgba(0,0,0,0.36)' : '0 2px 10px rgba(255,255,255,0.35)' }}
                >
                    Kho thư cá nhân
                </h2>
            </div>

            <div className={`${ui.glassLight} border rounded-2xl p-4 mb-8`}>
                <div className="flex items-center justify-between mb-3">
                    <h3 className={`${ui.textSubtle} font-display text-xl font-semibold`}>Thư bạn đã gửi</h3>
                </div>

                {sentLetters.length > 0 ? (
                    <div className="grid grid-cols-1 gap-3">
                        {sentLetters.map((item) => (
                            <button
                                key={item.id}
                                type="button"
                                onClick={() => onOpenSentLetter(item)}
                                className="text-left rounded-xl border px-4 py-3 transition-all"
                                style={{ borderColor: isDark ? 'rgba(242,235,224,0.2)' : 'rgba(18,30,40,0.18)' }}
                            >
                                <div className="flex items-start justify-between gap-3 mb-1">
                                    <p className={`${ui.textSubtle} font-display text-base font-semibold`}>Thư của bạn</p>
                                    <p className={`${ui.textSubtler} text-xs`}>{formatRelativeTime(item.sent_at)}</p>
                                </div>
                                <p className={`${ui.textSubtler} text-sm line-clamp-1 mb-1`}>{item.content}</p>
                                <p className={`${ui.textSubtler} text-xs uppercase tracking-wider`}>
                                    {item.reply
                                        ? `${item.reply.anonymous_name ? `Ẩn danh: ${item.reply.anonymous_name}` : 'Có hồi âm'}${item.reply.has_reaction ? ` · Đã được thả ${item.reply.reaction_type ?? 'cảm xúc'}` : ' · Chưa được thả cảm xúc'}`
                                        : 'Đang chờ hồi âm'}
                                </p>
                            </button>
                        ))}
                    </div>
                ) : loadingSent ? <Loading /> : (
                    <p className={`${ui.textSubtler} text-sm`}>Bạn chưa gửi thư nào.</p>
                )}
            </div>

            <div className={`${ui.glassLight} border rounded-2xl p-4`}>
                <div className="flex items-center justify-between mb-3">
                    <h3 className={`${ui.textSubtle} font-display text-xl font-semibold`}>Thư bạn đã phản hồi</h3>
                </div>

                {replyLetters.length > 0 ? (
                    <div className="grid grid-cols-1 gap-3">
                        {replyLetters.map((item) => (
                            <button
                                key={item.reply_id}
                                type="button"
                                onClick={() => onOpenReplyLetter(item)}
                                className="text-left rounded-xl border px-4 py-3"
                                style={{ borderColor: isDark ? 'rgba(242,235,224,0.2)' : 'rgba(18,30,40,0.18)' }}
                            >
                                <div className="flex items-start justify-between gap-3 mb-1">
                                    <p className={`${ui.textSubtle} font-display text-base font-semibold`}>Phản hồi của bạn</p>
                                    <p className={`${ui.textSubtler} text-xs`}>{formatRelativeTime(item.sent_at)}</p>
                                </div>
                                <p className={`${ui.textSubtler} text-xs mb-2`}>
                                    {item.anonymous_name ? `Ẩn danh: ${item.anonymous_name}` : 'Ẩn danh'}
                                    {item.has_reaction ? ` · Đã được thả ${item.reaction_type ?? 'cảm xúc'}` : ' · Chưa được thả cảm xúc'}
                                </p>
                                <p className={`${ui.textSubtler} text-sm line-clamp-2 mb-2`}>{item.content}</p>
                                {item.original_content ? (
                                    <p className={`${ui.textSubtler} text-xs italic line-clamp-2`}>Trả lời cho: {item.original_content}</p>
                                ) : null}
                            </button>
                        ))}
                    </div>
                ) : loadingSent ? <Loading /> : (
                    <p className={`${ui.textSubtler} text-sm`}>Bạn chưa phản hồi thư nào.</p>
                )}
            </div>
        </div>
    )
}
