import { useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import { toast } from 'react-toastify'
import { Check, Trash2, Mail, AlertCircle, Clock, Sparkles } from 'lucide-react'

export default function AdminLetters() {
    const [letters, setLetters] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [runningAi, setRunningAi] = useState(false)

    const load = async () => {
        setLoading(true)
        try {
            const data = await adminService.listLetters({ status: 'reported' })
            setLetters(data.letters)
        } catch (err) {
            toast.error('Không thể tải danh sách thư bị báo cáo')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        load()
    }, [])

    const handleReview = async (letterId: string, action: 'keep' | 'delete') => {
        try {
            await adminService.reviewLetter(letterId, action)
            setLetters(letters.filter(l => l.letter_id !== letterId))
            toast.success(action === 'keep' ? 'Đã giữ lại thư' : 'Đã xóa thư')
        } catch (err) {
            toast.error('Thao tác thất bại')
        }
    }

    const runAiResponder = async () => {
        setRunningAi(true)
        try {
            const res = await adminService.runAiResponder(6)
            toast.success(`AI đã xử lý xong ${res.processed_count} lá thư chờ quá 6 tiếng.`)
            load()
        } catch (err) {
            toast.error('Không thể chạy AI Responder')
        } finally {
            setRunningAi(false)
        }
    }

    return (
        <div className="space-y-6">
            <header className="flex justify-between items-start">
                <div>
                    <h1 className="text-2xl font-bold text-white">Kiểm duyệt thư (Báo cáo)</h1>
                    <p className="text-slate-400">Xem xét các lá thư bị người dùng báo cáo vi phạm.</p>
                </div>
                <button
                    onClick={runAiResponder}
                    disabled={runningAi}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white rounded-lg font-medium transition-all shadow-lg shadow-indigo-500/20"
                >
                    <Sparkles size={18} className={runningAi ? 'animate-spin' : ''} />
                    {runningAi ? 'AI đang viết thư...' : 'Chạy AI Responder (6h+)'}
                </button>
            </header>

            <div className="grid grid-cols-1 gap-4">
                {letters.map((letter) => (
                    <div key={letter.letter_id} className="bg-white/5 border border-white/10 rounded-xl p-6 hover:border-white/20 transition-all">
                        <div className="flex justify-between items-start gap-4">
                            <div className="space-y-4 flex-1">
                                <div className="flex items-center gap-3 text-sm">
                                    <span className="flex items-center gap-1.5 text-rose-400 bg-rose-400/10 px-2 py-0.5 rounded-full font-medium">
                                        <AlertCircle size={14} />
                                        Bị báo cáo
                                    </span>
                                    <span className="flex items-center gap-1.5 text-slate-400">
                                        <Clock size={14} />
                                        {new Date(letter.created_at).toLocaleString('vi-VN')}
                                    </span>
                                </div>
                                
                                <div className="bg-black/20 p-4 rounded-lg border border-white/5 italic text-slate-300 relative">
                                    <Mail className="absolute -top-3 -left-3 text-white/10 w-8 h-8" />
                                    "{letter.content}"
                                </div>

                                <div className="space-y-2">
                                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Lý do báo cáo:</p>
                                    <div className="flex flex-wrap gap-2">
                                        {letter.report_data?.details?.map((d: any, i: number) => (
                                            <div key={i} className="bg-white/5 px-3 py-2 rounded-lg border border-white/5">
                                                <p className="text-xs text-rose-400 font-medium capitalize">{d.category}</p>
                                                <p className="text-sm text-slate-300">{d.reason || 'Không có lý do chi tiết'}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="flex flex-col gap-2">
                                <button
                                    onClick={() => handleReview(letter.letter_id, 'keep')}
                                    className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 text-emerald-500 rounded-lg hover:bg-emerald-500/20 transition-colors"
                                >
                                    <Check size={18} />
                                    <span className="text-sm font-medium">Giữ lại</span>
                                </button>
                                <button
                                    onClick={() => handleReview(letter.letter_id, 'delete')}
                                    className="flex items-center gap-2 px-4 py-2 bg-rose-500/10 text-rose-500 rounded-lg hover:bg-rose-500/20 transition-colors"
                                >
                                    <Trash2 size={18} />
                                    <span className="text-sm font-medium">Xóa bỏ</span>
                                </button>
                            </div>
                        </div>
                    </div>
                ))}

                {loading && <div className="text-center py-10 text-slate-500">Đang tải danh sách báo cáo...</div>}
                {!loading && letters.length === 0 && (
                    <div className="text-center py-20 bg-white/5 rounded-xl border border-dashed border-white/10">
                        <Mail size={40} className="mx-auto text-slate-600 mb-4" />
                        <p className="text-slate-400">Không có lá thư nào cần kiểm duyệt.</p>
                    </div>
                )}
            </div>
        </div>
    )
}
