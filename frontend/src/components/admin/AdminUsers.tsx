import { useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import { ApiRequestError } from '../../api/types'
import { toast } from 'react-toastify'
import { Search, UserCheck, UserX, Info, Users, Loader2, Mail, Calendar, ShieldCheck } from 'lucide-react'

import { adminCache } from '../../hooks/useAdminStore'

export default function AdminUsers() {
    const cached = adminCache.getUsers()
    const [users, setUsers] = useState<any[]>(cached.users)
    const [loading, setLoading] = useState(cached.users.length === 0)
    const [query, setQuery] = useState(cached.query)
    const [total, setTotal] = useState(cached.total)

    const load = async () => {
        setLoading(true)
        try {
            const data = await adminService.listUsers({ query })
            setUsers(data.users)
            setTotal(data.total)
            adminCache.setUsers({ users: data.users, total: data.total, query })
        } catch (err) {
            if (err instanceof ApiRequestError && err.handledByModal) return
            toast.error('Không thể tải danh sách người dùng')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        load()
    }, [])

    const toggleStatus = async (userId: string, current: boolean) => {
        try {
            await adminService.updateUser(userId, { is_active: !current })
            setUsers(users.map(u => u.user_id === userId ? { ...u, is_active: !current } : u))
            toast.success(`Đã ${!current ? 'mở khóa' : 'khóa'} tài khoản`)
        } catch (err) {
            toast.error('Cập nhật thất bại')
        }
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Users className="text-emerald-400" />
                        Quản lý người dùng
                    </h1>
                    <p className="text-slate-400">Hệ thống hiện có <span className="text-emerald-400 font-bold">{total}</span> thành viên.</p>
                </div>
                
                <div className="flex gap-2 w-full md:w-auto">
                    <div className="relative flex-1 md:w-64">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                        <input
                            type="text"
                            placeholder="Tên, email, id..."
                            className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-white outline-none focus:border-emerald-500/50 transition-all"
                            value={query}
                            onChange={e => setQuery(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && load()}
                        />
                    </div>
                    <button 
                        onClick={load}
                        className="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 transition-all shadow-lg shadow-emerald-600/20 font-medium"
                    >
                        Tìm
                    </button>
                </div>
            </header>

            <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden backdrop-blur-sm shadow-2xl">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="bg-white/5 text-slate-400 text-[11px] uppercase tracking-widest font-bold">
                                <th className="px-6 py-4">Thông tin cơ bản</th>
                                <th className="px-6 py-4">Liên lạc</th>
                                <th className="px-6 py-4">Ngày tham gia</th>
                                <th className="px-6 py-4">Trạng thái</th>
                                <th className="px-6 py-4 text-right">Hành động</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5 text-slate-300">
                            {users.map((u) => (
                                <tr key={u.user_id} className="hover:bg-white/5 transition-all group">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold">
                                                {u.display_name?.charAt(0).toUpperCase() || 'U'}
                                            </div>
                                            <div>
                                                <p className="font-bold text-white group-hover:text-emerald-400 transition-colors">{u.display_name}</p>
                                                <p className="text-[10px] text-slate-500 font-mono">{u.user_id}</p>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2 text-sm text-slate-400">
                                            <Mail size={14} className="text-slate-600" />
                                            {u.email}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2 text-sm text-slate-400">
                                            <Calendar size={14} className="text-slate-600" />
                                            {new Date(u.created_at).toLocaleDateString('vi-VN')}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-tighter ${u.is_active ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-500 border border-rose-400/20'}`}>
                                            <div className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
                                            {u.is_active ? 'Đang hoạt động' : 'Đã bị khóa'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex justify-end gap-2">
                                            <button 
                                                onClick={() => toggleStatus(u.user_id, u.is_active)}
                                                className={`p-2.5 rounded-xl transition-all shadow-sm ${u.is_active ? 'bg-rose-500/10 text-rose-500 hover:bg-rose-500 hover:text-white' : 'bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500 hover:text-white'}`}
                                                title={u.is_active ? 'Khóa tài khoản' : 'Mở khóa'}
                                            >
                                                {u.is_active ? <UserX size={18} /> : <UserCheck size={18} />}
                                            </button>
                                            <button className="p-2.5 bg-blue-500/10 text-blue-400 rounded-xl hover:bg-blue-500 hover:text-white transition-all shadow-sm">
                                                <Info size={18} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {loading && (
                    <div className="py-20 flex flex-col items-center justify-center text-slate-500 gap-4">
                        <Loader2 className="animate-spin text-emerald-500" size={32} />
                        <p className="text-sm font-medium animate-pulse">Đang tải danh sách người dùng...</p>
                    </div>
                )}
                
                {!loading && users.length === 0 && (
                    <div className="py-20 flex flex-col items-center justify-center text-slate-500 gap-2">
                        <ShieldCheck size={48} className="text-slate-800" />
                        <p className="text-sm font-medium">Không tìm thấy kết quả nào khớp với tìm kiếm.</p>
                    </div>
                )}
            </div>
        </div>
    )
}
