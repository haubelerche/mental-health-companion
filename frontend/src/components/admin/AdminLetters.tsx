/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { adminService } from '../../services/adminService'
import { ApiRequestError } from '../../api/types'
import { toast } from 'react-toastify'
import { Shield, Clock, User, AlertTriangle, Brain, ChevronLeft, ChevronRight, Loader2, Sparkles, Activity, Send, X, MessageSquare, Inbox, Bot, UserCheck } from 'lucide-react'

type RepliedByFilter = 'all' | 'none' | 'ai' | 'human' | 'reported'

export default function AdminLetters() {
    // const cached = adminCache.getLetters()
    const [filter, setFilter] = useState<RepliedByFilter>('none')
    const [letters, setLetters] = useState<any[]>([])
    const [total, setTotal] = useState(0)
    const [page, setPage] = useState(0)
    const limit = 12

    const [loading, setLoading] = useState(false)
    const [analyzingId, setAnalyzingId] = useState<string | null>(null)
    const [suggestingId, setSuggestingId] = useState<string | null>(null)
    const [aiResults, setAiResults] = useState<Record<string, any>>({})
    const [aiSuggestions, setAiSuggestions] = useState<Record<string, any[]>>({})
    const [replyDrafts, setReplyDrafts] = useState<Record<string, string>>({})
    const [isReplying, setIsReplying] = useState<Record<string, boolean>>({})
    const [sendingReplyId, setSendingReplyId] = useState<string | null>(null)
    
    const [selectedLetter, setSelectedLetter] = useState<any | null>(null)

    const loadLetters = useCallback(async () => {
        setLoading(true)
        try {
            const params: any = { 
                limit, 
                offset: page * limit,
                status: filter === 'reported' ? 'reported' : 'active'
            }
            if (['none', 'ai', 'human'].includes(filter)) {
                params.replied_by = filter
            }

            const data = await adminService.listLetters(params)
            setLetters(data?.letters || [])
            setTotal(data?.total || 0)
        } catch (err) {
            if (!(err instanceof ApiRequestError && err.handledByModal)) {
                toast.error('Không thể tải danh sách thư')
            }
        } finally {
            setLoading(false)
        }
    }, [filter, page])

    useEffect(() => {
        loadLetters()
    }, [loadLetters])

    const handleAction = async (id: string, action: 'keep' | 'delete') => {
        try {
            await adminService.reviewLetter(id, action)
            toast.success(action === 'keep' ? 'Đã duyệt thư' : 'Đã xóa thư')
            loadLetters()
            if (selectedLetter?.letter_id === id) setSelectedLetter(null)
        } catch {
            toast.error('Thao tác thất bại')
        }
    }

    const handleAiAnalyze = async (id: string) => {
        setAnalyzingId(id)
        try {
            const res = await adminService.aiAnalyzeLetter(id)
            setAiResults(prev => ({ ...prev, [id]: res }))
            toast.info('AI đã hoàn thành phân tích')
        } catch {
            toast.error('AI không thể phân tích lúc này')
        } finally {
            setAnalyzingId(null)
        }
    }

    const handleAiSuggest = async (id: string) => {
        setSuggestingId(id)
        try {
            const res = await adminService.getAiReplySuggestions(id)
            setAiSuggestions(prev => ({ ...prev, [id]: res.suggestions }))
            setIsReplying(prev => ({ ...prev, [id]: true }))
            toast.success('AI đã tạo gợi ý phản hồi')
        } catch {
            toast.error('Không thể lấy gợi ý AI')
        } finally {
            setSuggestingId(null)
        }
    }

    const handleSendReply = async (id: string) => {
        const content = replyDrafts[id]
        if (!content || content.trim().length < 10) {
            return toast.warning('Nội dung phản hồi quá ngắn')
        }
        setSendingReplyId(id)
        try {
            await adminService.replyToLetter(id, { content })
            toast.success('Đã gửi phản hồi cho người dùng')
            setIsReplying(prev => ({ ...prev, [id]: false }))
            loadLetters()
            // If in detail view, update the local object
            if (selectedLetter?.letter_id === id) {
                const updated = { ...selectedLetter }
                updated.replies = [...(updated.replies || []), { content, created_at: new Date().toISOString(), author: 'Admin', is_ai: false }]
                setSelectedLetter(updated)
            }
        } catch {
            toast.error('Gửi phản hồi thất bại')
        } finally {
            setSendingReplyId(null)
        }
    }

    const totalPages = Math.ceil(total / limit)

    return (
        <div className="space-y-6">
            <header className="flex flex-col xl:flex-row xl:items-center justify-between gap-6">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-indigo-500/10 rounded-2xl border border-indigo-500/20">
                        <Inbox className="text-indigo-400 w-8 h-8" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-black text-white tracking-tight uppercase">Kiểm duyệt tâm sự</h1>
                        <p className="text-slate-500 text-xs font-bold uppercase tracking-tighter">Quan sát tương tác và phản hồi thư của người dùng.</p>
                    </div>
                </div>
                
                <div className="flex flex-wrap bg-black/40 p-1 rounded-2xl border border-white/5">
                    {[
                        { id: 'all', label: 'Tất cả', icon: Activity },
                        { id: 'none', label: 'Chưa rep', icon: Clock },
                        { id: 'ai', label: 'AI REP', icon: Bot },
                        { id: 'human', label: 'Người REP', icon: UserCheck },
                        { id: 'reported', label: 'Báo cáo', icon: AlertTriangle }
                    ].map(t => (
                        <button 
                            key={t.id}
                            onClick={() => { setFilter(t.id as any); setPage(0); }}
                            className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-wider transition-all flex items-center gap-2 ${filter === t.id ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-500 hover:text-slate-300'}`}
                        >
                            <t.icon size={14} />
                            {t.label}
                        </button>
                    ))}
                </div>
            </header>

            <div className="relative min-h-[500px]">
                {loading && (
                    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/40 backdrop-blur-[2px] rounded-[40px] animate-in fade-in duration-300">
                        <div className="bg-slate-900/90 p-10 rounded-[40px] border border-indigo-500/30 shadow-[0_0_50px_rgba(79,70,229,0.2)] flex flex-col items-center gap-6">
                            <Loader2 className="animate-spin text-indigo-400" size={56} />
                            <p className="text-sm font-black text-white uppercase tracking-[0.2em]">Đang đồng bộ</p>
                        </div>
                    </div>
                )}

                <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 transition-all duration-500 ${loading ? 'opacity-30 blur-[2px] grayscale-[0.5]' : 'opacity-100'}`}>
                    {letters.length === 0 && !loading ? (
                        <div className="xl:col-span-4 bg-white/5 border border-white/10 border-dashed rounded-[40px] p-32 text-center">
                            <Inbox className="mx-auto text-slate-800 mb-6" size={80} />
                            <p className="text-slate-500 font-black uppercase tracking-[0.3em] text-lg">Hộp thư trống</p>
                        </div>
                    ) : (
                        letters.map((letter) => (
                            <div key={letter.letter_id} className="bg-white/5 border border-white/10 rounded-[32px] overflow-hidden hover:border-indigo-500/40 hover:bg-white/[0.07] transition-all flex flex-col group shadow-2xl relative cursor-pointer" onClick={() => setSelectedLetter(letter)}>
                                {/* Letter Content Block */}
                                <div className="p-6 flex-1 flex flex-col gap-4">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <div className="w-8 h-8 rounded-xl bg-indigo-500/20 border border-indigo-500/20 flex items-center justify-center">
                                                <User size={14} className="text-indigo-400" />
                                            </div>
                                            <div className="flex flex-col">
                                                <span className="text-white text-[10px] font-black">{letter.sender_id.slice(-8)}</span>
                                                <span className="text-[8px] text-slate-500 font-black uppercase">{new Date(letter.created_at).toLocaleDateString('vi-VN')}</span>
                                            </div>
                                        </div>
                                        {letter.status === 'reported' && (
                                            <AlertTriangle size={16} className="text-rose-500 animate-pulse" />
                                        )}
                                    </div>

                                    <div className="bg-black/20 rounded-2xl p-4 min-h-[80px] border border-white/5 relative">
                                        <p className="text-slate-300 text-xs leading-relaxed italic line-clamp-3">
                                            "{letter.content}"
                                        </p>
                                        {aiResults[letter.letter_id] && (
                                            <div className={`absolute -top-2 -right-2 px-2 py-1 rounded-lg text-[8px] font-black uppercase flex items-center gap-1 shadow-lg ${aiResults[letter.letter_id].action === 'delete' ? 'bg-rose-500 text-white' : 'bg-emerald-500 text-white'}`}>
                                                <Brain size={10} /> AI Checked
                                            </div>
                                        )}
                                        {letter.content.length > 100 && (
                                            <span className="text-[9px] text-indigo-400 font-black uppercase mt-2 block">Xem thêm...</span>
                                        )}
                                    </div>

                                    {/* Replies Display - Compact */}
                                    <div className="space-y-2">
                                        {letter.replies?.slice(0, 2).map((r: any, i: number) => (
                                            <div key={i} className={`p-2 rounded-xl text-[10px] border ${r.is_ai ? 'bg-emerald-500/5 border-emerald-500/10 text-emerald-400/80' : 'bg-blue-500/5 border-blue-500/10 text-blue-400/80'}`}>
                                                <p className="line-clamp-1 italic font-medium">"{r.content}"</p>
                                            </div>
                                        ))}
                                        {letter.replies?.length > 2 && (
                                            <p className="text-[9px] text-slate-500 font-bold ml-1">+{letter.replies.length - 2} phản hồi khác</p>
                                        )}
                                    </div>
                                </div>

                                {/* Action Footer */}
                                <div className="p-4 bg-white/5 border-t border-white/5 flex gap-2" onClick={e => e.stopPropagation()}>
                                    <button 
                                        onClick={() => handleAiAnalyze(letter.letter_id)}
                                        disabled={analyzingId === letter.letter_id}
                                        className="w-10 h-10 flex items-center justify-center bg-white/5 hover:bg-indigo-500/20 text-indigo-400 rounded-xl transition-all border border-white/5"
                                        title="AI Analyze"
                                    >
                                        {analyzingId === letter.letter_id ? <Loader2 size={16} className="animate-spin" /> : <Brain size={16} />}
                                    </button>
                                    <button 
                                        onClick={() => handleAiSuggest(letter.letter_id)}
                                        disabled={suggestingId === letter.letter_id || letter.replies?.length > 0}
                                        className={`flex-1 flex items-center justify-center gap-2 rounded-xl text-[10px] font-black uppercase transition-all shadow-lg ${
                                            letter.replies?.length > 0
                                            ? 'bg-slate-800 text-slate-600 cursor-not-allowed opacity-50' 
                                            : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/20'
                                        }`}
                                    >
                                        <Sparkles size={14} />
                                        Trả lời
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex flex-col items-center gap-4 mt-12">
                    <p className="text-[10px] text-slate-500 font-black uppercase tracking-[0.2em]">
                        Trang {page + 1} / {totalPages} • {total} kết quả
                    </p>
                    <div className="flex items-center gap-2">
                        <button 
                            disabled={page === 0 || loading}
                            onClick={() => setPage(p => Math.max(0, p - 1))}
                            className="w-10 h-10 flex items-center justify-center bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:text-white disabled:opacity-20 transition-all"
                        >
                            <ChevronLeft size={18} />
                        </button>
                        
                        <div className="flex items-center gap-1.5">
                            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                let p = i + 1;
                                if (totalPages > 5 && page > 2) p = page - 2 + i + 1;
                                if (p > totalPages) return null;
                                return (
                                    <button
                                        key={p}
                                        onClick={() => setPage(p - 1)}
                                        className={`w-10 h-10 rounded-xl text-xs font-black transition-all border ${
                                            p === page + 1 
                                            ? 'bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-600/30' 
                                            : 'bg-white/5 border-white/5 text-slate-500 hover:text-white hover:bg-white/10'
                                        }`}
                                    >
                                        {p}
                                    </button>
                                );
                            })}
                        </div>

                        <button 
                            disabled={page === totalPages - 1 || loading}
                            onClick={() => setPage(p => p + 1)}
                            className="w-10 h-10 flex items-center justify-center bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:text-white disabled:opacity-20 transition-all"
                        >
                            <ChevronRight size={18} />
                        </button>
                    </div>
                </div>
            )}

            {/* Detail Modal */}
            {selectedLetter && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 md:p-10 animate-in fade-in duration-300">
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-md" onClick={() => setSelectedLetter(null)} />
                    <div className="relative bg-slate-900 border border-white/10 w-full max-w-4xl max-h-[90vh] rounded-[40px] shadow-[0_0_100px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col animate-in zoom-in-95 duration-300">
                        <header className="p-6 border-b border-white/5 flex items-center justify-between bg-white/5">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 rounded-2xl bg-indigo-500/20 flex items-center justify-center border border-indigo-500/20">
                                    <Inbox className="text-indigo-400" size={24} />
                                </div>
                                <div>
                                    <h2 className="text-xl font-black text-white uppercase tracking-tight">Chi tiết tâm sự</h2>
                                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">ID: {selectedLetter.letter_id}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                {aiResults[selectedLetter.letter_id] && (
                                    <div className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase flex items-center gap-2 border ${aiResults[selectedLetter.letter_id].action === 'delete' ? 'bg-rose-500/10 border-rose-500/20 text-rose-400' : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'}`}>
                                        <Shield size={14} /> AI: {aiResults[selectedLetter.letter_id].action === 'delete' ? 'CẦN LƯU Ý' : 'AN TOÀN'}
                                    </div>
                                )}
                                <button onClick={() => setSelectedLetter(null)} className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-slate-400 hover:text-white hover:bg-rose-500/20 transition-all">
                                    <X size={20} />
                                </button>
                            </div>
                        </header>

                        <div className="flex-1 overflow-y-auto p-6 md:p-10 space-y-10 custom-scrollbar">
                            {/* Original Letter */}
                            <section className="space-y-4">
                                <div className="flex items-center gap-2">
                                    <User size={16} className="text-indigo-400" />
                                    <span className="text-xs font-black text-white uppercase">{selectedLetter.sender_id} gửi lúc {new Date(selectedLetter.created_at).toLocaleString('vi-VN')}</span>
                                </div>
                                <div className="bg-white/5 border border-white/5 p-8 rounded-[32px] relative group">
                                    <div className="absolute -left-1 top-8 w-1 h-12 bg-indigo-500 rounded-full shadow-[0_0_15px_rgba(99,102,241,0.5)]" />
                                    <p className="text-lg text-slate-200 leading-relaxed font-medium italic">
                                        "{selectedLetter.content}"
                                    </p>
                                </div>

                                {/* AI Analysis Result Display */}
                                {analyzingId === selectedLetter.letter_id ? (
                                    <div className="p-8 bg-indigo-500/5 border border-indigo-500/20 border-dashed rounded-[32px] flex flex-col items-center gap-4 animate-pulse">
                                        <Loader2 className="animate-spin text-indigo-400" size={32} />
                                        <p className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em]">AI đang thẩm định nội dung...</p>
                                    </div>
                                ) : aiResults[selectedLetter.letter_id] && (
                                    <motion.div 
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        className={`p-6 rounded-[32px] border ${aiResults[selectedLetter.letter_id].action === 'delete' ? 'bg-rose-500/10 border-rose-500/20' : 'bg-indigo-500/10 border-indigo-500/20'}`}
                                    >
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="flex items-center gap-2">
                                                <div className={`p-2 rounded-xl ${aiResults[selectedLetter.letter_id].action === 'delete' ? 'bg-rose-500/20 text-rose-400' : 'bg-indigo-500/20 text-indigo-400'}`}>
                                                    <Brain size={18} />
                                                </div>
                                                <div>
                                                    <h4 className="text-sm font-black text-white uppercase tracking-tight">Kết quả Phân tích AI</h4>
                                                    <p className={`text-[10px] font-bold uppercase ${aiResults[selectedLetter.letter_id].action === 'delete' ? 'text-rose-400' : 'text-indigo-400'}`}>
                                                        Trạng thái: {aiResults[selectedLetter.letter_id].action === 'delete' ? 'Cảnh báo bất thường' : 'Bình thường'}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase ${aiResults[selectedLetter.letter_id].action === 'delete' ? 'bg-rose-500 text-white' : 'bg-indigo-500 text-white'}`}>
                                                {aiResults[selectedLetter.letter_id].category || 'General'}
                                            </div>
                                        </div>
                                        <p className="text-xs text-slate-400 leading-relaxed italic">
                                            "<strong>Nhận định:</strong> {aiResults[selectedLetter.letter_id].reason}"
                                        </p>
                                    </motion.div>
                                )}
                            </section>

                            {/* Replies Timeline */}
                            <section className="space-y-6">
                                <div className="flex items-center gap-2 mb-4">
                                    <MessageSquare size={16} className="text-emerald-400" />
                                    <h3 className="text-sm font-black text-white uppercase tracking-widest">Cuộc hội thoại ({selectedLetter.replies?.length || 0})</h3>
                                </div>
                                
                                <div className="space-y-6 pl-4 border-l-2 border-white/5 ml-2">
                                    {selectedLetter.replies?.map((r: any, i: number) => (
                                        <div key={i} className="relative animate-in slide-in-from-left-4 duration-500" style={{ animationDelay: `${i * 100}ms` }}>
                                            <div className="absolute -left-[25px] top-4 w-4 h-4 rounded-full bg-slate-900 border-2 border-white/10 flex items-center justify-center">
                                                <div className={`w-1.5 h-1.5 rounded-full ${r.is_ai ? 'bg-emerald-400' : 'bg-blue-400'}`} />
                                            </div>
                                            <div className={`p-6 rounded-3xl border shadow-xl ${r.is_ai ? 'bg-emerald-500/5 border-emerald-500/10' : 'bg-blue-500/5 border-blue-500/10'}`}>
                                                <div className="flex items-center justify-between mb-3">
                                                    <div className="flex items-center gap-2">
                                                        {r.is_ai ? <Bot size={14} className="text-emerald-400" /> : <UserCheck size={14} className="text-blue-400" />}
                                                        <span className={`text-[10px] font-black uppercase tracking-widest ${r.is_ai ? 'text-emerald-400' : 'text-blue-400'}`}>
                                                            {r.is_ai ? 'AI Assistant' : `Người dùng: ${r.author}`}
                                                        </span>
                                                    </div>
                                                    <span className="text-[9px] text-slate-500 font-bold uppercase">{new Date(r.created_at).toLocaleString('vi-VN')}</span>
                                                </div>
                                                <p className="text-sm text-slate-300 leading-relaxed italic">"{r.content}"</p>
                                            </div>
                                        </div>
                                    ))}
                                    
                                    {isReplying[selectedLetter.letter_id] && (
                                        <div className="p-6 bg-indigo-500/5 border border-indigo-500/10 rounded-3xl space-y-6 animate-in slide-in-from-bottom-4">
                                            <div className="flex items-center justify-between">
                                                <span className="text-xs font-black text-indigo-400 uppercase tracking-widest">Phản hồi của bạn</span>
                                                <button onClick={() => setIsReplying(prev => ({...prev, [selectedLetter.letter_id]: false}))} className="text-slate-600 hover:text-white"><X size={16} /></button>
                                            </div>

                                            {/* AI Suggestion Pills */}
                                            {suggestingId === selectedLetter.letter_id ? (
                                                <div className="space-y-3">
                                                    <div className="admin-skeleton h-10 w-full" />
                                                    <div className="admin-skeleton h-10 w-4/5" />
                                                </div>
                                            ) : aiSuggestions[selectedLetter.letter_id] && (
                                                <div className="space-y-3">
                                                    <p className="text-[9px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                                                        <Sparkles size={10} className="text-amber-400" /> AI Gợi ý phản hồi (Chọn để sử dụng)
                                                    </p>
                                                    <div className="flex flex-col gap-2">
                                                        {aiSuggestions[selectedLetter.letter_id].map((s, idx) => (
                                                            <button 
                                                                key={idx}
                                                                onClick={() => setReplyDrafts(prev => ({...prev, [selectedLetter.letter_id]: s.content}))}
                                                                className="text-left p-4 bg-white/5 border border-white/10 rounded-2xl hover:border-indigo-500/40 hover:bg-white/10 transition-all group"
                                                            >
                                                                <div className="flex items-center gap-2 mb-1">
                                                                    <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-400 rounded-md text-[8px] font-black uppercase">{s.style}</span>
                                                                </div>
                                                                <p className="text-[11px] text-slate-400 leading-relaxed group-hover:text-slate-200 line-clamp-2 italic">"{s.content}"</p>
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            <textarea 
                                                value={replyDrafts[selectedLetter.letter_id] || ''}
                                                onChange={(e) => setReplyDrafts(prev => ({...prev, [selectedLetter.letter_id]: e.target.value}))}
                                                rows={6}
                                                className="w-full bg-black/40 border border-white/10 rounded-2xl p-4 text-white text-sm outline-none focus:border-indigo-500 transition-all font-medium italic"
                                                placeholder="Viết nội dung phản hồi tại đây hoặc chọn gợi ý từ AI bên trên..."
                                            />
                                            <div className="flex justify-end">
                                                <button 
                                                    onClick={() => handleSendReply(selectedLetter.letter_id)}
                                                    disabled={sendingReplyId === selectedLetter.letter_id}
                                                    className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-3 rounded-2xl text-[10px] font-black flex items-center gap-2 transition-all shadow-lg shadow-indigo-600/20"
                                                >
                                                    {sendingReplyId === selectedLetter.letter_id ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                                                    GỬI PHẢN HỒI NGAY
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </section>
                        </div>

                        <footer className="p-6 bg-white/5 border-t border-white/5 flex gap-4">
                            <button 
                                onClick={() => handleAiAnalyze(selectedLetter.letter_id)}
                                disabled={analyzingId === selectedLetter.letter_id}
                                className="px-6 py-3 bg-white/5 hover:bg-indigo-500/20 text-indigo-400 rounded-2xl flex items-center gap-2 text-xs font-black uppercase transition-all"
                            >
                                {analyzingId === selectedLetter.letter_id ? <Loader2 size={16} className="animate-spin" /> : <Brain size={16} />}
                                AI Phân tích
                            </button>
                            <button 
                                onClick={() => handleAiSuggest(selectedLetter.letter_id)}
                                disabled={suggestingId === selectedLetter.letter_id || selectedLetter.replies?.length > 0}
                                className={`flex-1 py-3 rounded-2xl flex items-center justify-center gap-2 text-xs font-black uppercase transition-all shadow-xl ${
                                    selectedLetter.replies?.length > 0
                                    ? 'bg-slate-800 text-slate-600 cursor-not-allowed opacity-50' 
                                    : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/20'
                                }`}
                            >
                                <Sparkles size={16} />
                                Trả lời
                            </button>
                            {selectedLetter.status === 'reported' && (
                                <button 
                                    onClick={() => handleAction(selectedLetter.letter_id, 'delete')}
                                    className="px-6 py-3 bg-rose-500/10 hover:bg-rose-500 text-rose-500 hover:text-white rounded-2xl text-xs font-black uppercase transition-all border border-rose-500/20"
                                >
                                    Xóa thư
                                </button>
                            )}
                        </footer>
                    </div>
                </div>
            )}
        </div>
    )
}
