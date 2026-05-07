import { useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import { ApiRequestError } from '../../api/types'
import { toast } from 'react-toastify'
import { Shield, Clock, User, AlertTriangle, CheckCircle, Trash2, Brain, ChevronLeft, ChevronRight, Loader2, Sparkles, Mail } from 'lucide-react'

import { adminCache } from '../../hooks/useAdminStore'

type Tab = 'normal' | 'reported'

export default function AdminLetters() {
    const cached = adminCache.getLetters()
    const [activeTab, setActiveTab] = useState<Tab>(cached.reported.length > 0 && cached.normal.length === 0 ? 'reported' : 'normal')
    
    // Caching state to prevent reloads when switching tabs
    const [dataNormal, setDataNormal] = useState<any[]>(cached.normal)
    const [dataReported, setDataReported] = useState<any[]>(cached.reported)
    const [totalReported, setTotalReported] = useState(cached.totalReported)
    const [currentPage, setCurrentPage] = useState(cached.currentPage)
    const pageSize = 5

    const [loading, setLoading] = useState(false)
    const [analyzingId, setAnalyzingId] = useState<string | null>(null)
    const [aiResults, setAiResults] = useState<Record<string, any>>({})

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
            // Refresh current view
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
                                <div className="flex-1 space-y-3">
                                    <div className="flex items-center gap-3 text-[11px] font-medium uppercase tracking-wider text-slate-500">
                                        <span className="flex items-center gap-1"><User size={12} /> {letter.sender_id}</span>
                                        <span className="flex items-center gap-1"><Clock size={12} /> {new Date(letter.created_at).toLocaleString('vi-VN')}</span>
                                        {letter.status === 'reported' && (
                                            <span className="flex items-center gap-1 text-rose-400 bg-rose-400/10 px-2 py-0.5 rounded-full">
                                                <AlertTriangle size={10} /> Đã báo cáo
                                            </span>
                                        )}
                                    </div>
                                    <div className="relative">
                                        <Mail className="absolute -top-2 -left-2 text-white/5 w-10 h-10 -z-10" />
                                        <p className="text-slate-200 leading-relaxed italic border-l-2 border-indigo-500/30 pl-4 py-1">
                                            "{letter.content}"
                                        </p>
                                    </div>
                                    
                                    {letter.status === 'reported' && (
                                        <div className="space-y-2 mt-4">
                                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Lý do báo cáo chi tiết:</p>
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

                                    {letter.ai_reply && (
                                        <div className="bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-lg space-y-2 mt-4 animate-in slide-in-from-left-2 duration-500">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-2 text-emerald-400 font-bold text-[10px] uppercase tracking-widest">
                                                    <Sparkles size={12} /> Serene AI đã hồi đáp
                                                </div>
                                                <span className="text-[10px] text-slate-500 font-medium">{new Date(letter.ai_reply.created_at).toLocaleString('vi-VN')}</span>
                                            </div>
                                            <p className="text-sm text-slate-200 leading-relaxed pl-3 border-l-2 border-emerald-500/30 py-1">
                                                {letter.ai_reply.content}
                                            </p>
                                        </div>
                                    )}

                                    {aiResults[letter.letter_id] && (
                                        <div className="bg-indigo-500/10 border border-indigo-500/20 p-4 rounded-lg space-y-2 animate-in zoom-in-95 duration-300">
                                            <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs uppercase tracking-widest">
                                                <Brain size={14} /> AI Moderation Insight
                                            </div>
                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <p className="text-[10px] text-slate-500 uppercase">Phân loại</p>
                                                    <p className="text-sm text-slate-200 capitalize">{aiResults[letter.letter_id].category}</p>
                                                </div>
                                                <div>
                                                    <p className="text-[10px] text-slate-500 uppercase">Mức độ</p>
                                                    <p className={`text-sm font-bold capitalize ${aiResults[letter.letter_id].severity === 'cao' ? 'text-rose-400' : 'text-yellow-400'}`}>
                                                        {aiResults[letter.letter_id].severity}
                                                    </p>
                                                </div>
                                            </div>
                                            <p className="text-xs text-slate-400 border-t border-white/5 pt-2 mt-2">
                                                {aiResults[letter.letter_id].reason}
                                            </p>
                                            <div className="flex items-center gap-1 text-[10px] text-indigo-400/60 mt-1 italic">
                                                <Sparkles size={10} /> Đề xuất: {aiResults[letter.letter_id].action === 'delete' ? 'Nên xóa bỏ' : 'Có thể giữ lại'}
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div className="flex md:flex-col justify-end gap-2 shrink-0">
                                    <button 
                                        onClick={() => handleAiAnalyze(letter.letter_id)}
                                        disabled={analyzingId === letter.letter_id}
                                        className="flex items-center justify-center gap-2 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 px-4 py-2 rounded-lg text-sm font-medium border border-indigo-500/20 transition-all disabled:opacity-50"
                                    >
                                        {analyzingId === letter.letter_id ? <Loader2 size={16} className="animate-spin" /> : <Brain size={16} />}
                                        AI Phân tích
                                    </button>
                                    <div className="flex gap-2">
                                        <button 
                                            onClick={() => handleAction(letter.letter_id, 'keep')}
                                            className="flex-1 flex items-center justify-center gap-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 px-4 py-2 rounded-lg text-sm font-medium border border-emerald-500/20 transition-all"
                                        >
                                            <CheckCircle size={16} /> Giữ
                                        </button>
                                        <button 
                                            onClick={() => handleAction(letter.letter_id, 'delete')}
                                            className="flex-1 flex items-center justify-center gap-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 px-4 py-2 rounded-lg text-sm font-medium border border-rose-500/20 transition-all"
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
