import { useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import { ApiRequestError } from '../../api/types'
import { toast } from 'react-toastify'
import { Bell, Send, Info, Coffee, Sparkles, MessageCircle, Activity } from 'lucide-react'
import WorkerAutomationCard from './automation/WorkerAutomationCard'

const TEMPLATES = [
    {
        id: 'morning',
        icon: Coffee,
        title: 'Chào buổi sáng',
        body: 'Chào buổi sáng bạn nhé! Đừng quên dành 5 phút check-in tâm trạng hôm nay cùng Serene nhé. 🌿',
        category: 'morning'
    },
    {
        id: 'checkin_reminder',
        icon: Sparkles,
        title: 'Nhắc nhở tự chăm sóc',
        body: 'Bạn ơi, hôm nay bạn đã dành thời gian cho bản thân chưa? Một chút nhạc thư giãn có thể giúp bạn cảm thấy tốt hơn đấy. ❤️',
        category: 'reminder'
    },
    {
        id: 'letter_promo',
        icon: MessageCircle,
        title: 'Gửi trao tâm tình',
        body: 'Hôm nay có rất nhiều lá thư ẩn danh đang đợi được hồi đáp. Hãy ghé qua hòm thư để chia sẻ sự thấu cảm cùng mọi người nhé! 💌',
        category: 'letters'
    }
]

export default function AdminNotifications() {
    const [title, setTitle] = useState('')
    const [body, setBody] = useState('')
    const [category, setCategory] = useState('general')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<any>(null)
    const [logs, setLogs] = useState<any[]>([])

    const fetchLogs = async () => {
        try {
            const res = await adminService.getAutomationStatus()
            const notifLogs = (res.logs || []).filter((l: any) => l.worker.startsWith('notif_')).slice(0, 5)
            setLogs(notifLogs)
        } catch (err) {}
    }

    useEffect(() => {
        fetchLogs()
        const inv = setInterval(fetchLogs, 15000)
        return () => clearInterval(inv)
    }, [])

    const applyTemplate = (tpl: typeof TEMPLATES[0]) => {
        setTitle(tpl.title)
        setBody(tpl.body)
        setCategory(tpl.category)
    }

    const handleBroadcast = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!body.trim()) {
            toast.error('Nội dung thông báo không được để trống')
            return
        }

        setLoading(true)
        setResult(null)
        try {
            const res = await adminService.broadcastNotification({ title, body, category })
            setResult(res)
            toast.success(`Đã gửi thông báo đến ${res.sent_to_count} người dùng!`)
            // Reset form
            setTitle('')
            setBody('')
        } catch (err) {
            if (err instanceof ApiRequestError && err.handledByModal) return
            toast.error('Không thể gửi thông báo hàng loạt')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="space-y-8">
            <header>
                <h1 className="text-2xl font-bold text-white">Trung tâm Thông báo</h1>
                <p className="text-slate-400">Gửi thông báo hàng loạt đến toàn bộ người dùng đang hoạt động.</p>
            </header>


            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Templates Section */}
                <div className="space-y-4">
                    <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                        <Sparkles size={16} />
                        Mẫu thông báo (Templates)
                    </h2>
                    <div className="grid grid-cols-1 gap-3">
                        {TEMPLATES.map((tpl) => (
                            <button
                                key={tpl.id}
                                onClick={() => applyTemplate(tpl)}
                                className="text-left p-4 bg-white/5 border border-white/10 rounded-xl hover:border-indigo-500/50 hover:bg-white/10 transition-all group"
                            >
                                <div className="flex items-center gap-3 mb-2">
                                    <div className="p-2 bg-indigo-500/20 rounded-lg text-indigo-400 group-hover:scale-110 transition-transform">
                                        {(() => {
                                            const Icon = tpl.icon
                                            return <Icon size={18} />
                                        })()}
                                    </div>
                                    <span className="font-bold text-white">{tpl.title}</span>
                                </div>
                                <p className="text-xs text-slate-400 line-clamp-2">{tpl.body}</p>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Form Section */}
                <div className="lg:col-span-2 space-y-6">
                    <form onSubmit={handleBroadcast} className="bg-white/5 border border-white/10 rounded-2xl p-6 space-y-6 shadow-xl shadow-black/20">
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-slate-500 uppercase">Tiêu đề (Tùy chọn)</label>
                                    <input
                                        type="text"
                                        value={title}
                                        onChange={(e) => setTitle(e.target.value)}
                                        placeholder="📢 Thông báo hệ thống"
                                        className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-indigo-500 outline-none transition-all"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-slate-500 uppercase">Phân loại (Category)</label>
                                    <select
                                        value={category}
                                        onChange={(e) => setCategory(e.target.value)}
                                        className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-indigo-500 outline-none transition-all"
                                    >
                                        <option value="general">Chung (General)</option>
                                        <option value="morning">Chào buổi sáng</option>
                                        <option value="reminder">Nhắc nhở</option>
                                        <option value="letters">Hòm thư</option>
                                        <option value="update">Cập nhật hệ thống</option>
                                    </select>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-bold text-slate-500 uppercase">Nội dung thông báo</label>
                                <textarea
                                    value={body}
                                    onChange={(e) => setBody(e.target.value)}
                                    placeholder="Nhập nội dung tin nhắn muốn gửi đến người dùng..."
                                    rows={4}
                                    className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-indigo-500 outline-none transition-all resize-none"
                                    required
                                />
                            </div>
                        </div>

                        <div className="flex items-center justify-between gap-4 pt-4 border-t border-white/5">
                            <div className="flex items-center gap-2 text-xs text-amber-400 bg-amber-400/10 px-3 py-2 rounded-lg">
                                <Info size={14} />
                                Tin nhắn sẽ được gửi đến tất cả người dùng đang hoạt động.
                            </div>
                            <button
                                type="submit"
                                disabled={loading}
                                className="flex items-center gap-2 px-8 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl font-bold transition-all shadow-lg shadow-indigo-500/20"
                            >
                                {loading ? <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> : <Send size={18} />}
                                Gửi hàng loạt
                            </button>
                        </div>
                    </form>

                    {result && (
                        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-6 flex items-center justify-between animate-in fade-in slide-in-from-top-2">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-emerald-500/20 rounded-full text-emerald-500">
                                    <Bell size={24} />
                                </div>
                                <div>
                                    <h3 className="font-bold text-white">Gửi thành công!</h3>
                                    <p className="text-sm text-slate-400">Đã đẩy {result.sent_to_count} tin nhắn vào hàng chờ hệ thống.</p>
                                </div>
                            </div>
                            <button onClick={() => setResult(null)} className="text-slate-500 hover:text-white transition-colors">Đóng</button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
