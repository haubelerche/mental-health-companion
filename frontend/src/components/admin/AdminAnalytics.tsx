import { useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import { ApiRequestError } from '../../api/types'
import { 
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, LineChart, Line, Legend
} from 'recharts'
import { toast } from 'react-toastify'
import { Activity, Heart, Package, TrendingUp } from 'lucide-react'

import './AdminCommon.css'

const COLORS = ['#10b981', '#3b82f6', '#fbbf24', '#f87171', '#8b5cf6', '#ec4899', '#06b6d4']

export default function AdminAnalytics() {
    const [moodDist, setMoodDist] = useState<any[]>([])
    const [moodTrend, setMoodTrend] = useState<any[]>([])
    const [clinical, setClinical] = useState<any>(null)
    const [resourceData, setResourceData] = useState<any>(null)
    const [heartData, setHeartData] = useState<any>(null)
    const [loading, setLoading] = useState(true)

    const loadData = async () => {
        setLoading(true)
        try {
            // Fetch individually to be more resilient
            adminService.getMoodAnalytics().then(res => {
                if (res?.distribution) {
                    setMoodDist(Object.entries(res.distribution).map(([name, value]) => ({ name, value })))
                }
            }).catch(e => console.error("Mood Analytics Error:", e))

            adminService.getMoodTrend().then(res => {
                if (res?.trend) setMoodTrend(res.trend)
            }).catch(e => console.error("Mood Trend Error:", e))

            adminService.getClinicalAnalytics().then(res => {
                if (res) setClinical(res)
            }).catch(e => console.error("Clinical Analytics Error:", e))

            adminService.getResourceAnalytics().then(res => {
                if (res) setResourceData(res)
            }).catch(e => console.error("Resource Analytics Error:", e))

            adminService.getHeartAnalytics().then(res => {
                if (res) setHeartData(res)
            }).catch(e => console.error("Heart Analytics Error:", e))

            // We wait a bit or just assume they are loading in background
            // To keep the loading state simple, we can use a small delay or track all
            await new Promise(resolve => setTimeout(resolve, 1200))
        } catch (err) {
            if (err instanceof ApiRequestError && err.handledByModal) return
            toast.error('Không thể tải một số dữ liệu phân tích')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadData()
    }, [])

    const SkeletonCard = () => (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
            <div className="flex items-center gap-4">
                <div className="w-12 h-12 admin-skeleton !rounded-xl" />
                <div className="flex-1 space-y-2">
                    <div className="h-3 w-2/3 admin-skeleton" />
                    <div className="h-6 w-1/2 admin-skeleton" />
                </div>
            </div>
        </div>
    )

    const SkeletonChart = () => (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 h-[320px]">
            <div className="h-4 w-1/3 admin-skeleton mb-8" />
            <div className="space-y-4">
                {[1, 2, 3, 4].map(i => (
                    <div key={i} className="flex items-center gap-4">
                        <div className="w-12 h-3 admin-skeleton" />
                        <div className="flex-1 h-3 admin-skeleton !rounded-full" />
                    </div>
                ))}
            </div>
            <div className="mt-12 h-32 w-full admin-skeleton !rounded-xl opacity-20" />
        </div>
    )

    if (loading) return (
        <div className="space-y-10 animate-in fade-in duration-700">
            <header>
                <div className="h-9 w-64 admin-skeleton mb-2" />
                <div className="h-4 w-96 admin-skeleton" />
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <SkeletonChart />
                <SkeletonChart />
                <SkeletonChart />
                <SkeletonChart />
            </div>
        </div>
    )

    return (
        <div className="space-y-10 pb-20">
            <header>
                <h1 className="text-3xl font-bold text-white tracking-tight">Trung tâm phân tích toàn diện</h1>
                <p className="text-slate-400 mt-1">Dữ liệu thời thực về hành vi, cảm xúc và kinh tế hệ thống.</p>
            </header>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-emerald-500/10 text-emerald-500 rounded-xl">
                            <Heart size={24} />
                        </div>
                        <div>
                            <p className="text-sm text-slate-400 font-medium">Tổng Trái tim phát hành</p>
                            <p className="text-2xl font-bold text-white mt-1">{heartData?.total_issued?.toLocaleString() || 0}</p>
                        </div>
                    </div>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-500/10 text-blue-500 rounded-xl">
                            <Activity size={24} />
                        </div>
                        <div>
                            <p className="text-sm text-slate-400 font-medium">Lượt tương tác Resource</p>
                            <p className="text-2xl font-bold text-white mt-1">{resourceData?.top_played?.reduce((a: any, b: any) => a + b.count, 0) || 0}</p>
                        </div>
                    </div>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-amber-500/10 text-amber-500 rounded-xl">
                            <Package size={24} />
                        </div>
                        <div>
                            <p className="text-sm text-slate-400 font-medium">Top Spender (Hearts)</p>
                            <p className="text-2xl font-bold text-white mt-1">{heartData?.total_spent?.toLocaleString() || 0}</p>
                        </div>
                    </div>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-rose-500/10 text-rose-500 rounded-xl">
                            <TrendingUp size={24} />
                        </div>
                        <div>
                            <p className="text-sm text-slate-400 font-medium">User Crisis Rate</p>
                            <p className="text-2xl font-bold text-white mt-1">
                                {((clinical?.crisis_distribution?.['3'] || 0) + (clinical?.crisis_distribution?.['4'] || 0) + (clinical?.crisis_distribution?.['5'] || 0)) || 0}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Mood Distribution */}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                    <h2 className="text-lg font-semibold text-white mb-6">Phân bố cảm xúc (30 ngày)</h2>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={moodDist}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {moodDist.map((_, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: 'none', borderRadius: '8px' }} />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Mood Trend */}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                    <h2 className="text-lg font-semibold text-white mb-6">Xu hướng Check-in hàng ngày</h2>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={moodTrend}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                                <XAxis dataKey="date" stroke="#64748b" fontSize={10} tickFormatter={(val) => val?.split('-')?.slice(1)?.join('/') || val} />
                                <YAxis stroke="#64748b" fontSize={10} />
                                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: 'none', borderRadius: '8px' }} />
                                <Line type="monotone" dataKey="count" stroke="#10b981" strokeWidth={3} dot={{ r: 4, fill: '#10b981' }} activeDot={{ r: 6 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Clinical PHQ-9 */}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                    <h2 className="text-lg font-semibold text-white mb-6">Phân tích Trầm cảm (PHQ-9 Severity)</h2>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={Object.entries(clinical?.phq9_distribution || {}).map(([name, value]) => ({ name, value }))}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                                <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                                <YAxis stroke="#64748b" fontSize={10} />
                                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: 'none', borderRadius: '8px' }} />
                                <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Top Resources */}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                    <h2 className="text-lg font-semibold text-white mb-6">Tài nguyên được xem nhiều nhất</h2>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart layout="vertical" data={resourceData?.top_played || []}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                                <XAxis type="number" stroke="#64748b" fontSize={10} />
                                <YAxis type="category" dataKey="title" stroke="#64748b" fontSize={8} width={100} />
                                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: 'none', borderRadius: '8px' }} />
                                <Bar dataKey="count" fill="#fbbf24" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Heart Earners */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                <h2 className="text-lg font-semibold text-white mb-6">Bảng xếp hạng Trái tim (Top Earners)</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                    {heartData?.top_earners?.map((user: any, i: number) => (
                        <div key={i} className="bg-white/5 p-4 rounded-xl border border-white/5 text-center">
                            <p className="text-xs text-slate-500 font-bold uppercase mb-1">Hạng {i+1}</p>
                            <p className="text-white font-medium truncate">{user.name}</p>
                            <p className="text-emerald-500 font-bold mt-1">{user.amount.toLocaleString()} ❤️</p>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}
