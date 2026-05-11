import { useEffect, useState } from 'react'
import { adminService } from '../../../services/adminService'
import { toast } from 'react-toastify'
import { Settings, Play, Clock, Zap, Loader2, Trash2, Pause, History, Calendar, Repeat, CheckCircle } from 'lucide-react'

interface WorkerAutomationCardProps {
    workerKey?: string;
    trigger?: any;
    icon: any;
    description?: string;
    onEdit?: () => void;
    onDelete?: () => void;
    onRefresh?: () => void;
}

export default function WorkerAutomationCard({ 
    workerKey, 
    trigger, 
    icon: Icon, 
    description, 
    onEdit,
    onDelete,
    onRefresh
}: WorkerAutomationCardProps) {
    const [worker, setWorker] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [updating, setUpdating] = useState(false)
    const [now, setNow] = useState(new Date())
    const [showLogs, setShowLogs] = useState(false)
    const [logs, setLogs] = useState<any[]>([])
    const [loadingLogs, setLoadingLogs] = useState(false)
    const [tempValue, setTempValue] = useState<string>('')
    const [isDirty, setIsDirty] = useState(false)

    const fetchStatus = async () => {
        try {
            const res = await adminService.getAutomationStatus()
            const targetId = workerKey || trigger?.trigger_id
            if (res.workers && res.workers[targetId]) {
                setWorker(res.workers[targetId])
            } else if (trigger) {
                // Fallback if not in manager yet
                setWorker({
                    name: trigger.name,
                    active: trigger.is_active,
                    running: false,
                    last_run: trigger.last_run_at,
                    next_run: null,
                    daily_time: trigger.schedule_type === 'daily' ? trigger.schedule_value : null,
                    interval_min: trigger.schedule_type === 'interval' ? parseInt(trigger.schedule_value) : null,
                    schedule_type: trigger.schedule_type
                })
            }
        } catch (err) {
            console.error("Failed to fetch status", err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (worker) {
            setTempValue(worker.daily_time || String(worker.interval_min || ''))
            setIsDirty(false)
        }
    }, [worker?.daily_time, worker?.interval_min])

    const fetchLogs = async () => {
        setLoadingLogs(true)
        try {
            const targetId = workerKey || trigger?.trigger_id
            if (targetId) {
                const res = await adminService.getAutomationLogs(targetId)
                setLogs(res.logs)
            }
        } catch (err) {
            toast.error("Không thể lấy lịch sử")
        } finally {
            setLoadingLogs(false)
        }
    }

    useEffect(() => {
        fetchStatus()
        const interval = setInterval(fetchStatus, 15000)
        const tick = setInterval(() => setNow(new Date()), 1000)
        return () => {
            clearInterval(interval)
            clearInterval(tick)
        }
    }, [workerKey, trigger])

    const getCountdown = () => {
        if (!worker?.next_run) return "---"
        const nextRun = new Date(worker.next_run)
        const diff = nextRun.getTime() - now.getTime()
        if (diff <= 0) return "Đang khởi chạy..."
        const hours = Math.floor(diff / 3600000)
        const mins = Math.floor((diff % 3600000) / 60000)
        const secs = Math.floor((diff % 60000) / 1000)
        return `${hours > 0 ? `${hours}h ` : ''}${mins}m ${secs}s`
    }

    const handleToggle = async () => {
        setUpdating(true)
        try {
            const targetId = workerKey || trigger?.trigger_id
            await adminService.toggleWorker(targetId, !worker.active)
            toast.success(`${worker.active ? 'Đã dừng' : 'Đã bật'} tác vụ`)
            fetchStatus()
        } catch (err) {
            toast.error("Thao tác thất bại")
        } finally {
            setUpdating(false)
        }
    }

    const handleConfigSave = async () => {
        if (!isDirty) return
        setUpdating(true)
        try {
            const targetId = workerKey || trigger?.trigger_id
            const isDaily = !!worker.daily_time
            await adminService.updateWorkerConfig(
                targetId, 
                !isDaily ? parseInt(tempValue) : undefined, 
                isDaily ? tempValue : undefined
            )
            toast.success("Cập nhật lịch trình thành công")
            setIsDirty(false)
            fetchStatus()
        } catch (err) {
            toast.error("Cập nhật thất bại")
        } finally {
            setUpdating(false)
        }
    }

    const handleSwitchMode = async () => {
        setUpdating(true)
        try {
            const targetId = workerKey || trigger?.trigger_id
            const nextModeIsDaily = !worker.daily_time
            const nextValue = nextModeIsDaily ? '08:00' : '60'
            
            await adminService.updateWorkerConfig(
                targetId, 
                !nextModeIsDaily ? parseInt(nextValue) : undefined, 
                nextModeIsDaily ? nextValue : undefined
            )
            
            toast.success("Đã chuyển đổi chế độ lịch trình")
            fetchStatus()
        } catch (err) {
            toast.error("Chuyển đổi thất bại")
        } finally {
            setUpdating(false)
        }
    }

    const runNow = async () => {
        try {
            const targetId = workerKey || trigger?.trigger_id
            await adminService.runWorkerNow(targetId)
            toast.success("Đã kích hoạt chạy ngay")
            fetchStatus()
        } catch (e) {
            toast.error("Không thể chạy ngay")
        }
    }

    if (loading || !worker) return <div className="h-64 admin-skeleton rounded-[2.5rem]" />

    const isDaily = !!worker.daily_time

    return (
        <div className={`group relative overflow-hidden bg-[#1a1c2e]/40 backdrop-blur-xl border rounded-[3rem] p-8 transition-all duration-700 hover:shadow-[0_0_50px_-12px_rgba(99,102,241,0.3)] ${worker.active ? 'border-indigo-500/40 ring-1 ring-indigo-500/10' : 'border-white/5 opacity-80'}`}>
            {/* Animated Background Glow */}
            <div className={`absolute -top-24 -right-24 w-48 h-48 blur-[100px] transition-all duration-1000 ${worker.active ? 'bg-indigo-500/20' : 'bg-slate-500/10'}`} />
            
            <div className="relative z-10 flex flex-col h-full">
                {/* Header */}
                <div className="flex items-start justify-between mb-8">
                    <div className="flex items-center gap-5">
                        <div className={`relative p-5 rounded-[1.5rem] border transition-all duration-700 ${worker.active ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400 scale-110' : 'bg-white/5 border-white/10 text-slate-500'}`}>
                            <Icon size={32} />
                            {worker.running && (
                                <div className="absolute -top-1 -right-1 w-4 h-4 bg-amber-500 rounded-full border-2 border-[#1a1c2e] animate-pulse" />
                            )}
                        </div>
                        <div>
                            <h2 className="text-2xl font-black text-white tracking-tight mb-1 line-clamp-1">{worker.name}</h2>
                            <div className="flex items-center gap-2">
                                <span className={`flex items-center gap-1.5 text-[10px] font-black tracking-widest uppercase px-2 py-0.5 rounded-full border ${worker.active ? 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5' : 'text-slate-500 border-white/5 bg-white/5'}`}>
                                    <span className={`w-1.5 h-1.5 rounded-full ${worker.active ? 'bg-emerald-500 animate-pulse' : 'bg-slate-600'}`} />
                                    {worker.active ? (worker.running ? 'Đang chạy' : 'Sẵn sàng') : 'Đã tắt'}
                                </span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <button 
                            onClick={() => {
                                if (!showLogs) fetchLogs()
                                setShowLogs(!showLogs)
                            }}
                            className={`p-3.5 rounded-2xl transition-all border ${showLogs ? 'bg-indigo-500/20 border-indigo-500/30 text-indigo-400' : 'bg-white/5 border-white/10 text-slate-400 hover:text-white hover:bg-white/10'}`}
                            title="Lịch sử"
                        >
                            <History size={20} />
                        </button>
                        <button 
                            onClick={handleToggle}
                            disabled={updating}
                            className={`p-4 rounded-2xl border transition-all duration-500 active:scale-90 ${worker.active ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20' : 'bg-white/5 border-white/10 text-slate-500 hover:bg-white/10'}`}
                        >
                            {worker.active ? <Pause size={22} fill="currentColor" /> : <Play size={22} className="opacity-50" />}
                        </button>
                    </div>
                </div>

                {/* Main Status / Countdown */}
                {!showLogs && (
                    <div className="flex-1 flex flex-col gap-6">
                        <div className="relative group/time bg-gradient-to-br from-white/[0.03] to-transparent p-6 rounded-[2rem] border border-white/5 flex flex-col items-center justify-center min-h-[120px] transition-all hover:border-indigo-500/20">
                            <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.3em] mb-3 flex items-center gap-2">
                                <Zap size={12} className={worker.active ? 'text-amber-400' : 'text-slate-600'} /> 
                                {worker.active ? 'Sắp thực thi trong' : 'Lịch trình kế tiếp'}
                            </p>
                            <div className={`text-4xl font-black tracking-tighter tabular-nums ${worker.active ? 'text-white' : 'text-slate-700'}`}>
                                {worker.active ? getCountdown() : '---'}
                            </div>
                            <div className="absolute bottom-4 right-6 flex items-center gap-4 text-[10px] font-bold text-slate-500">
                                <span className="flex items-center gap-1.5"><Clock size={10} /> Chạy cuối: {worker.last_run ? new Date(worker.last_run).toLocaleTimeString('vi-VN', {hour:'2-digit', minute:'2-digit'}) : '--:--'}</span>
                            </div>
                        </div>

                        {/* Smart Schedule Config */}
                            <div className="flex-1 bg-black/40 p-2 rounded-[2rem] border border-white/10 flex items-center shadow-inner">
                                <button 
                                    onClick={handleSwitchMode}
                                    disabled={updating}
                                    className="ml-2 p-3 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-indigo-400 transition-all active:scale-90"
                                    title="Chuyển đổi chế độ (Daily / Interval)"
                                >
                                    {isDaily ? <Repeat size={14} /> : <Calendar size={14} />}
                                </button>
                                <div className="flex-1 flex items-center gap-3 px-4">
                                    {isDaily ? <Calendar size={16} className="text-indigo-400" /> : <Repeat size={16} className="text-amber-400" />}
                                    <div className="flex-1">
                                        <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest block mb-0.5">
                                            {isDaily ? 'Giờ chạy cố định' : 'Chu kỳ (Phút)'}
                                        </span>
                                        <div className="flex items-center gap-2">
                                            <input 
                                                type={isDaily ? "time" : "number"}
                                                value={tempValue}
                                                onChange={(e) => {
                                                    setTempValue(e.target.value)
                                                    setIsDirty(true)
                                                }}
                                                className="bg-transparent text-sm font-black text-white outline-none border-none w-full placeholder:text-slate-700"
                                                placeholder={isDaily ? "--:--" : "Nhập số phút..."}
                                            />
                                            {isDirty && (
                                                <button 
                                                    onClick={handleConfigSave}
                                                    className="p-1.5 bg-indigo-500 text-white rounded-lg animate-in zoom-in-50 duration-300 shadow-lg shadow-indigo-500/20"
                                                    title="Lưu thay đổi"
                                                >
                                                    <CheckCircle size={14} />
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            <button 
                                onClick={runNow}
                                disabled={worker.running || !worker.active}
                                className={`p-4 rounded-[1.5rem] transition-all ${worker.running ? 'bg-amber-500/20 text-amber-500' : 'bg-white/5 text-slate-400 hover:bg-indigo-500/20 hover:text-indigo-400 hover:scale-105 active:scale-95 disabled:opacity-30'}`}
                                title="Chạy ngay lập tức"
                            >
                                {worker.running ? <Loader2 size={18} className="animate-spin" /> : <Play size={18} />}
                            </button>
                        </div>
                    </div>
                )}

                {/* Logs View */}
                {showLogs && (
                    <div className="flex-1 flex flex-col animate-in fade-in zoom-in-95 duration-500">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xs font-black uppercase tracking-widest text-indigo-400 flex items-center gap-2">
                                <History size={14} /> Lịch sử hoạt động
                            </h3>
                            <button onClick={fetchLogs} className="text-[10px] font-bold text-slate-500 hover:text-white transition-colors">Làm mới</button>
                        </div>
                        <div className="flex-1 bg-[#0f111a]/60 rounded-[2rem] border border-white/5 overflow-hidden flex flex-col">
                            <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
                                {loadingLogs ? (
                                    <div className="h-full flex items-center justify-center"><Loader2 size={24} className="animate-spin text-indigo-500/50" /></div>
                                ) : logs.length > 0 ? (
                                    logs.map((log: any) => (
                                        <div key={log.log_id} className="group/log relative pl-4 border-l-2 border-white/5 hover:border-indigo-500/30 transition-all">
                                            <div className="flex items-center justify-between gap-3 mb-1">
                                                <span className={`text-[9px] font-black px-1.5 py-0.5 rounded-full ${log.status === 'success' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                                                    {log.status === 'success' ? 'SUCCESS' : 'FAILED'}
                                                </span>
                                                <span className="text-[9px] text-slate-600 font-bold">{new Date(log.created_at).toLocaleTimeString('vi-VN')}</span>
                                            </div>
                                            <p className="text-[11px] text-slate-300 font-medium line-clamp-2 mb-1">{log.message}</p>
                                            
                                            {/* Enhanced Details View */}
                                            {log.details && (
                                                <div className="mt-2 space-y-2">
                                                    {log.details.action === 'push_notifications' && (
                                                        <div className="p-2.5 bg-indigo-500/5 rounded-xl border border-indigo-500/10">
                                                            <div className="flex items-center justify-between text-[9px] font-black text-indigo-400 uppercase mb-1">
                                                                <span>Chiến dịch: {log.details.category}</span>
                                                                <span>{log.details.user_count} Users</span>
                                                            </div>
                                                            <p className="text-[10px] text-slate-400 leading-relaxed italic">"{log.details.body}"</p>
                                                        </div>
                                                    )}
                                                    
                                                    {log.details.action === 'crawl_resources' && log.details.titles && log.details.titles.length > 0 && (
                                                        <div className="p-2.5 bg-amber-500/5 rounded-xl border border-amber-500/10">
                                                            <p className="text-[9px] font-black text-amber-400 uppercase mb-2 flex items-center gap-1">
                                                                <Database size={10} /> Danh sách tài nguyên mới ({log.details.count})
                                                            </p>
                                                            <ul className="space-y-1">
                                                                {log.details.titles.map((t: string, i: number) => (
                                                                    <li key={i} className="text-[10px] text-slate-400 flex items-start gap-1.5">
                                                                        <span className="text-amber-500/50">•</span>
                                                                        <span className="line-clamp-1">{t}</span>
                                                                    </li>
                                                                ))}
                                                            </ul>
                                                        </div>
                                                    )}

                                                    {log.details.action === 'ai_reply_letters' && (
                                                        <div className="p-2.5 bg-emerald-500/5 rounded-xl border border-emerald-500/10">
                                                            <p className="text-[10px] text-emerald-400 font-bold italic">
                                                                ✓ Đã xử lý xong {log.details.count} lá thư tồn đọng trong hệ thống.
                                                            </p>
                                                        </div>
                                                    )}

                                                    {/* Fallback for other details */}
                                                    {!log.details.action && Object.keys(log.details).length > 0 && (
                                                        <div className="hidden group-hover/log:block bg-black/40 rounded-xl p-2">
                                                            <pre className="text-[8px] text-indigo-300/60 font-mono">
                                                                {JSON.stringify(log.details, null, 2)}
                                                            </pre>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    ))
                                ) : (
                                    <div className="h-full flex items-center justify-center text-slate-600 font-bold text-xs italic">Chưa có nhật ký</div>
                                )}
                            </div>
                            <button 
                                onClick={() => setShowLogs(false)}
                                className="w-full p-4 bg-white/5 hover:bg-white/10 text-[10px] font-black text-slate-500 hover:text-white uppercase tracking-widest transition-all border-t border-white/5"
                            >
                                Quay lại bảng điều khiển
                            </button>
                        </div>
                    </div>
                )}

                {/* Footer Actions */}
                {!showLogs && (
                    <div className="mt-8 pt-6 border-t border-white/5 flex items-center justify-between">
                        <p className="text-[11px] text-slate-500 font-medium italic line-clamp-1 flex-1 mr-4">
                            {description || "Hệ thống tự động hóa Serene AI"}
                        </p>
                        <div className="flex items-center gap-1">
                            {onEdit && (
                                <button onClick={onEdit} className="p-2.5 text-slate-500 hover:text-white hover:bg-white/5 rounded-xl transition-all" title="Cấu hình nâng cao">
                                    <Settings size={18} />
                                </button>
                            )}
                            {onDelete && (
                                <button onClick={onDelete} className="p-2.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-xl transition-all" title="Xóa tác vụ">
                                    <Trash2 size={18} />
                                </button>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
