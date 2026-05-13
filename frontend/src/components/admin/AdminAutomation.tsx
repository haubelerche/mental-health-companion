/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import { toast } from 'react-toastify'
import { Zap, Plus, Activity, Bell, Brain, Database, Globe, Mail, Info } from 'lucide-react'
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
    const [activeTab, setActiveTab] = useState<'notifications' | 'letters' | 'resources'>('notifications')
    const [triggers, setTriggers] = useState<Trigger[]>([])
    const [loading, setLoading] = useState(true)
    const [isModalOpen, setIsModalOpen] = useState(false)
    const [editingTrigger, setEditingTrigger] = useState<Trigger | null>(null)
    const [formData, setFormData] = useState({
        name: '',
        action_key: 'batch_notification',
        schedule_type: 'daily',
        schedule_value: '09:00',
        config: '{}',
        notif_title: '',
        notif_body: ''
    })

    const fetchTriggers = async () => {
        setLoading(true)
        try {
            const res = await adminService.listAutomationTriggers()
            setTriggers(res.triggers)
        } catch {
            toast.error('Không thể tải danh sách triggers')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchTriggers()
    }, [])

    const handleDelete = async (triggerId: string) => {
        if (!confirm('Bạn có chắc chắn muốn xóa trigger này?')) return
        try {
            await adminService.deleteAutomationTrigger(triggerId)
            setTriggers(prev => prev.filter(t => t.trigger_id !== triggerId))
            toast.success('Đã xóa trigger')
        } catch {
            toast.error('Không thể xóa trigger')
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            const configObj = JSON.parse(formData.config)
            let val = formData.schedule_value
            
            // Convert to minutes for interval type if unit is hours/days
            if (formData.schedule_type === 'interval') {
                const unit = (formData as any).schedule_unit || 'minutes'
                const rawVal = parseInt(val)
                if (unit === 'hours') val = (rawVal * 60).toString()
                else if (unit === 'days') val = (rawVal * 1440).toString()
            }

            // Sync notification fields to config if applicable
            if (formData.action_key === 'batch_notification') {
                configObj.title = formData.notif_title
                configObj.body = formData.notif_body
            }

            const payload = {
                name: formData.name,
                action_key: formData.action_key,
                schedule_type: (formData as any).schedule_type,
                schedule_value: val,
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
        } catch {
            toast.error('Dữ liệu JSON không hợp lệ hoặc lỗi kết nối')
        }
    }

    const getActionIcon = (key: string) => {
        switch (key) {
            case 'batch_notification': return Bell
            case 'ai_moderation': return Brain
            case 'resource_crawler': return Database
            case 'daily_reminder': return Activity
            default: return Globe
        }
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <header className="flex flex-col gap-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div>
                        <div className="flex items-center gap-3 mb-1">
                            <div className="p-2 bg-indigo-500/20 rounded-lg">
                                <Zap className="text-indigo-400 w-5 h-5" />
                            </div>
                            <h1 className="text-2xl font-bold text-white">Quản trị Tự động hóa</h1>
                        </div>
                        <p className="text-slate-400 text-sm">Cấu hình các kịch bản AI và tác vụ hệ thống thông minh.</p>
                    </div>
                    
                <div className="flex items-center gap-3">
                    {activeTab === 'notifications' && (
                        <button 
                            onClick={() => toast.info('Tính năng thông báo khẩn cấp đang được triển khai')}
                            className="flex items-center justify-center gap-2 bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 px-5 py-2.5 rounded-xl font-bold transition-all border border-rose-500/20"
                        >
                            <Bell size={18} />
                            Thông báo khẩn cấp
                        </button>
                    )}
                </div>
                </div>

                <div className="flex items-center gap-2 bg-white/5 p-1.5 rounded-2xl border border-white/5 w-fit">
                    <button 
                        onClick={() => setActiveTab('notifications')}
                        className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm transition-all ${activeTab === 'notifications' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
                    >
                        <Bell size={16} /> Thông báo
                    </button>
                    <button 
                        onClick={() => setActiveTab('letters')}
                        className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm transition-all ${activeTab === 'letters' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
                    >
                        <Mail size={16} /> Gửi thư AI
                    </button>
                    <button 
                        onClick={() => setActiveTab('resources')}
                        className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm transition-all ${activeTab === 'resources' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
                    >
                        <Database size={16} /> Crawler Tài nguyên
                    </button>
                </div>
            </header>

            <div className="space-y-6">
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-64 bg-white/5 border border-white/10 rounded-[2.5rem] animate-pulse" />
                        ))}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8 animate-in slide-in-from-bottom-4 duration-500">
                        {/* HIỂN THỊ TẤT CẢ TÁC VỤ TỪ DATABASE */}
                                {triggers
                                    .filter(t => {
                                        if (activeTab === 'notifications') return t.action_key === 'batch_notification' || t.action_key === 'daily_reminder'
                                        if (activeTab === 'letters') return t.action_key === 'ai_moderation'
                                        if (activeTab === 'resources') return t.action_key === 'resource_crawler'
                                        return false
                                    })
                                    .map((trigger) => (
                                        <WorkerAutomationCard 
                                            key={trigger.trigger_id}
                                            trigger={trigger}
                                            icon={getActionIcon(trigger.action_key)}
                                            onEdit={() => {
                                                setEditingTrigger(trigger)
                                                setFormData({
                                                    name: trigger.name,
                                                    action_key: trigger.action_key,
                                                    schedule_type: trigger.schedule_type,
                                                    schedule_value: trigger.schedule_value,
                                                    config: JSON.stringify(trigger.config, null, 2),
                                                    notif_title: trigger.config?.title || '',
                                                    notif_body: trigger.config?.body || ''
                                                })
                                                setIsModalOpen(true)
                                            }}
                                            onDelete={() => handleDelete(trigger.trigger_id)}
                                            onRefresh={fetchTriggers}
                                        />
                                    ))}

                        {/* 3. NÚT THÊM TRIGGER TÙY CHỈNH */}
                        <button 
                            onClick={() => {
                                setEditingTrigger(null)
                                const defaultAction = activeTab === 'notifications' ? 'batch_notification' : 
                                                    activeTab === 'letters' ? 'ai_moderation' : 'resource_crawler'
                                setFormData({ 
                                    name: '', 
                                    action_key: defaultAction, 
                                    schedule_type: 'daily', 
                                    schedule_value: '09:00', 
                                    config: '{}',
                                    notif_title: '',
                                    notif_body: ''
                                })
                                setIsModalOpen(true)
                            }}
                            className="group border-2 border-dashed border-white/5 rounded-[2.5rem] p-8 flex flex-col items-center justify-center gap-4 hover:border-indigo-500/30 hover:bg-indigo-500/5 transition-all duration-500 min-h-[300px]"
                        >
                            <div className="p-4 bg-white/5 rounded-2xl text-slate-500 group-hover:text-indigo-400 group-hover:bg-indigo-500/10 transition-all">
                                <Plus size={32} />
                            </div>
                            <span className="text-slate-500 font-bold group-hover:text-slate-300">Thêm Tác vụ {activeTab === 'notifications' ? 'Thông báo' : activeTab === 'letters' ? 'Phản hồi' : 'Crawler'}</span>
                        </button>
                    </div>
                )}
            </div>

            {/* Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setIsModalOpen(false)} />
                    <div className="relative bg-slate-900 border border-white/10 rounded-3xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col shadow-2xl animate-in zoom-in-95 duration-300">
                        <header className="p-6 border-b border-white/5 bg-white/5 shrink-0">
                            <h2 className="text-xl font-bold text-white">{editingTrigger ? 'Chỉnh sửa Trigger' : 'Tạo Trigger mới'}</h2>
                        </header>
                        
                        <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
                            <form id="automation-form" onSubmit={handleSubmit} className="space-y-6">
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

                            <div className="space-y-4 bg-black/20 p-6 rounded-3xl border border-white/5">
                                <div className="flex items-center justify-between">
                                    <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest">
                                        {(formData as any).schedule_type === 'daily' ? 'Giờ thực thi (HH:mm)' : 'Tần suất lặp lại'}
                                    </label>
                                    {(formData as any).schedule_type === 'interval' && (
                                        <select 
                                            value={(formData as any).schedule_unit || 'minutes'}
                                            onChange={e => setFormData({...formData, schedule_unit: e.target.value} as any)}
                                            className="bg-indigo-500/10 border border-indigo-500/20 rounded-lg px-3 py-1 text-[10px] font-black text-indigo-400 uppercase tracking-widest outline-none"
                                        >
                                            <option value="minutes">Phút</option>
                                            <option value="hours">Giờ</option>
                                            <option value="days">Ngày</option>
                                        </select>
                                    )}
                                </div>
                                <input 
                                    type={(formData as any).schedule_type === 'daily' ? 'time' : 'number'} 
                                    value={(formData as any).schedule_value}
                                    onChange={e => setFormData({...formData, schedule_value: e.target.value} as any)}
                                    className="w-full bg-black/40 border border-white/10 rounded-2xl px-5 py-4 text-white focus:border-indigo-500 outline-none transition-all"
                                    required
                                />
                                {(formData as any).schedule_type === 'interval' && (
                                    <p className="text-[10px] text-slate-600 italic">
                                        Tác vụ sẽ tự động chạy lại sau mỗi {(formData as any).schedule_value} {(formData as any).schedule_unit === 'minutes' ? 'phút' : (formData as any).schedule_unit === 'hours' ? 'giờ' : 'ngày'}.
                                    </p>
                                )}
                            </div>

                            {(formData.action_key === 'batch_notification' || formData.action_key === 'daily_reminder') && (
                                <div className="space-y-4 bg-indigo-500/5 p-6 rounded-3xl border border-indigo-500/10">
                                    <div className="space-y-2">
                                        <label className="block text-[10px] font-black text-indigo-400 uppercase tracking-widest">Tiêu đề thông báo</label>
                                        <input 
                                            type="text" 
                                            value={formData.notif_title}
                                            onChange={e => setFormData({...formData, notif_title: e.target.value})}
                                            className="w-full bg-black/40 border border-white/10 rounded-2xl px-5 py-3 text-white focus:border-indigo-500 outline-none transition-all text-sm"
                                            placeholder="📢 Thông báo mới"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="block text-[10px] font-black text-indigo-400 uppercase tracking-widest">Nội dung tin nhắn</label>
                                        <textarea 
                                            value={formData.notif_body}
                                            onChange={e => setFormData({...formData, notif_body: e.target.value})}
                                            rows={3}
                                            className="w-full bg-black/40 border border-white/10 rounded-2xl px-5 py-3 text-white focus:border-indigo-500 outline-none transition-all text-sm resize-none"
                                            placeholder="Nhập nội dung bạn muốn gửi..."
                                            required
                                        />
                                    </div>
                                </div>
                            )}

                            <div className="space-y-4 bg-slate-800/50 p-6 rounded-3xl border border-white/5">
                                <h3 className="text-xs font-black text-indigo-400 uppercase tracking-widest flex items-center gap-2">
                                    <Info size={14} /> Hướng dẫn cấu hình JSON
                                </h3>
                                <div className="space-y-3 text-[11px] text-slate-400">
                                    <div className="p-3 bg-black/30 rounded-xl border border-white/5">
                                        <p className="font-bold text-slate-300 mb-1 flex items-center gap-2"><Bell size={12} /> Thông báo (batch_notification):</p>
                                        <code className="text-indigo-300 block bg-black/20 p-2 rounded mt-1">{"{ \"title\": \"Chào buổi sáng\", \"body\": \"Nội dung...\" }"}</code>
                                    </div>
                                    <div className="p-3 bg-black/30 rounded-xl border border-white/5">
                                        <p className="font-bold text-slate-300 mb-1 flex items-center gap-2"><Brain size={12} /> AI Phản hồi thư (ai_moderation):</p>
                                        <code className="text-indigo-300 block bg-black/20 p-2 rounded mt-1">{"{ \"hours_threshold\": 1 }"}</code>
                                        <p className="mt-1 text-[10px] italic opacity-70">(hours_threshold: Số giờ tối thiểu thư chờ trước khi AI rep)</p>
                                    </div>
                                    <div className="p-3 bg-black/30 rounded-xl border border-white/5">
                                        <p className="font-bold text-slate-300 mb-1 flex items-center gap-2"><Database size={12} /> Crawler (resource_crawler):</p>
                                        <code className="text-indigo-300 block bg-black/20 p-2 rounded mt-1">{"{ \"category\": \"meditation\", \"limit\": 3 }"}</code>
                                    </div>
                                </div>
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
                            </form>
                        </div>

                        <footer className="p-6 bg-white/5 border-t border-white/5 flex gap-4 shrink-0">
                            <button 
                                type="button"
                                onClick={() => setIsModalOpen(false)}
                                className="flex-1 bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white font-bold py-4 rounded-2xl transition-all border border-white/5"
                            >
                                Hủy
                            </button>
                            <button 
                                type="submit"
                                form="automation-form"
                                className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-4 rounded-2xl transition-all shadow-xl shadow-indigo-600/20 active:scale-95"
                            >
                                {editingTrigger ? 'Lưu thay đổi' : 'Kích hoạt ngay'}
                            </button>
                        </footer>
                    </div>
                </div>
            )}
        </div>
    )
}
