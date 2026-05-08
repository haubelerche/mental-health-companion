import { useEffect, useState } from 'react'
import { adminService } from '../../../services/adminService'
import { toast } from 'react-toastify'
import { Settings, Play, Square, Clock, Zap, Loader2 } from 'lucide-react'

interface WorkerAutomationCardProps {
    workerKey: string;
    icon: any;
    description: string;
}

export default function WorkerAutomationCard({ workerKey, icon: Icon, description }: WorkerAutomationCardProps) {
    const [worker, setWorker] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [updating, setUpdating] = useState(false)
    const [now, setNow] = useState(new Date())

    const fetchStatus = async () => {
        try {
            const res = await adminService.getAutomationStatus()
            if (res.workers && res.workers[workerKey]) {
                setWorker(res.workers[workerKey])
            }
        } catch (err) {
            console.error("Failed to fetch worker status", err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchStatus()
        const interval = setInterval(fetchStatus, 10000)
        const tick = setInterval(() => setNow(new Date()), 1000)
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

    const handleToggle = async () => {
        if (!worker) return
        setUpdating(true)
        try {
            await adminService.toggleWorker(workerKey, !worker.active)
            toast.success(`${worker.active ? 'Dừng' : 'Bắt đầu'} ${worker.name} thành công`)
            fetchStatus()
        } catch (err) {
            toast.error("Thao tác thất bại")
        } finally {
            setUpdating(null)
        }
    }

    const handleIntervalChange = async (newInterval: number) => {
        if (newInterval < 1) return
        try {
            await adminService.updateWorkerConfig(workerKey, newInterval)
            fetchStatus()
        } catch (err) {
            toast.error("Cập nhật thất bại")
        }
    }

    const handleTimeChange = async (newTime: string) => {
        try {
            await adminService.updateWorkerConfig(workerKey, undefined, newTime)
            fetchStatus()
        } catch (err) {
            toast.error("Cập nhật thất bại")
        }
    }

    const runNow = async () => {
        try {
            await adminService.runWorkerNow(workerKey)
            toast.success("Đã kích hoạt chạy ngay")
            fetchStatus()
        } catch (e) {
            toast.error("Không thể chạy ngay")
        }
    }

    if (loading || !worker) return <div className="h-48 admin-skeleton rounded-2xl" />

    return (
        <div className={`relative overflow-hidden bg-white/5 border rounded-2xl p-6 transition-all duration-500 ${worker.active ? 'border-indigo-500/30' : 'border-white/10'}`}>
            <div className="relative z-10 flex flex-col gap-6">
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-4">
                        <div className={`p-3 rounded-xl border transition-all ${worker.active ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400' : 'bg-white/5 border-white/10 text-slate-500'}`}>
                            <Icon size={24} />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-white tracking-tight">{worker.name}</h2>
                            <div className="flex items-center gap-2 mt-0.5">
                                <span className={`w-1.5 h-1.5 rounded-full ${worker.active ? 'bg-emerald-500 animate-ping' : 'bg-slate-600'}`} />
                                <span className={`text-[10px] font-bold uppercase tracking-widest ${worker.active ? 'text-emerald-400' : 'text-slate-500'}`}>
                                    {worker.active ? (worker.running ? 'Đang chạy...' : 'Đang chờ') : 'Đã dừng'}
                                </span>
                            </div>
                        </div>
                    </div>

                    <button 
                        onClick={handleToggle}
                        disabled={updating}
                        className={`p-2.5 rounded-lg border transition-all active:scale-90 disabled:opacity-50 ${worker.active ? 'bg-rose-500/10 border-rose-500/20 text-rose-400 hover:bg-rose-500/20' : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20'}`}
                    >
                        {worker.active ? <Square size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
                    </button>
                </div>

                <div className="grid grid-cols-2 gap-3">
                    <div className="bg-black/20 p-3 rounded-lg border border-white/5">
                        <p className="text-[9px] text-slate-500 font-bold uppercase mb-1 flex items-center gap-1">
                            <Clock size={10} /> Chạy lần cuối
                        </p>
                        <p className="text-xs text-slate-200 font-medium">{worker.last_run ? new Date(worker.last_run).toLocaleTimeString() : '---'}</p>
                    </div>
                    <div className="bg-black/20 p-3 rounded-lg border border-white/5">
                        <p className="text-[9px] text-slate-500 font-bold uppercase mb-1 flex items-center gap-1">
                            <Zap size={10} /> Đếm ngược
                        </p>
                        <p className={`text-xs font-bold ${worker.active ? 'text-indigo-400' : 'text-slate-600'}`}>
                            {worker.active ? getCountdown(worker.next_run) : '---'}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={runNow}
                        disabled={worker.running}
                        className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border text-xs font-bold transition-all ${worker.running ? 'bg-amber-500/10 border-amber-500/20 text-amber-500 cursor-not-allowed' : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'}`}
                    >
                        {worker.running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                        {worker.running ? 'Đang chạy...' : 'Chạy ngay'}
                    </button>
                    
                    <div className="flex-1">
                        <div className="flex items-center justify-between mb-1.5">
                            <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1">
                                <Settings size={10} /> {worker.daily_time ? 'Giờ gửi' : 'Tần suất'}
                            </span>
                            {worker.interval_min && (
                                <span className="text-[10px] font-bold text-indigo-400">
                                    {worker.interval_min}p
                                </span>
                            )}
                        </div>
                        {worker.daily_time !== undefined && worker.daily_time !== null ? (
                            <input 
                                type="time"
                                value={worker.daily_time}
                                onChange={(e) => handleTimeChange(e.target.value)}
                                className="w-full bg-black/20 border border-white/10 rounded-lg px-2 py-1 text-xs text-white outline-none focus:border-indigo-500 transition-all"
                            />
                        ) : (
                            <input 
                                type="range"
                                min="1"
                                max="120"
                                value={worker.interval_min || 60}
                                onChange={(e) => handleIntervalChange(parseInt(e.target.value))}
                                className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                            />
                        )}
                    </div>
                </div>
                
                <p className="text-[10px] text-slate-500 leading-relaxed italic border-t border-white/5 pt-3">
                    {description}
                </p>
            </div>
        </div>
    )
}
