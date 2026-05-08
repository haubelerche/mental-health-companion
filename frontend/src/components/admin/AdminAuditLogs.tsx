import { useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import { ApiRequestError } from '../../api/types'
import { toast } from 'react-toastify'
import { Shield, Clock, User } from 'lucide-react'

export default function AdminAuditLogs() {
    const [logs, setLogs] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    const load = async () => {
        setLoading(true)
        try {
            const data = await adminService.listAuditLogs()
            console.log("Audit Logs Data:", data)
            setLogs(data?.items || [])
        } catch (err) {
            if (err instanceof ApiRequestError && err.handledByModal) return
            toast.error('Không thể tải nhật ký hoạt động')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        load()
    }, [])

    return (
        <div className="space-y-6">
            <header className="flex justify-between items-end">
                <div>
                    <h1 className="text-2xl font-bold text-white">Nhật ký hoạt động (Audit Logs)</h1>
                    <p className="text-slate-400">Theo dõi mọi thao tác của quản trị viên trên hệ thống.</p>
                </div>
                <button onClick={load} className="text-sm text-indigo-400 hover:text-indigo-300 font-medium">Làm mới</button>
            </header>

            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                <table className="w-full text-left text-sm">
                    <thead>
                        <tr className="border-b border-white/10 bg-white/5 text-slate-400">
                            <th className="px-6 py-4 font-semibold uppercase tracking-wider text-[11px]">Thời gian</th>
                            <th className="px-6 py-4 font-semibold uppercase tracking-wider text-[11px]">Admin</th>
                            <th className="px-6 py-4 font-semibold uppercase tracking-wider text-[11px]">Hành động</th>
                            <th className="px-6 py-4 font-semibold uppercase tracking-wider text-[11px]">Resource</th>
                            <th className="px-6 py-4 font-semibold uppercase tracking-wider text-[11px]">IP Address</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {(logs || []).map((log) => (
                            <tr key={log.log_id} className="hover:bg-white/5 transition-colors">
                                <td className="px-6 py-4 text-slate-400 whitespace-nowrap">
                                    <div className="flex items-center gap-2">
                                        <Clock size={14} />
                                        {new Date(log.created_at).toLocaleString('vi-VN')}
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-2 text-indigo-400 font-medium">
                                        <User size={14} />
                                        {log.admin_id}
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <span className="bg-white/10 px-2 py-1 rounded text-slate-200 font-mono text-[12px]">
                                        {log.action}
                                    </span>
                                </td>
                                <td className="px-6 py-4 text-slate-400 max-w-xs truncate">
                                    {log.resource_accessed}
                                </td>
                                <td className="px-6 py-4 text-slate-500 font-mono">
                                    {log.ip_address}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {loading && <div className="text-center py-20 text-slate-500">Đang tải dữ liệu...</div>}
                {!loading && logs.length === 0 && (
                    <div className="text-center py-20">
                        <Shield size={40} className="mx-auto text-slate-700 mb-4" />
                        <p className="text-slate-500">Chưa có nhật ký hoạt động nào.</p>
                    </div>
                )}
            </div>
        </div>
    )
}
