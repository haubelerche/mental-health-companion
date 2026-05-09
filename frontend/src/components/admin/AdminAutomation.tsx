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
    Loader2
} from 'lucide-react'

type Trigger = {
    trigger_id: string
    name: string
    trigger_type: 'fixed' | 'custom'
    action_key: 'batch_notification' | 'ai_moderation' | 'resource_crawler' | 'custom_webhook'
    config: any
    schedule_interval: string
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
        schedule_interval: '0 9 * * *',
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
            if (editingTrigger) {
                await adminService.updateAutomationTrigger(editingTrigger.trigger_id, {
                    name: formData.name,
                    schedule_interval: formData.schedule_interval,
                    config: configObj
                })
                toast.success('Đã cập nhật trigger')
            } else {
                await adminService.createAutomationTrigger({
                    ...formData,
                    config: configObj
                })
                toast.success('Đã tạo trigger mới')
            }
            setIsModalOpen(false)
            fetchTriggers()
        } catch (err) {
            toast.error('Dữ liệu không hợp lệ hoặc lỗi server')
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
                        setFormData({ name: '', action_key: 'batch_notification', schedule_interval: '0 9 * * *', config: '{}' })
                        setIsModalOpen(true)
                    }}
                    className="flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl font-bold transition-all shadow-lg shadow-indigo-600/20 active:scale-95"
                >
                    <Plus size={18} />
                    Thêm Trigger mới
                </button>
            </header>

            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-64 bg-white/5 border border-white/10 rounded-3xl animate-pulse" />
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {triggers.map((trigger) => (
                        <div 
                            key={trigger.trigger_id} 
                            className={`group relative bg-white/5 border border-white/10 rounded-3xl p-6 hover:bg-white/[0.08] transition-all duration-300 ${!trigger.is_active ? 'opacity-70' : ''}`}
                        >
                            <div className="flex items-start justify-between mb-6">
                                <div className={`p-3 rounded-2xl ${trigger.trigger_type === 'fixed' ? 'bg-indigo-500/10 border border-indigo-500/20' : 'bg-slate-500/10 border border-slate-500/20'}`}>
                                    {getActionIcon(trigger.action_key)}
                                </div>
                                <div className="flex items-center gap-2">
                                    <button 
                                        onClick={() => handleToggle(trigger)}
                                        className={`p-2 rounded-xl transition-all ${trigger.is_active ? 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20' : 'bg-slate-500/10 text-slate-400 hover:bg-slate-500/20'}`}
                                    >
                                        {trigger.is_active ? <Pause size={18} /> : <Play size={18} />}
                                    </button>
                                    <button 
                                        onClick={() => {
                                            setEditingTrigger(trigger)
                                            setFormData({
                                                name: trigger.name,
                                                action_key: trigger.action_key,
                                                schedule_interval: trigger.schedule_interval,
                                                config: JSON.stringify(trigger.config, null, 2)
                                            })
                                            setIsModalOpen(true)
                                        }}
                                        className="p-2 bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 rounded-xl transition-all"
                                    >
                                        <Settings size={18} />
                                    </button>
                                    {trigger.trigger_type !== 'fixed' && (
                                        <button 
                                            onClick={() => handleDelete(trigger.trigger_id)}
                                            className="p-2 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 rounded-xl transition-all"
                                        >
                                            <Trash2 size={18} />
                                        </button>
                                    )}
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <h3 className="text-lg font-bold text-white mb-1 flex items-center gap-2">
                                        {trigger.name}
                                        {trigger.trigger_type === 'fixed' && (
                                            <span className="text-[10px] bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded-full uppercase tracking-widest font-black">Hệ thống</span>
                                        )}
                                    </h3>
                                    <div className="flex items-center gap-2 text-slate-500 text-xs font-medium">
                                        <Clock size={12} />
                                        {trigger.schedule_interval}
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-3 pt-2">
                                    <div className="bg-black/20 rounded-2xl p-3 border border-white/5">
                                        <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider mb-1">Loại Action</p>
                                        <p className="text-xs text-slate-300 capitalize">{trigger.action_key.replace('_', ' ')}</p>
                                    </div>
                                    <div className="bg-black/20 rounded-2xl p-3 border border-white/5">
                                        <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider mb-1">Lần chạy cuối</p>
                                        <p className="text-xs text-slate-300">{trigger.last_run_at ? new Date(trigger.last_run_at).toLocaleTimeString() : 'Chưa chạy'}</p>
                                    </div>
                                </div>
                            </div>
                            
                            <div className="absolute bottom-0 left-6 right-6 h-[2px] bg-gradient-to-r from-transparent via-indigo-500/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                    ))}
                </div>
            )}

            {/* Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setIsModalOpen(false)} />
                    <div className="relative bg-slate-900 border border-white/10 rounded-3xl w-full max-w-lg overflow-hidden shadow-2xl animate-in zoom-in-95 duration-300">
                        <header className="p-6 border-b border-white/5 bg-white/5">
                            <h2 className="text-xl font-bold text-white">{editingTrigger ? 'Chỉnh sửa Trigger' : 'Tạo Trigger mới'}</h2>
                        </header>
                        
                        <form onSubmit={handleSubmit} className="p-6 space-y-5">
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Tên Trigger</label>
                                <input 
                                    type="text" 
                                    value={formData.name}
                                    onChange={e => setFormData({...formData, name: e.target.value})}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-indigo-500 outline-none transition-all"
                                    placeholder="Ví dụ: Daily Morning Alert"
                                    required
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Action</label>
                                    <select 
                                        value={formData.action_key}
                                        onChange={e => setFormData({...formData, action_key: e.target.value as any})}
                                        disabled={!!editingTrigger}
                                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-indigo-500 outline-none transition-all disabled:opacity-50"
                                    >
                                        <option value="batch_notification">Notification</option>
                                        <option value="ai_moderation">AI Moderation</option>
                                        <option value="resource_crawler">Crawler</option>
                                        <option value="custom_webhook">Webhook</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Lịch trình (Cron)</label>
                                    <input 
                                        type="text" 
                                        value={formData.schedule_interval}
                                        onChange={e => setFormData({...formData, schedule_interval: e.target.value})}
                                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-indigo-500 outline-none transition-all"
                                        placeholder="0 9 * * *"
                                        required
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Cấu hình (JSON)</label>
                                <textarea 
                                    value={formData.config}
                                    onChange={e => setFormData({...formData, config: e.target.value})}
                                    rows={5}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white font-mono text-sm focus:border-indigo-500 outline-none transition-all"
                                    placeholder="{}"
                                />
                            </div>

                            <div className="flex gap-3 pt-4">
                                <button 
                                    type="button"
                                    onClick={() => setIsModalOpen(false)}
                                    className="flex-1 bg-white/5 hover:bg-white/10 text-white font-bold py-3 rounded-xl transition-all"
                                >
                                    Hủy
                                </button>
                                <button 
                                    type="submit"
                                    className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 rounded-xl transition-all shadow-lg shadow-indigo-600/20"
                                >
                                    {editingTrigger ? 'Cập nhật' : 'Tạo ngay'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
