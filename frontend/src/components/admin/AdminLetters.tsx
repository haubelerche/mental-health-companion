import { useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import { ApiRequestError } from '../../api/types'
import { toast } from 'react-toastify'
import { 
    Shield, 
    Clock, 
    User, 
    AlertTriangle, 
    CheckCircle, 
    Trash2, 
    Brain, 
    ChevronLeft, 
    ChevronRight, 
    Loader2, 
    Sparkles, 
    Mail, 
    Activity,
    Send,
    Edit3,
    X,
    MessageSquare
} from 'lucide-react'

import { adminCache } from '../../hooks/useAdminStore'
import WorkerAutomationCard from './automation/WorkerAutomationCard'

type Tab = 'normal' | 'reported'

export default function AdminLetters() {
    const cached = adminCache.getLetters()
    const [activeTab, setActiveTab] = useState<Tab>(cached.reported.length > 0 && cached.normal.length === 0 ? 'reported' : 'normal')
    
    const [dataNormal, setDataNormal] = useState<any[]>(cached.normal)
    const [dataReported, setDataReported] = useState<any[]>(cached.reported)
    const [totalReported, setTotalReported] = useState(cached.totalReported)
    const [currentPage, setCurrentPage] = useState(cached.currentPage)
    const pageSize = 5

    const [loading, setLoading] = useState(false)
    const [analyzingId, setAnalyzingId] = useState<string | null>(null)
    const [suggestingId, setSuggestingId] = useState<string | null>(null)
    const [aiResults, setAiResults] = useState<Record<string, any>>({})
    const [aiSuggestions, setAiSuggestions] = useState<Record<string, any[]>>({})
    const [replyDrafts, setReplyDrafts] = useState<Record<string, string>>({})
    const [isReplying, setIsReplying] = useState<Record<string, boolean>>({})
    const [sendingReplyId, setSendingReplyId] = useState<string | null>(null)
    const [logs, setLogs] = useState<any[]>([])

    const fetchLogs = async () => {
        try {
            const res = await adminService.getAutomationStatus()
            const letterLogs = (res.logs || []).filter((l: any) => l.worker === 'letter').slice(0, 5)
            setLogs(letterLogs)
        } catch (err) {}
    }

    useEffect(() => {
        fetchLogs()
        const inv = setInterval(fetchLogs, 15000)
        return () => clearInterval(inv)
    }, [])

    const loadNormal = async (force = false) => {
        if (!force && dataNormal.length > 0) return
        setLoading(true)
        try {
            const data = await adminService.listLetters({ status: 'active', limit: 20 })
            const letters = data?.letters || []
            setDataNormal(letters)
            adminCache.setLetters({ normal: letters })
        } catch (err) {
            if (!(err instanceof ApiRequestError && err.handledByModal)) {
                toast.error('Không thể tải danh sách thư')
            }
        } finally {
            setLoading(false)
        }
    }

    const loadReported = async (page = 1, force = false) => {
        if (!force && dataReported.length > 0 && page === currentPage) return
        setLoading(true)
        try {
            const data = await adminService.listLetters({ 
                status: 'reported', 
                limit: pageSize, 
                offset: (page - 1) * pageSize 
            })
            const letters = data?.letters || []
            setDataReported(letters)
            setTotalReported(data?.total || 0)
            adminCache.setLetters({ 
                reported: letters, 
                totalReported: data?.total || 0,
                currentPage: page
            })
        } catch (err) {
            if (!(err instanceof ApiRequestError && err.handledByModal)) {
                toast.error('Không thể tải danh sách báo cáo')
            }
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (activeTab === 'normal') loadNormal()
        else loadReported(currentPage)
    }, [activeTab, currentPage])

    const handleAction = async (id: string, action: 'keep' | 'delete') => {
        try {
            await adminService.reviewLetter(id, action)
            toast.success(action === 'keep' ? 'Đã giữ lại thư' : 'Đã xóa thư')
            if (activeTab === 'normal') loadNormal(true)
            else loadReported(currentPage, true)
        } catch (err) {
            toast.error('Thao tác thất bại')
        }
    }

    const handleAiAnalyze = async (id: string) => {
        setAnalyzingId(id)
        try {
            const res = await adminService.aiAnalyzeLetter(id)
            setAiResults(prev => ({ ...prev, [id]: res }))
            toast.info('AI đã hoàn thành phân tích')
        } catch (err) {
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
            toast.success('AI đã tạo 3 gợi ý phản hồi')
        } catch (err) {
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
            // Refresh to show the reply
            if (activeTab === 'normal') loadNormal(true)
            else loadReported(currentPage, true)
        } catch (err) {
            toast.error('Gửi phản hồi thất bại')
        } finally {
            setSendingReplyId(null)
        }
    }

    const currentData = activeTab === 'normal' ? dataNormal : dataReported
    const totalPages = Math.ceil(totalReported / pageSize)

    return (
        <div className="space-y-6">
            <header className="flex flex-col xl:flex-row xl:items-center justify-between gap-6">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-indigo-500/10 rounded-2xl border border-indigo-500/20">
                        <Shield className="text-indigo-400 w-8 h-8" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-white tracking-tight">Kiểm duyệt tâm sự</h1>
                        <p className="text-slate-400 text-sm">Xem xét thư và kích hoạt phản hồi AI tự động.</p>
                    </div>
                </div>
                
                <div className="flex bg-black/40 p-1 rounded-xl border border-white/10">
                    <button 
                        onClick={() => setActiveTab('normal')}
                        className={`px-5 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${activeTab === 'normal' ? 'bg-white/10 text-white shadow-inner' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        Thư thường
                    </button>
                    <button 
                        onClick={() => setActiveTab('reported')}
                        className={`px-5 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-2 ${activeTab === 'reported' ? 'bg-rose-500 text-white shadow-lg shadow-rose-500/20' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        Bị báo cáo
                        {totalReported > 0 && <span className="bg-white/20 text-[10px] px-1.5 py-0.5 rounded-full">{totalReported}</span>}
                    </button>
                </div>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-1">
                    <WorkerAutomationCard 
                        workerKey="letter" 
                        icon={Brain} 
                        description="Tự động trả lời thư Public chưa có hồi đáp sau ngưỡng thời gian cấu hình."
                    />
                </div>
                <div className="lg:col-span-2 bg-black/40 border border-white/10 rounded-2xl p-6 flex flex-col">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                            <Activity size={14} className="text-indigo-400" /> Nhật ký AI mới nhất
                        </h3>
                    </div>
                    <div className="space-y-2 flex-1 overflow-y-auto max-h-[140px] custom-scrollbar pr-2">
                        {logs.length > 0 ? (
                            logs.map((log, i) => (
                                <div key={i} className="flex gap-3 text-[11px] border-l border-indigo-500/20 pl-3 py-1 hover:bg-white/5 transition-all">
                                    <span className="text-slate-600 shrink-0">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                                    <span className="text-slate-300 line-clamp-1">{log.message}</span>
                                </div>
                            ))
                        ) : (
                            <p className="text-xs text-slate-600 italic py-4 text-center">Chưa có hoạt động nào được ghi nhận.</p>
                        )}
                    </div>
                </div>
            </div>

            <div className="h-[1px] bg-white/5 w-full" />

            <div className="grid gap-4">
                {loading && currentData.length === 0 ? (
                    <div className="bg-white/5 border border-white/10 rounded-xl p-20 text-center">
                        <Loader2 className="mx-auto text-indigo-400 animate-spin mb-4" size={32} />
                        <p className="text-slate-400 animate-pulse">Đang tải dữ liệu tâm sự...</p>
                    </div>
                ) : currentData.length === 0 ? (
                    <div className="bg-white/5 border border-white/10 rounded-xl p-20 text-center border-dashed">
                        <CheckCircle className="mx-auto text-slate-700 mb-4" size={48} />
                        <p className="text-slate-500">Mọi thứ đều sạch sẽ. Chưa có thư nào cần xử lý.</p>
                        <button onClick={() => activeTab === 'normal' ? loadNormal(true) : loadReported(currentPage, true)} className="mt-4 text-indigo-400 text-sm hover:underline">Tải lại trang</button>
                    </div>
                ) : (
                    currentData.map((letter) => (
                        <div key={letter.letter_id} className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-white/20 transition-all group animate-in fade-in slide-in-from-bottom-2 duration-300">
                            <div className="p-5 flex flex-col md:flex-row gap-6">
                                <div className="flex-1 space-y-4">
                                    <div className="flex items-center gap-3 text-[11px] font-medium uppercase tracking-wider text-slate-500">
                                        <span className="flex items-center gap-1"><User size={12} /> {letter.sender_id}</span>
                                        <span className="flex items-center gap-1"><Clock size={12} /> {new Date(letter.created_at).toLocaleString('vi-VN')}</span>
                                        {letter.status === 'reported' && (
                                            <span className="flex items-center gap-1 text-rose-400 bg-rose-400/10 px-2 py-0.5 rounded-full">
                                                <AlertTriangle size={10} /> Đã báo cáo
                                            </span>
                                        )}
                                    </div>
                                    <div className="relative group/content">
                                        <div className="flex gap-4">
                                            <div className="flex flex-col items-center gap-2">
                                                <div className="w-8 h-8 rounded-full bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 shrink-0">
                                                    <User size={14} className="text-indigo-400" />
                                                </div>
                                                <div className="w-[2px] flex-1 bg-gradient-to-b from-indigo-500/20 to-transparent" />
                                            </div>
                                            <div className="flex-1 pb-4 space-y-4">
                                                <div className="bg-white/5 border border-white/10 rounded-2xl p-4 hover:border-white/20 transition-all">
                                                    <p className="text-slate-200 leading-relaxed italic">
                                                        "{letter.content}"
                                                    </p>
                                                </div>

                                                {letter.status === 'reported' && (
                                                    <div className="space-y-2 px-1">
                                                        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Lý do báo cáo:</p>
                                                        <div className="flex flex-wrap gap-2">
                                                            {letter.report_data?.details?.length > 0 ? (
                                                                letter.report_data.details.map((d: any, i: number) => (
                                                                    <div key={i} className="bg-rose-400/5 border border-rose-400/10 px-3 py-1.5 rounded-lg">
                                                                        <p className="text-[10px] text-rose-400 font-bold uppercase">{d.category}</p>
                                                                        <p className="text-xs text-slate-300">{d.reason}</p>
                                                                    </div>
                                                                ))
                                                            ) : (
                                                                <div className="bg-rose-400/5 border border-rose-400/10 px-3 py-1.5 rounded-lg text-xs text-rose-300">
                                                                    {letter.report_data?.reason || 'Báo cáo không có lý do chi tiết.'}
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                )}

                                                {aiResults[letter.letter_id] && (
                                                    <div className="bg-indigo-500/10 border border-indigo-500/20 p-4 rounded-xl space-y-2 animate-in zoom-in-95 duration-300">
                                                        <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs uppercase tracking-widest">
                                                            <Brain size={14} /> AI Moderation Insight
                                                        </div>
                                                        <p className="text-xs text-slate-400">
                                                            {aiResults[letter.letter_id].reason}
                                                        </p>
                                                        <div className="flex items-center gap-3 text-[10px] mt-1">
                                                            <span className={`px-2 py-0.5 rounded-full ${aiResults[letter.letter_id].action === 'delete' ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                                                                {aiResults[letter.letter_id].action === 'delete' ? 'Nên xóa bỏ' : 'Có thể giữ lại'}
                                                            </span>
                                                            <span className="text-slate-500 capitalize italic">Loại: {aiResults[letter.letter_id].category}</span>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        {letter.ai_reply && (
                                            <div className="flex gap-4 animate-in slide-in-from-left-4 duration-500">
                                                <div className="flex flex-col items-center gap-2">
                                                    <div className="w-8 h-8 rounded-full bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 shrink-0">
                                                        <MessageSquare size={14} className="text-emerald-400" />
                                                    </div>
                                                </div>
                                                <div className="flex-1">
                                                    <div className="bg-emerald-500/5 border border-emerald-500/20 p-4 rounded-2xl space-y-2 relative">
                                                        <div className="absolute -left-2 top-4 w-2 h-2 bg-emerald-500/20 rotate-45 border-l border-b border-emerald-500/20" />
                                                        <div className="flex items-center justify-between mb-1">
                                                            <span className="text-emerald-400 font-bold text-[10px] uppercase tracking-widest">Đã có phản hồi</span>
                                                            <span className="text-[10px] text-slate-500 font-medium">{new Date(letter.ai_reply.created_at).toLocaleString('vi-VN')}</span>
                                                        </div>
                                                        <p className="text-sm text-slate-300 leading-relaxed">
                                                            {letter.ai_reply.content}
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {/* Reply Editor Section */}
                                    {isReplying[letter.letter_id] && (
                                        <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-2xl p-5 space-y-4 animate-in slide-in-from-top-2 duration-300">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs uppercase tracking-widest">
                                                    <MessageSquare size={14} /> Phản hồi cho người dùng
                                                </div>
                                                <button onClick={() => setIsReplying(prev => ({...prev, [letter.letter_id]: false}))} className="text-slate-500 hover:text-white transition-colors">
                                                    <X size={16} />
                                                </button>
                                            </div>

                                            {aiSuggestions[letter.letter_id] && (
                                                <div className="space-y-2">
                                                    <p className="text-[10px] text-slate-500 uppercase font-black tracking-widest ml-1">AI Gợi ý phương án:</p>
                                                    <div className="grid grid-cols-3 gap-2">
                                                        {aiSuggestions[letter.letter_id].map((s: any, idx: number) => (
                                                            <button 
                                                                key={idx}
                                                                onClick={() => setReplyDrafts(prev => ({...prev, [letter.letter_id]: s.content}))}
                                                                className="bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 p-2.5 rounded-xl text-left transition-all group"
                                                            >
                                                                <p className="text-[9px] text-indigo-400 font-bold uppercase mb-1">{s.style}</p>
                                                                <p className="text-[11px] text-slate-300 line-clamp-2 group-hover:line-clamp-none transition-all">{s.content}</p>
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            <div className="relative">
                                                <textarea 
                                                    value={replyDrafts[letter.letter_id] || ''}
                                                    onChange={(e) => setReplyDrafts(prev => ({...prev, [letter.letter_id]: e.target.value}))}
                                                    rows={4}
                                                    className="w-full bg-black/40 border border-white/10 rounded-xl p-4 text-sm text-slate-200 focus:border-indigo-500 outline-none transition-all resize-none"
                                                    placeholder="Viết câu trả lời của bạn tại đây hoặc chọn gợi ý từ AI..."
                                                />
                                                <div className="absolute bottom-3 right-3 flex items-center gap-2">
                                                    <span className="text-[10px] text-slate-600">{(replyDrafts[letter.letter_id] || '').length} ký tự</span>
                                                    <button 
                                                        onClick={() => handleSendReply(letter.letter_id)}
                                                        disabled={sendingReplyId === letter.letter_id}
                                                        className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 transition-all shadow-lg shadow-indigo-600/20 disabled:opacity-50"
                                                    >
                                                        {sendingReplyId === letter.letter_id ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
                                                        Gửi ngay
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div className="flex md:flex-col justify-end gap-2 shrink-0">
                                    <div className="flex gap-2">
                                        <button 
                                            onClick={() => handleAiAnalyze(letter.letter_id)}
                                            disabled={analyzingId === letter.letter_id}
                                            className="flex-1 flex items-center justify-center gap-2 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 px-4 py-2.5 rounded-lg text-sm font-medium border border-indigo-500/20 transition-all disabled:opacity-50"
                                            title="AI Phân tích nội dung"
                                        >
                                            {analyzingId === letter.letter_id ? <Loader2 size={16} className="animate-spin" /> : <Brain size={16} />}
                                            <span className="md:hidden lg:inline">Phân tích</span>
                                        </button>
                                        <button 
                                            onClick={() => handleAiSuggest(letter.letter_id)}
                                            disabled={suggestingId === letter.letter_id || letter.ai_reply}
                                            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium border transition-all disabled:opacity-50 ${isReplying[letter.letter_id] ? 'bg-indigo-500 text-white border-indigo-500' : 'bg-white/5 hover:bg-white/10 text-slate-300 border-white/10'}`}
                                            title="AI Gợi ý câu trả lời"
                                        >
                                            {suggestingId === letter.letter_id ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                                            <span className="md:hidden lg:inline">Gợi ý & Trả lời</span>
                                        </button>
                                    </div>
                                    
                                    <div className="flex gap-2 border-t border-white/5 pt-2 md:border-t-0 md:pt-0">
                                        <button 
                                            onClick={() => handleAction(letter.letter_id, 'keep')}
                                            className="flex-1 flex items-center justify-center gap-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 px-4 py-2.5 rounded-lg text-sm font-medium border border-emerald-500/20 transition-all"
                                        >
                                            <CheckCircle size={16} /> Giữ
                                        </button>
                                        <button 
                                            onClick={() => handleAction(letter.letter_id, 'delete')}
                                            className="flex-1 flex items-center justify-center gap-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 px-4 py-2.5 rounded-lg text-sm font-medium border border-rose-500/20 transition-all"
                                        >
                                            <Trash2 size={16} /> Xóa
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {activeTab === 'reported' && totalPages > 1 && (
                <div className="flex items-center justify-center gap-4 mt-8">
                    <button 
                        disabled={currentPage === 1}
                        onClick={() => setCurrentPage(prev => prev - 1)}
                        className="p-2 rounded-full border border-white/10 text-slate-400 hover:bg-white/5 disabled:opacity-30 transition-all"
                    >
                        <ChevronLeft size={20} />
                    </button>
                    <div className="flex items-center gap-2">
                        {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                            <button
                                key={p}
                                onClick={() => setCurrentPage(p)}
                                className={`w-8 h-8 rounded-lg text-xs font-bold transition-all ${currentPage === p ? 'bg-indigo-600 text-white' : 'bg-white/5 text-slate-500 hover:text-slate-300'}`}
                            >
                                {p}
                            </button>
                        ))}
                    </div>
                    <button 
                        disabled={currentPage === totalPages}
                        onClick={() => setCurrentPage(prev => prev + 1)}
                        className="p-2 rounded-full border border-white/10 text-slate-400 hover:bg-white/5 disabled:opacity-30 transition-all"
                    >
                        <ChevronRight size={20} />
                    </button>
                </div>
            )}
        </div>
    )
}
