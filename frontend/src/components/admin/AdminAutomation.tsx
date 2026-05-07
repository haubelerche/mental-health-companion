import { useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import { toast } from 'react-toastify'
import { Settings, Play, Square, Clock, Activity, Zap, Cpu, Bell } from 'lucide-react'
import './AdminCommon.css'

export default function AdminAutomation() {
    const [workers, setWorkers] = useState<Record<string, any>>({})
    const [loading, setLoading] = useState(true)
    const [updating, setUpdating] = useState<string | null>(null)
    const [now, setNow] = useState(new Date())

    const fetchStatus = async () => {
        try {
            const res = await adminService.getAutomationStatus()
            setWorkers(res)
        } catch (err) {
            console.error("Failed to fetch automation status", err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchStatus()
        const interval = setInterval(fetchStatus, 10000) // Poll every 10s for sync
        const tick = setInterval(() => setNow(new Date()), 1000) // Tick every 1s
        return () => {
            clearInterval(interval)
            clearInterval(tick)
        }
    }, [])

    const getCountdown = (nextRunStr: string | null) => {
        if (!nextRunStr) return null
        const nextRun = new Date(nextRunStr)
        const diff = nextRun.getTime() - now.getTime()
        if (diff <= 0) return "Đang khởi chạy..."
        const mins = Math.floor(diff / 60000)
        const secs = Math.floor((diff % 60000) / 1000)
        return `${mins}p ${secs}s`
    }

    const handleToggle = async (name: string, currentActive: boolean) => {
        setUpdating(name)
        try {
            await adminService.toggleWorker(name, !currentActive)
            toast.success(`${currentActive ? 'Dừng' : 'Bắt đầu'} worker ${name} thành công`)
            fetchStatus()
        } catch (err) {
            toast.error("Thao tác thất bại")
        } finally {
            setUpdating(null)
        }
    }

    const handleIntervalChange = async (name: string, newInterval: number) => {
        if (newInterval < 1) return
        try {
            await adminService.updateWorkerConfig(name, newInterval)
            toast.info(`Cập nhật tần suất cho ${name}: ${newInterval} phút`)
            fetchStatus()
        } catch (err) {
            toast.error("Cập nhật thất bại")
        }
    }

    if (loading && (!workers.workers || Object.keys(workers.workers).length === 0)) {
        return (
            <div className="space-y-10 animate-in fade-in duration-700">
                <div className="h-20 w-full admin-skeleton !rounded-2xl" />
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="h-64 admin-skeleton !rounded-2xl" />
                    <div className="h-64 admin-skeleton !rounded-2xl" />
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-10 pb-20">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
                        <Cpu className="text-indigo-400" />
                        Trung tâm Tự động hóa AI
                    </h1>
                    <p className="text-slate-400 mt-1">Giám sát và điều khiển các Agent chạy ngầm trong hệ thống.</p>
                </div>
                
                <div className="flex items-center gap-3 bg-indigo-500/10 px-4 py-2 rounded-xl border border-indigo-500/20">
                    <Activity size={18} className="text-indigo-400 animate-pulse" />
                    <span className="text-sm font-bold text-indigo-300 uppercase tracking-widest">Hệ thống đang trực tuyến</span>
                </div>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {Object.entries(workers.workers || {}).map(([key, worker]: [string, any]) => (
                    <div key={key} className={`relative overflow-hidden bg-white/5 border rounded-2xl p-8 transition-all duration-500 ${worker.active ? 'border-indigo-500/30' : 'border-white/10'}`}>
                        {/* Background Decoration */}
                        <div className={`absolute -top-10 -right-10 w-40 h-40 rounded-full blur-[80px] transition-all duration-1000 ${worker.active ? 'bg-indigo-500/20' : 'bg-slate-500/10'}`} />
                        
                        <div className="relative z-10 flex flex-col h-full">
                            <div className="flex items-start justify-between mb-8">
                                <div className="flex items-center gap-4">
                                    <div className={`p-4 rounded-2xl border transition-all ${worker.active ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.2)]' : 'bg-white/5 border-white/10 text-slate-500'}`}>
                                        {key === 'letter' ? <Bell size={28} /> : <Zap size={28} />}
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-bold text-white tracking-tight">{worker.name}</h2>
                                        <div className="flex items-center gap-2 mt-1">
                                            <span className={`w-2 h-2 rounded-full ${worker.active ? 'bg-emerald-500 animate-ping' : 'bg-slate-600'}`} />
                                            <span className={`text-xs font-bold uppercase tracking-widest ${worker.active ? 'text-emerald-400' : 'text-slate-500'}`}>
                                                {worker.active ? (worker.running ? 'Đang chạy...' : 'Đang chờ') : 'Đã dừng'}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <button 
                                    onClick={() => handleToggle(key, worker.active)}
                                    disabled={updating === key}
                                    className={`p-3 rounded-xl border transition-all active:scale-90 disabled:opacity-50 ${worker.active ? 'bg-rose-500/10 border-rose-500/20 text-rose-400 hover:bg-rose-500/20' : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20'}`}
                                >
                                    {worker.active ? <Square size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" />}
                                </button>
                            </div>

                            <div className="grid grid-cols-2 gap-4 mb-8">
                                <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                                    <p className="text-[10px] text-slate-500 font-bold uppercase mb-1 flex items-center gap-1">
                                        <Clock size={10} /> Chạy lần cuối
                                    </p>
                                    <p className="text-sm text-slate-200 font-medium">{worker.last_run ? new Date(worker.last_run).toLocaleTimeString() : '---'}</p>
                                </div>
                                <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                                    <p className="text-[10px] text-slate-500 font-bold uppercase mb-1 flex items-center gap-1">
                                        <Zap size={10} /> Đếm ngược
                                    </p>
                                    <p className={`text-sm font-bold ${worker.active ? 'text-indigo-400' : 'text-slate-600'}`}>
                                        {worker.active ? getCountdown(worker.next_run) : '---'}
                                    </p>
                                </div>
                            </div>

                            <div className="flex gap-3 mb-8">
                                <button
                                    onClick={async () => {
                                        try {
                                            await adminService.runWorkerNow(key)
                                            toast.success(`Đã kích hoạt ${worker.name} chạy ngay`)
                                            fetchStatus()
                                        } catch(e) {
                                            toast.error("Không thể chạy ngay")
                                        }
                                    }}
                                    disabled={worker.running}
                                    className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl border text-sm font-bold transition-all ${worker.running ? 'bg-amber-500/10 border-amber-500/20 text-amber-500 cursor-not-allowed' : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'}`}
                                >
                                    {worker.running ? (
                                        <Loader2 size={16} className="animate-spin" />
                                    ) : (
                                        <Play size={16} />
                                    )}
                                    {worker.running ? 'Đang thực hiện...' : 'Chạy ngay'}
                                </button>
                            </div>

                            <div className="mt-auto">
                                <div className="flex items-center justify-between mb-3">
                                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                        <Settings size={14} /> Tần suất hoạt động
                                    </span>
                                    <span className="text-xs font-bold text-white bg-indigo-500/20 px-2 py-0.5 rounded-md border border-indigo-500/20">
                                        {worker.interval_min} phút
                                    </span>
                                </div>
                                <input 
                                    type="range"
                                    min="1"
                                    max="120"
                                    value={worker.interval_min}
                                    onChange={(e) => handleIntervalChange(key, parseInt(e.target.value))}
                                    className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                                />
                                <div className="flex justify-between mt-2">
                                    <span className="text-[10px] text-slate-600 font-bold">1P</span>
                                    <span className="text-[10px] text-slate-600 font-bold">120P</span>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Logs Activity Box */}
            <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
                <div className="px-8 py-5 border-b border-white/10 bg-white/5 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Activity size={20} className="text-indigo-400" />
                        <h2 className="text-xl font-bold text-white tracking-tight">Nhật ký hoạt động</h2>
                    </div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-black/20 px-3 py-1 rounded-full border border-white/5">
                        Live Stream
                    </span>
                </div>
                
                <div className="p-4 bg-black/40 font-mono text-[13px] h-64 overflow-y-auto custom-scrollbar">
                    {workers.logs && workers.logs.length > 0 ? (
                        <div className="space-y-2">
                            {workers.logs.map((log: any, i: number) => (
                                <div key={i} className="flex gap-4 border-l-2 border-indigo-500/20 pl-4 py-1 hover:bg-white/5 transition-all">
                                    <span className="text-slate-600 shrink-0">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                                    <span className={`font-bold shrink-0 w-20 ${log.worker === 'letter' ? 'text-amber-400' : 'text-indigo-400'}`}>
                                        {log.worker.toUpperCase()}
                                    </span>
                                    <span className="text-slate-300">{log.message}</span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-slate-600">
                            <Activity size={32} className="mb-2 opacity-20" />
                            <p>Chưa có dữ liệu hoạt động</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Logs/Status Placeholder */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-8">
                <div className="flex items-center gap-4 mb-6">
                    <div className="p-3 bg-amber-500/10 text-amber-500 rounded-xl border border-amber-500/20">
                        <Bell size={24} />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white tracking-tight">Ghi chú vận hành</h2>
                        <p className="text-slate-400 text-sm">Hướng dẫn cấu hình các Agent tự động.</p>
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-slate-400">
                    <div className="space-y-2">
                        <p className="flex items-start gap-2">
                            <span className="text-indigo-400 font-bold">•</span>
                            <strong>Letter Responder:</strong> Tự động quét các bức thư chưa có hồi đáp sau 2 giờ và sử dụng nhân cách Tiến sĩ Serene để trả lời.
                        </p>
                        <p className="flex items-start gap-2">
                            <span className="text-indigo-400 font-bold">•</span>
                            <strong>Resource Crawler:</strong> Tự động tìm kiếm các video chữa lành mới trên YouTube, kiểm duyệt qua chuyên gia tâm lý AI và cập nhật vào kho tài nguyên.
                        </p>
                    </div>
                    <div className="space-y-2">
                        <p className="flex items-start gap-2">
                            <span className="text-amber-400 font-bold">•</span>
                            Việc thay đổi tần suất sẽ có hiệu lực ngay sau khi phiên làm việc hiện tại kết thúc hoặc sau khi bạn khởi động lại worker.
                        </p>
                        <p className="flex items-start gap-2">
                            <span className="text-rose-400 font-bold">•</span>
                            Hãy cẩn thận với tần suất quá cao (dưới 5 phút) vì có thể làm tiêu tốn nhiều Token AI và vượt quá hạn ngạch YouTube API.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
