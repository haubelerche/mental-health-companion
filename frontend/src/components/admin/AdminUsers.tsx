/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import { ApiRequestError } from '../../api/types'
import { toast } from 'react-toastify'
import { Search, Users, Info, ShieldCheck } from 'lucide-react'

import { adminCache } from '../../hooks/useAdminStore'

export default function AdminUsers() {
    const cached = adminCache.getUsers()
    const [users, setUsers] = useState<any[]>(cached.users)
    const [loading, setLoading] = useState(cached.users.length === 0)
    const [query, setQuery] = useState(cached.query)
    const [submittedQuery, setSubmittedQuery] = useState(cached.query)
    const [total, setTotal] = useState(cached.total)
    const [page, setPage] = useState(0)
    const limit = 20

    const load = useCallback(async (targetPage: number, targetQuery: string) => {
        setLoading(true)
        try {
            const data = await adminService.listUsers({ query: targetQuery, limit, offset: targetPage * limit })
            setUsers(data.users)
            setTotal(data.total)
            adminCache.setUsers({ users: data.users, total: data.total, query: targetQuery })
        } catch (err) {
            if (err instanceof ApiRequestError && err.handledByModal) return
            toast.error('Không thể tải danh sách người dùng')
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        void load(page, submittedQuery)
    }, [load, page, submittedQuery])

    const toggleStatus = async (userId: string, current: boolean) => {
        try {
            await adminService.updateUser(userId, { is_active: !current })
            setUsers(users.map(u => u.user_id === userId ? { ...u, is_active: !current } : u))
            toast.success(`Đã ${!current ? 'mở khóa' : 'khóa'} tài khoản`)
        } catch {
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
                            onKeyDown={e => {
                                if (e.key === 'Enter') {
                                    setSubmittedQuery(query)
                                    setPage(0)
                                }
                            }}
                        />
                    </div>
                    <button 
                        onClick={() => { setSubmittedQuery(query); setPage(0); }}
                        className="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 transition-all shadow-lg shadow-emerald-600/20 font-medium"
                    >
                        Tìm
                    </button>
                </div>
            </header>

            {/* Top Pagination Bar Removed */}

            <div className="admin-glass-container overflow-hidden backdrop-blur-sm shadow-2xl relative">
                <div className={`p-6 transition-all duration-500 ${loading ? 'opacity-50' : 'opacity-100'}`}>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                        {loading && users.length === 0 ? (
                            // Premium Skeletons
                            Array.from({ length: 8 }).map((_, i) => (
                                <div key={i} className="bg-white/5 border border-white/10 rounded-3xl p-6 space-y-6">
                                    <div className="flex items-center gap-4">
                                        <div className="admin-skeleton admin-skeleton-circle" />
                                        <div className="flex-1 space-y-2">
                                            <div className="admin-skeleton h-4 w-2/3" />
                                            <div className="admin-skeleton h-3 w-1/3" />
                                        </div>
                                    </div>
                                    <div className="space-y-3">
                                        <div className="admin-skeleton h-3 w-full" />
                                        <div className="admin-skeleton h-3 w-1/2" />
                                    </div>
                                    <div className="flex gap-2">
                                        <div className="admin-skeleton h-10 flex-1" />
                                        <div className="admin-skeleton h-10 w-12" />
                                    </div>
                                </div>
                            ))
                        ) : (
                            users.map((u) => (
                                <div key={u.user_id} className="group relative bg-white/5 border border-white/10 rounded-3xl p-6 hover:bg-white/[0.08] hover:border-white/20 transition-all hover:-translate-y-1 shadow-xl">
                                    <div className="flex items-center gap-4 mb-6">
                                        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 flex items-center justify-center border border-emerald-500/30 group-hover:scale-110 transition-transform">
                                            <span className="text-xl font-black text-emerald-400">{u.display_name?.charAt(0).toUpperCase() || 'U'}</span>
                                        </div>
                                        <div className="min-w-0 flex-1">
                                            <h3 className="text-white font-black truncate text-base leading-tight" title={u.display_name}>{u.display_name}</h3>
                                            <p className="text-slate-500 text-[11px] font-bold uppercase tracking-tighter truncate">{u.user_id.slice(-8)}</p>
                                        </div>
                                        <div className={`w-2.5 h-2.5 rounded-full ${u.is_active ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' : 'bg-slate-700'}`} />
                                    </div>

                                    <div className="space-y-4 mb-6">
                                        <div className="flex flex-col gap-1">
                                            <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Email</span>
                                            <span className="text-slate-300 text-xs font-medium truncate">{u.email}</span>
                                        </div>
                                        <div className="flex justify-between items-end">
                                            <div className="flex flex-col gap-1">
                                                <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Joined</span>
                                                <span className="text-slate-400 text-[11px]">{new Date(u.created_at).toLocaleDateString('vi-VN')}</span>
                                            </div>
                                            <span className="px-2.5 py-1 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-indigo-400 text-[10px] font-black uppercase tracking-widest">Member</span>
                                        </div>
                                    </div>

                                    <div className="flex gap-2">
                                        <button 
                                            onClick={() => toggleStatus(u.user_id, u.is_active)}
                                            className={`flex-1 py-2.5 rounded-xl text-xs font-black transition-all border ${
                                                u.is_active 
                                                ? 'bg-rose-500/10 border-rose-500/20 text-rose-500 hover:bg-rose-500 hover:text-white' 
                                                : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-500 hover:bg-emerald-500 hover:text-white'
                                            }`}
                                        >
                                            {u.is_active ? 'Khóa tài khoản' : 'Mở khóa'}
                                        </button>
                                        <button className="px-4 py-2.5 bg-blue-500/10 text-blue-400 rounded-xl hover:bg-blue-500 hover:text-white transition-all border border-blue-500/20">
                                            <Info size={16} />
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                    {users.length === 0 && !loading && (
                        <div className="py-20 flex flex-col items-center justify-center text-slate-500 gap-2">
                            <ShieldCheck size={48} className="text-slate-800" />
                            <p className="text-sm font-medium">Không tìm thấy kết quả nào khớp với tìm kiếm.</p>
                        </div>
                    )}
                </div>

                
                {!loading && users.length === 0 && (
                    <div className="py-20 flex flex-col items-center justify-center text-slate-500 gap-2">
                        <ShieldCheck size={48} className="text-slate-800" />
                        <p className="text-sm font-medium">Không tìm thấy kết quả nào khớp với tìm kiếm.</p>
                    </div>
                )}

                {/* Bottom Pagination */}
                {total > limit && (
                    <div className="px-6 py-4 border-t border-white/5 flex items-center justify-between bg-white/5">
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">
                            Trang {page + 1} / {Math.ceil(total / limit)} • {total} Thành viên
                        </p>
                        
                        <div className="flex items-center gap-1.5">
                            <button
                                onClick={() => setPage(p => Math.max(0, p - 1))}
                                disabled={page === 0 || loading}
                                className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 disabled:opacity-10 border border-white/5 rounded-md transition-all"
                            >
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" /></svg>
                            </button>

                            {(() => {
                                const totalPages = Math.ceil(total / limit);
                                const current = page + 1;
                                const range = [];
                                
                                if (totalPages <= 7) {
                                    for (let i = 1; i <= totalPages; i++) range.push(i);
                                } else {
                                    if (current <= 4) {
                                        range.push(1, 2, 3, 4, 5, '...', totalPages);
                                    } else if (current >= totalPages - 3) {
                                        range.push(1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
                                    } else {
                                        range.push(1, '...', current - 1, current, current + 1, '...', totalPages);
                                    }
                                }

                                return range.map((p, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => typeof p === 'number' && setPage(p - 1)}
                                        disabled={loading || p === '...'}
                                        className={`w-8 h-8 flex items-center justify-center rounded-md text-[11px] font-bold transition-all border ${
                                            p === current 
                                            ? 'bg-emerald-500 border-emerald-500 text-white' 
                                            : p === '...' 
                                                ? 'text-slate-700 border-transparent cursor-default' 
                                                : 'text-slate-500 border-white/5 hover:bg-white/5 hover:text-white'
                                        }`}
                                    >
                                        {p}
                                    </button>
                                ));
                            })()}

                            <button
                                onClick={() => setPage(p => p + 1)}
                                disabled={(page + 1) * limit >= total || loading}
                                className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 disabled:opacity-10 border border-white/5 rounded-md transition-all"
                            >
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" /></svg>
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
