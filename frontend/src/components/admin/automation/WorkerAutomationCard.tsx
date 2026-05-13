/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from 'react'
import { adminService } from '../../../services/adminService'
import { toast } from 'react-toastify'
import { Settings, Play, Clock, Zap, Loader2, Trash2, Pause, History, Calendar, Repeat, CheckCircle, Database, Mail, ArrowRight, ExternalLink } from 'lucide-react'

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
        } catch {
            console.error("Failed to fetch status")
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (worker) {
            setTempValue(worker.daily_time || String(worker.interval_min || ''))
            setIsDirty(false)
        }
    }, [worker])

    const fetchLogs = async () => {
        setLoadingLogs(true)
        try {
            const targetId = workerKey || trigger?.trigger_id
            if (targetId) {
                const res = await adminService.getAutomationLogs(targetId)
                setLogs(res.logs)
            }
        } catch {
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
        // eslint-disable-next-line react-hooks/exhaustive-deps
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
            onRefresh?.()
            fetchStatus()
        } catch {
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
            onRefresh?.()
            fetchStatus()
        } catch {
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
            onRefresh?.()
            fetchStatus()
        } catch {
            toast.error("Chuyển đổi thất bại")
        } finally {
            setUpdating(false)
        }
    }

    const runNow = async () => {
        setUpdating(true)
        try {
            const targetId = workerKey || trigger?.trigger_id
            await adminService.runWorkerNow(targetId)
            toast.success("Đã kích hoạt chạy ngay")
            onRefresh?.()
            fetchStatus()
        } catch {
            toast.error("Không thể chạy ngay")
        } finally {
            setUpdating(false)
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
                            className={`p-4 rounded-2xl border transition-all duration-500 active:scale-90 ${worker.active ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20' : 'bg-white/5 border-white/10 text-slate-500 hover:bg-white/10'} disabled:opacity-50`}
                        >
                            {updating ? <Loader2 size={22} className="animate-spin" /> : (worker.active ? <Pause size={22} fill="currentColor" /> : <Play size={22} className="opacity-50" />)}
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
                                    className="ml-2 p-3 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-indigo-400 transition-all active:scale-90 disabled:opacity-50"
                                    title="Chuyển đổi chế độ (Daily / Interval)"
                                >
                                    {updating ? <Loader2 size={14} className="animate-spin" /> : (isDaily ? <Repeat size={14} /> : <Calendar size={14} />)}
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
                                disabled={worker.running || !worker.active || updating}
                                className={`p-4 rounded-[1.5rem] transition-all ${worker.running || updating ? 'bg-amber-500/20 text-amber-500' : 'bg-white/5 text-slate-400 hover:bg-indigo-500/20 hover:text-indigo-400 hover:scale-105 active:scale-95 disabled:opacity-30'}`}
                                title="Chuyển đổi chế độ (Daily / Interval)"
                            >
                                {worker.running || updating ? <Loader2 size={18} className="animate-spin" /> : <Play size={18} />}
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
                                            <p className="text-[11px] text-slate-200 font-bold mb-2">{log.message}</p>
                                            
                                            {/* Enhanced Details View */}
                                            {/* Enhanced Details View */}
                                            {log.details && (
                                                <div className="mt-3 space-y-3">
                                                    {/* Push Notifications (New & Old format) */}
                                                    {(log.details.action === 'push_notifications' || (log.details.user_count && log.details.body)) && (
                                                        <div className="p-3 bg-indigo-500/5 rounded-2xl border border-indigo-500/10">
                                                            <div className="flex items-center justify-between text-[9px] font-black text-indigo-400 uppercase mb-2">
                                                                <span>Chiến dịch: {log.details.category || 'N/A'}</span>
                                                                <span>{log.details.user_count} Users</span>
                                                            </div>
                                                            {log.details.body && <p className="text-[10px] text-slate-400 leading-relaxed italic">"{log.details.body}"</p>}
                                                        </div>
                                                    )}

                                                    {/* YouTube Crawler (New format) */}
                                                    {log.details.action === 'youtube_crawl' && log.details.items && (
                                                        <div className="p-3 bg-amber-500/5 rounded-2xl border border-amber-500/10">
                                                            <div className="flex items-center justify-between text-[9px] font-black text-amber-400 uppercase mb-3">
                                                                <span className="flex items-center gap-2"><Database size={12} /> Chủ đề: {log.details.category}</span>
                                                                <span>{log.details.inserted_count}/{log.details.total_processed} mới</span>
                                                            </div>
                                                            <div className="space-y-2">
                                                                {log.details.items.slice(0, 5).map((item: any, i: number) => (
                                                                    <div key={i} className="flex items-center gap-3 bg-white/5 p-2 rounded-xl border border-white/5">
                                                                        {item.thumbnail && <img src={item.thumbnail} alt="" className="w-10 h-10 rounded-lg object-cover flex-shrink-0" />}
                                                                        <div className="flex-1 min-w-0">
                                                                            <p className="text-[10px] text-white font-bold line-clamp-1">{item.title}</p>
                                                                            <span className={`text-[8px] font-black uppercase tracking-tighter ${item.status === 'inserted' ? 'text-emerald-400' : 'text-slate-500'}`}>
                                                                                {item.status === 'inserted' ? 'Đã thêm mới' : 'Đã tồn tại'}
                                                                            </span>
                                                                        </div>
                                                                        {item.url && (
                                                                            <a href={item.url} target="_blank" rel="noreferrer" className="p-1.5 text-slate-500 hover:text-white transition-colors">
                                                                                <ExternalLink size={10} />
                                                                            </a>
                                                                        )}
                                                                    </div>
                                                                ))}
                                                                {log.details.items.length > 5 && (
                                                                    <p className="text-[9px] text-slate-600 text-center font-bold pt-1">và {log.details.items.length - 5} tài nguyên khác...</p>
                                                                )}
                                                            </div>
                                                        </div>
                                                    )}

                                                    {/* YouTube Crawler (Old format / Legacy) */}
                                                    {!log.details.action && log.details.category && !log.details.body && (
                                                        <div className="p-3 bg-amber-500/5 rounded-2xl border border-amber-500/10">
                                                            <div className="flex items-center justify-between text-[9px] font-black text-amber-400 uppercase">
                                                                <span className="flex items-center gap-2"><Database size={12} /> Chủ đề: {log.details.category}</span>
                                                                {log.details.count !== undefined && <span>{log.details.count} tài nguyên</span>}
                                                            </div>
                                                            {log.details.titles && log.details.titles.length > 0 && (
                                                                <ul className="mt-2 space-y-1">
                                                                    {log.details.titles.map((t: string, i: number) => (
                                                                        <li key={i} className="text-[10px] text-slate-400 flex items-start gap-1.5">
                                                                            <span className="text-amber-500/50">•</span>
                                                                            <span className="line-clamp-1">{t}</span>
                                                                        </li>
                                                                    ))}
                                                                </ul>
                                                            )}
                                                        </div>
                                                    )}
                                                    
                                                    {/* AI Reply Letters (New & Old format) */}
                                                    {(log.details.action === 'ai_reply_letters' || (log.details.count !== undefined && !log.details.category)) && (
                                                        <div className="p-3 bg-emerald-500/5 rounded-2xl border border-emerald-500/10">
                                                            <div className="flex items-center justify-between text-[9px] font-black text-emerald-400 uppercase mb-2">
                                                                <span className="flex items-center gap-2"><Mail size={12} /> Phản hồi: {log.details.count} lá thư</span>
                                                                {log.details.duration_sec && (
                                                                    <span className="flex items-center gap-1 text-slate-500"><Clock size={10} /> {log.details.duration_sec}s</span>
                                                                )}
                                                            </div>
                                                            {log.details.replied_items && (
                                                                <div className="space-y-3 mt-3">
                                                                    {log.details.replied_items.slice(0, 3).map((item: any, i: number) => (
                                                                        <div key={i} className="space-y-1.5 border-b border-white/5 pb-2 last:border-0 last:pb-0">
                                                                            <div className="flex items-center gap-2 text-[9px] text-slate-400 font-bold">
                                                                                <span className="bg-white/10 px-1.5 py-0.5 rounded uppercase">{item.letter_id}</span>
                                                                                <ArrowRight size={8} />
                                                                                <span className="text-emerald-400/70 italic">AI Replying...</span>
                                                                            </div>
                                                                            <p className="text-[10px] text-slate-300 line-clamp-1 italic">"{item.content_brief}"</p>
                                                                            <p className="text-[10px] text-emerald-400/80 line-clamp-1 font-medium bg-emerald-500/5 p-1.5 rounded-lg border border-emerald-500/10">
                                                                                {item.reply_brief}
                                                                            </p>
                                                                        </div>
                                                                    ))}
                                                                    {log.details.replied_items.length > 3 && (
                                                                        <p className="text-[9px] text-slate-600 text-center font-bold pt-1">và {log.details.replied_items.length - 3} thư khác...</p>
                                                                    )}
                                                                </div>
                                                            )}
                                                            {log.details.count === 0 && (
                                                                <p className="text-[10px] text-slate-500 italic text-center">Không có thư mới cần phản hồi.</p>
                                                            )}
                                                        </div>
                                                    )}

                                                    {/* Fallback for other details */}
                                                    {Object.keys(log.details).length > 0 && 
                                                     !log.details.action && 
                                                     !log.details.category && 
                                                     log.details.count === undefined && (
                                                        <div className="group-hover/log:block bg-black/40 rounded-xl p-2">
                                                            <pre className="text-[8px] text-indigo-300/60 font-mono overflow-x-auto">
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
