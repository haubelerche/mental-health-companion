import { useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import { toast } from 'react-toastify'
import { Search, UserCheck, UserX, Info } from 'lucide-react'

export default function AdminUsers() {
    const [users, setUsers] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [query, setQuery] = useState('')
    const [total, setTotal] = useState(0)

    const load = async () => {
        setLoading(true)
        try {
            const data = await adminService.listUsers({ query })
            setUsers(data.users)
            setTotal(data.total)
        } catch (err) {
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
            toast.success('Đã cập nhật trạng thái')
        } catch (err) {
            toast.error('Cập nhật thất bại')
        }
    }

    return (
        <div className="space-y-6">
            <header>
                <h1 className="text-2xl font-bold text-white">Quản lý người dùng</h1>
                <p className="text-slate-400">Xem và quản lý tài khoản người dùng hệ thống.</p>
            </header>

            <div className="flex gap-4">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Tìm kiếm theo tên hoặc email..."
                        className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-white outline-none focus:border-emerald-500/50"
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && load()}
                    />
                </div>
                <button 
                    onClick={load}
                    className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 transition-colors"
                >
                    Tìm kiếm
                </button>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-white/5 text-slate-400 text-sm">
                        <tr>
                            <th className="px-6 py-4 font-medium">Người dùng</th>
                            <th className="px-6 py-4 font-medium">Email</th>
                            <th className="px-6 py-4 font-medium">Ngày tạo</th>
                            <th className="px-6 py-4 font-medium">Trạng thái</th>
                            <th className="px-6 py-4 font-medium">Hành động</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-slate-300">
                        {users.map(u => (
                            <tr key={u.user_id} className="hover:bg-white/5 transition-colors">
                                <td className="px-6 py-4 font-medium text-white">{u.display_name}</td>
                                <td className="px-6 py-4 text-sm">{u.email}</td>
                                <td className="px-6 py-4 text-sm">{new Date(u.created_at).toLocaleDateString('vi-VN')}</td>
                                <td className="px-6 py-4">
                                    <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${u.is_active ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'}`}>
                                        {u.is_active ? 'Active' : 'Banned'}
                                    </span>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex gap-3">
                                        <button 
                                            onClick={() => toggleStatus(u.user_id, u.is_active)}
                                            className={`p-2 rounded-lg transition-colors ${u.is_active ? 'bg-rose-500/10 text-rose-500 hover:bg-rose-500/20' : 'bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20'}`}
                                            title={u.is_active ? 'Ban user' : 'Unban user'}
                                        >
                                            {u.is_active ? <UserX size={16} /> : <UserCheck size={16} />}
                                        </button>
                                        <button className="p-2 bg-blue-500/10 text-blue-500 rounded-lg hover:bg-blue-500/20 transition-colors">
                                            <Info size={16} />
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {loading && (
                    <div className="py-10 text-center text-slate-500">Đang tải...</div>
                )}
                {!loading && users.length === 0 && (
                    <div className="py-10 text-center text-slate-500">Không tìm thấy người dùng nào.</div>
                )}
            </div>
        </div>
    )
}
