/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState } from 'react'
import { adminService } from '../../../services/adminService'
import { toast } from 'react-toastify'
import { Shield, Lock, ArrowRight, Loader2 } from 'lucide-react'

interface Props {
    onSuccess: () => void
}
/* eslint-disable @typescript-eslint/no-explicit-any */

export default function AdminReAuthModal({ onSuccess }: Props) {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [totp, setTotp] = useState('')
    const [loading, setLoading] = useState(false)

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        try {
            await adminService.login({
                email,
                password,
                totp_code: totp
            })
            toast.success('Xác thực lại thành công!')
            onSuccess()
        } catch (err: any) {
            toast.error(err.message || 'Xác thực thất bại')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
            <div className="bg-[#1e293b] border border-indigo-500/30 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl shadow-indigo-500/10">
                <div className="bg-indigo-600/10 p-6 border-b border-white/5 flex items-center gap-4">
                    <div className="p-3 bg-indigo-500/20 rounded-xl text-indigo-400">
                        <Shield size={24} />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white">Phiên làm việc hết hạn</h2>
                        <p className="text-sm text-slate-400">Vui lòng nhập lại thông tin để tiếp tục.</p>
                    </div>
                </div>

                <form onSubmit={handleLogin} className="p-6 space-y-4">
                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Email</label>
                        <div className="relative">
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-indigo-500 outline-none transition-all"
                                placeholder="admin@serene.app"
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Mật khẩu</label>
                        <div className="relative">
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-indigo-500 outline-none transition-all"
                                placeholder="••••••••"
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Mã OTP (TOTP)</label>
                        <div className="relative">
                            <input
                                type="text"
                                value={totp}
                                onChange={(e) => setTotp(e.target.value)}
                                className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-indigo-500 outline-none transition-all font-mono tracking-[0.5em] text-center text-lg"
                                placeholder="000000"
                                maxLength={6}
                                required
                            />
                            <Lock className="absolute left-4 top-3.5 text-slate-500" size={18} />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full mt-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl py-3.5 font-bold flex items-center justify-center gap-2 transition-all group"
                    >
                        {loading ? (
                            <Loader2 className="animate-spin" size={20} />
                        ) : (
                            <>
                                Tiếp tục kiểm soát
                                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                            </>
                        )}
                    </button>
                </form>
            </div>
        </div>
    )
}
