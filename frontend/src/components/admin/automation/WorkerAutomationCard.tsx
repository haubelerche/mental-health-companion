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
            setUpdating(false)
        }
    }

    const handleConfigChange = async (type: 'daily' | 'interval', value: string) => {
        try {
            await adminService.updateWorkerConfig(workerKey, type === 'interval' ? parseInt(value) : undefined, type === 'daily' ? value : undefined)
            toast.success("Đã cập nhật lịch trình")
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
        <div className={`relative overflow-hidden bg-[#1a1c2e]/50 backdrop-blur-md border rounded-[2.5rem] p-8 transition-all duration-500 hover:shadow-2xl hover:shadow-indigo-500/10 ${worker.active ? 'border-indigo-500/30 ring-1 ring-indigo-500/10' : 'border-white/5'}`}>
            <div className="relative z-10 flex flex-col gap-8">
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-5">
                        <div className={`p-4 rounded-2xl border transition-all duration-500 ${worker.active ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400' : 'bg-white/5 border-white/10 text-slate-500'}`}>
                            <Icon size={28} />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-white tracking-tight leading-none mb-2">{worker.name}</h2>
                            <div className="flex items-center gap-2">
                                <span className={`w-2 h-2 rounded-full ${worker.active ? 'bg-emerald-500 animate-pulse' : 'bg-slate-600'}`} />
                                <span className={`text-[10px] font-black uppercase tracking-[0.2em] ${worker.active ? 'text-emerald-400' : 'text-slate-500'}`}>
                                    {worker.active ? (worker.running ? 'ĐANG CHẠY' : 'ĐÃ BẬT') : 'ĐÃ DỪNG'}
                                </span>
                            </div>
                        </div>
                    </div>

                    <button 
                        onClick={handleToggle}
                        disabled={updating}
                        className={`p-4 rounded-2xl border transition-all duration-300 active:scale-90 disabled:opacity-50 ${worker.active ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20' : 'bg-white/5 border-white/10 text-slate-500 hover:bg-white/10'}`}
                    >
                        {worker.active ? <Play size={20} fill="currentColor" /> : <Play size={20} className="opacity-50" />}
                    </button>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-[#0f111a]/60 p-4 rounded-2xl border border-white/5 group/kpi transition-colors hover:border-indigo-500/20">
                        <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mb-2 flex items-center gap-2">
                            <Clock size={12} className="text-indigo-400" /> Chạy lần cuối
                        </p>
                        <p className="text-sm text-slate-200 font-bold tracking-tight">
                            {worker.last_run ? new Date(worker.last_run).toLocaleTimeString('vi-VN') : '---'}
                        </p>
                    </div>
                    <div className="bg-[#0f111a]/60 p-4 rounded-2xl border border-white/5 group/kpi transition-colors hover:border-indigo-500/20">
                        <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mb-2 flex items-center gap-2">
                            <Zap size={12} className="text-amber-400" /> Đếm ngược
                        </p>
                        <p className={`text-sm font-black tracking-tight ${worker.active ? 'text-indigo-400' : 'text-slate-600'}`}>
                            {worker.active ? getCountdown(worker.next_run) : '---'}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <button
                        onClick={runNow}
                        disabled={worker.running || updating}
                        className={`group flex items-center justify-center gap-3 px-6 py-4 rounded-2xl border text-sm font-bold transition-all ${worker.running ? 'bg-amber-500/10 border-amber-500/20 text-amber-500' : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10 hover:border-white/20 active:scale-95'}`}
                    >
                        {worker.running ? <Loader2 size={18} className="animate-spin" /> : <Play size={18} className="group-hover:translate-x-0.5 transition-transform" />}
                        {worker.running ? 'Đang chạy...' : 'Chạy ngay'}
                    </button>
                    
                    <div className="flex-1 bg-[#0f111a]/40 p-1.5 rounded-2xl border border-white/5 flex items-center gap-2">
                        <div className="flex-1 px-3">
                            <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest block mb-1">
                                {worker.daily_time ? 'Giờ gửi' : 'Tần suất'}
                            </span>
                            {worker.daily_time ? (
                                <input 
                                    type="time"
                                    value={worker.daily_time}
                                    onChange={(e) => handleConfigChange('daily', e.target.value)}
                                    className="bg-transparent text-sm font-bold text-white outline-none border-none w-full"
                                />
                            ) : (
                                <div className="flex items-center gap-2">
                                    <input 
                                        type="range"
                                        min="5"
                                        max="120"
                                        step="5"
                                        value={worker.interval_min || 60}
                                        onChange={(e) => handleConfigChange('interval', e.target.value)}
                                        className="flex-1 h-1 bg-white/10 rounded-full appearance-none cursor-pointer accent-indigo-500"
                                    />
                                    <span className="text-xs font-black text-indigo-400 min-w-[30px]">{worker.interval_min}p</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
                
                <p className="text-xs text-slate-500 leading-relaxed font-medium italic border-t border-white/5 pt-5 px-1">
                    {description}
                </p>
            </div>
        </div>
    )
}
