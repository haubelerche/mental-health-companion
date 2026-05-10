import React, { useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import { toast } from 'react-toastify'
import { 
    Zap, 
    Plus, 
    Settings, 
    Play, 
    Pause, 
    Trash2, 
    Clock, 
    Shield, 
    Activity, 
    Bell, 
    Search,
    Brain,
    Database,
    Globe,
    ChevronRight,
    Loader2,
    Mail
} from 'lucide-react'
import WorkerAutomationCard from './automation/WorkerAutomationCard'

type Trigger = {
    trigger_id: string
    name: string
    trigger_type: 'fixed' | 'custom'
    action_key: 'batch_notification' | 'ai_moderation' | 'resource_crawler' | 'custom_webhook' | 'daily_reminder'
    config: any
    schedule_type: 'daily' | 'interval'
    schedule_value: string
    is_active: boolean
    last_run_at: string | null
    created_at: string
}

export default function AdminAutomation() {
    const [triggers, setTriggers] = useState<Trigger[]>([])
    const [loading, setLoading] = useState(true)
    const [isModalOpen, setIsModalOpen] = useState(false)
    const [editingTrigger, setEditingTrigger] = useState<Trigger | null>(null)
    const [formData, setFormData] = useState({
        name: '',
        action_key: 'batch_notification',
        schedule_type: 'daily',
        schedule_value: '09:00',
        config: '{}'
    })

    const fetchTriggers = async () => {
        setLoading(true)
        try {
            const res = await adminService.listAutomationTriggers()
            setTriggers(res.triggers)
        } catch (err) {
            toast.error('Không thể tải danh sách triggers')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchTriggers()
    }, [])

    const handleToggle = async (trigger: Trigger) => {
        try {
            await adminService.updateAutomationTrigger(trigger.trigger_id, { is_active: !trigger.is_active })
            setTriggers(prev => prev.map(t => t.trigger_id === trigger.trigger_id ? { ...t, is_active: !t.is_active } : t))
            toast.success(`${trigger.is_active ? 'Đã tắt' : 'Đã bật'} trigger ${trigger.name}`)
        } catch (err) {
            toast.error('Thao tác thất bại')
        }
    }

    const handleDelete = async (triggerId: string) => {
        if (!confirm('Bạn có chắc chắn muốn xóa trigger này?')) return
        try {
            await adminService.deleteAutomationTrigger(triggerId)
            setTriggers(prev => prev.filter(t => t.trigger_id !== triggerId))
            toast.success('Đã xóa trigger')
        } catch (err) {
            toast.error('Không thể xóa trigger')
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            const configObj = JSON.parse(formData.config)
            const payload = {
                name: formData.name,
                action_key: formData.action_key,
                schedule_type: (formData as any).schedule_type,
                schedule_value: (formData as any).schedule_value,
                config: configObj
            }
            if (editingTrigger) {
                await adminService.updateAutomationTrigger(editingTrigger.trigger_id, payload)
                toast.success('Đã cập nhật trigger thành công')
            } else {
                await adminService.createAutomationTrigger(payload)
                toast.success('Đã kích hoạt trigger mới')
            }
            setIsModalOpen(false)
            fetchTriggers()
        } catch (err) {
            toast.error('Dữ liệu JSON không hợp lệ hoặc lỗi kết nối')
        }
    }

    const getActionIcon = (key: string) => {
        switch (key) {
            case 'batch_notification': return <Bell className="text-amber-400" size={18} />
            case 'ai_moderation': return <Brain className="text-indigo-400" size={18} />
            case 'resource_crawler': return <Database className="text-emerald-400" size={18} />
            default: return <Globe className="text-slate-400" size={18} />
        }
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                    <div className="flex items-center gap-3 mb-1">
                        <div className="p-2 bg-indigo-500/20 rounded-lg">
                            <Zap className="text-indigo-400 w-5 h-5" />
                        </div>
                        <h1 className="text-2xl font-bold text-white">Automation Triggers</h1>
                    </div>
                    <p className="text-slate-400 text-sm">Quản lý và cấu hình các tác vụ tự động hóa hệ thống.</p>
                </div>
                
                <button 
                    onClick={() => {
                        setEditingTrigger(null)
                        setFormData({ name: '', action_key: 'batch_notification', schedule_type: 'daily', schedule_value: '09:00', config: '{}' })
                        setIsModalOpen(true)
                    }}
                    className="flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl font-bold transition-all shadow-lg shadow-indigo-600/20 active:scale-95"
                >
                    <Plus size={18} />
                    Thêm Trigger mới
                </button>
            </header>

                    <section className="space-y-6">
                <h2 className="text-sm font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-3">
                    <Shield size={16} className="text-indigo-400" /> Worker Hệ thống
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
                    <WorkerAutomationCard 
                        workerKey="letter" 
                        icon={Brain} 
                        description="Tự động trả lời thư Public chưa có hồi đáp sau ngưỡng thời gian cấu hình."
                    />
                    <WorkerAutomationCard 
                        workerKey="resource" 
                        icon={Database} 
                        description="Tự động quét và cập nhật tài nguyên từ YouTube dựa trên xu hướng tâm trạng."
                    />
                    <WorkerAutomationCard 
                        workerKey="notif_morning" 
                        icon={Bell} 
                        description="Gửi lời chào & nhắc nhở check-in buổi sáng (07:00 AM)."
                    />
                    <WorkerAutomationCard 
                        workerKey="notif_reminder" 
                        icon={Activity} 
                        description="Nhắc nhở người dùng dành thời gian tự chăm sóc bản thân (02:00 PM)."
                    />
                    <WorkerAutomationCard 
                        workerKey="notif_letters" 
                        icon={Mail} 
                        description="Khuyến khích người dùng tham gia viết/trả lời thư (08:00 PM)."
                    />
                </div>
            </section>

            <section className="space-y-6">
                <div className="flex items-center justify-between">
                    <h2 className="text-sm font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-3">
                        <Zap size={16} className="text-amber-400" /> Triggers Tùy chỉnh
                    </h2>
                    <div className="h-[1px] flex-1 bg-white/5 mx-6" />
                </div>

                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {[1, 2].map(i => (
                            <div key={i} className="h-64 bg-white/5 border border-white/10 rounded-[2.5rem] animate-pulse" />
                        ))}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {triggers.map((trigger) => (
                            <div 
                                key={trigger.trigger_id} 
                                className={`group relative bg-[#1a1c2e]/50 backdrop-blur-md border rounded-[2.5rem] p-8 transition-all duration-500 hover:shadow-2xl hover:shadow-amber-500/10 ${trigger.is_active ? 'border-amber-500/20' : 'border-white/5'}`}
                            >
                                <div className="flex items-start justify-between mb-8">
                                    <div className={`p-4 rounded-2xl border transition-all ${trigger.is_active ? 'bg-amber-500/10 border-amber-500/20 text-amber-400' : 'bg-white/5 border-white/10 text-slate-500'}`}>
                                        {getActionIcon(trigger.action_key)}
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <button 
                                            onClick={() => handleToggle(trigger)}
                                            className={`p-3 rounded-xl transition-all ${trigger.is_active ? 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20' : 'bg-white/5 text-slate-500 hover:text-white hover:bg-white/10'}`}
                                        >
                                            {trigger.is_active ? <Pause size={18} /> : <Play size={18} />}
                                        </button>
                                        <button 
                                            onClick={() => {
                                                setEditingTrigger(trigger)
                                                setFormData({
                                                    name: trigger.name,
                                                    action_key: trigger.action_key,
                                                    schedule_type: (trigger as any).schedule_type || 'daily',
                                                    schedule_value: (trigger as any).schedule_value || '',
                                                    config: JSON.stringify(trigger.config, null, 2)
                                                })
                                                setIsModalOpen(true)
                                            }}
                                            className="p-3 bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 rounded-xl transition-all"
                                        >
                                            <Settings size={18} />
                                        </button>
                                        <button 
                                            onClick={() => handleDelete(trigger.trigger_id)}
                                            className="p-3 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 rounded-xl transition-all"
                                        >
                                            <Trash2 size={18} />
                                        </button>
                                    </div>
                                </div>

                                <div className="space-y-6">
                                    <div>
                                        <h3 className="text-xl font-bold text-white mb-2">{trigger.name}</h3>
                                        <div className="flex items-center gap-3">
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest ${trigger.is_active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-500/20 text-slate-500'}`}>
                                                {trigger.is_active ? 'Active' : 'Paused'}
                                            </span>
                                            <div className="flex items-center gap-2 text-slate-500 text-xs font-bold">
                                                <Clock size={12} />
                                                {(trigger as any).schedule_type === 'daily' ? `Hàng ngày lúc ${(trigger as any).schedule_value}` : `Mỗi ${(trigger as any).schedule_value} phút`}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="bg-black/20 rounded-2xl p-4 border border-white/5">
                                            <p className="text-[10px] text-slate-500 uppercase font-black tracking-widest mb-1">Loại Action</p>
                                            <p className="text-xs text-slate-300 font-bold capitalize">{trigger.action_key.replace('_', ' ')}</p>
                                        </div>
                                        <div className="bg-black/20 rounded-2xl p-4 border border-white/5">
                                            <p className="text-[10px] text-slate-500 uppercase font-black tracking-widest mb-1">Lần chạy cuối</p>
                                            <p className="text-xs text-slate-300 font-bold">{trigger.last_run_at ? new Date(trigger.last_run_at).toLocaleTimeString() : '---'}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                        
                        <button 
                            onClick={() => {
                                setEditingTrigger(null)
                                setFormData({ name: '', action_key: 'batch_notification', schedule_type: 'daily', schedule_value: '09:00', config: '{}' })
                                setIsModalOpen(true)
                            }}
                            className="group border-2 border-dashed border-white/5 rounded-[2.5rem] p-8 flex flex-col items-center justify-center gap-4 hover:border-indigo-500/30 hover:bg-indigo-500/5 transition-all duration-500"
                        >
                            <div className="p-4 bg-white/5 rounded-2xl text-slate-500 group-hover:text-indigo-400 group-hover:bg-indigo-500/10 transition-all">
                                <Plus size={32} />
                            </div>
                            <span className="text-slate-500 font-bold group-hover:text-slate-300">Thêm Trigger Tùy chỉnh</span>
                        </button>
                    </div>
                )}
            </section>

            {/* Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setIsModalOpen(false)} />
                    <div className="relative bg-slate-900 border border-white/10 rounded-3xl w-full max-w-lg overflow-hidden shadow-2xl animate-in zoom-in-95 duration-300">
                        <header className="p-6 border-b border-white/5 bg-white/5">
                            <h2 className="text-xl font-bold text-white">{editingTrigger ? 'Chỉnh sửa Trigger' : 'Tạo Trigger mới'}</h2>
                        </header>
                        
                        <form onSubmit={handleSubmit} className="p-8 space-y-6">
                            <div className="space-y-2">
                                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest">Tên Trigger</label>
                                <input 
                                    type="text" 
                                    value={formData.name}
                                    onChange={e => setFormData({...formData, name: e.target.value})}
                                    className="w-full bg-black/40 border border-white/10 rounded-2xl px-5 py-4 text-white focus:border-indigo-500 outline-none transition-all placeholder:text-slate-700"
                                    placeholder="Ví dụ: Daily Morning Alert"
                                    required
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest">Loại Action</label>
                                    <select 
                                        value={formData.action_key}
                                        onChange={e => setFormData({...formData, action_key: e.target.value as any})}
                                        disabled={!!editingTrigger}
                                        className="w-full bg-black/40 border border-white/10 rounded-2xl px-5 py-4 text-white focus:border-indigo-500 outline-none transition-all disabled:opacity-50 appearance-none"
                                    >
                                        <option value="batch_notification">Notification</option>
                                        <option value="daily_reminder">Daily Reminder</option>
                                        <option value="ai_moderation">AI Moderation</option>
                                        <option value="resource_crawler">Crawler</option>
                                        <option value="custom_webhook">Webhook</option>
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest">Loại lịch trình</label>
                                    <select 
                                        value={(formData as any).schedule_type}
                                        onChange={e => setFormData({...formData, schedule_type: e.target.value} as any)}
                                        className="w-full bg-black/40 border border-white/10 rounded-2xl px-5 py-4 text-white focus:border-indigo-500 outline-none transition-all appearance-none"
                                    >
                                        <option value="daily">Hàng ngày (Daily)</option>
                                        <option value="interval">Định kỳ (Interval)</option>
                                    </select>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest">
                                    {(formData as any).schedule_type === 'daily' ? 'Giờ gửi (HH:mm)' : 'Khoảng cách (Phút)'}
                                </label>
                                <input 
                                    type={(formData as any).schedule_type === 'daily' ? 'time' : 'number'} 
                                    value={(formData as any).schedule_value}
                                    onChange={e => setFormData({...formData, schedule_value: e.target.value} as any)}
                                    className="w-full bg-black/40 border border-white/10 rounded-2xl px-5 py-4 text-white focus:border-indigo-500 outline-none transition-all"
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest">Cấu hình JSON (Tùy chọn)</label>
                                <textarea 
                                    value={formData.config}
                                    onChange={e => setFormData({...formData, config: e.target.value})}
                                    rows={4}
                                    className="w-full bg-black/40 border border-white/10 rounded-2xl px-5 py-4 text-white font-mono text-xs focus:border-indigo-500 outline-none transition-all resize-none"
                                    placeholder="{}"
                                />
                            </div>

                            <div className="flex gap-4 pt-6">
                                <button 
                                    type="button"
                                    onClick={() => setIsModalOpen(false)}
                                    className="flex-1 bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white font-bold py-4 rounded-2xl transition-all border border-white/5"
                                >
                                    Hủy
                                </button>
                                <button 
                                    type="submit"
                                    className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-4 rounded-2xl transition-all shadow-xl shadow-indigo-600/20 active:scale-95"
                                >
                                    {editingTrigger ? 'Lưu thay đổi' : 'Kích hoạt ngay'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
