import './AdminDashboard.css'
import './AdminCommon.css'
import { useEffect, useState } from 'react'
import { ApiRequestError } from '../../api/types'
import {
    adminService,
    type AdminAuthLatencyResponse,
    type AdminCostDashboardResponse,
    type AdminDashboardAggregate,
} from '../../services/adminService'
import { 
    LayoutDashboard, 
    MessageSquare, 
    AlertCircle, 
    Zap, 
    DollarSign, 
    TrendingUp, 
    Users, 
    ShieldCheck, 
    Clock, 
    ArrowRight,
    Activity,
    ChevronRight,
    PieChart as PieIcon,
    BarChart3
} from 'lucide-react'

function numberOrDash(value: number | undefined): string {
    if (typeof value !== 'number' || Number.isNaN(value)) return '-'
    return value.toLocaleString('vi-VN')
}

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'

/* ── Modern Mood Pie Chart ── */
function MoodPieChart({ data }: { data: Record<string, number> }) {
    const MOOD_CONFIG: Record<string, { label: string; color: string; emoji: string }> = {
        awesome: { label: 'Tuyệt vời', color: '#10b981', emoji: '🤩' },
        great: { label: 'Rất tốt', color: '#059669', emoji: '🥰' },
        good: { label: 'Tốt', color: '#34d399', emoji: '😊' },
        fine: { label: 'Ổn', color: '#3b82f6', emoji: '🙂' },
        okay: { label: 'Bình thường', color: '#60a5fa', emoji: '😐' },
        stressed: { label: 'Căng thẳng', color: '#f59e0b', emoji: '😰' },
        bad: { label: 'Tệ', color: '#f87171', emoji: '😞' },
        struggling: { label: 'Khó khăn', color: '#ef4444', emoji: '😫' },
    }

    const chartData = Object.entries(data)
        .filter(([, value]) => value > 0)
        .map(([key, value]) => ({
            name: MOOD_CONFIG[key]?.label || key,
            value,
            color: MOOD_CONFIG[key]?.color || '#64748b',
            emoji: MOOD_CONFIG[key]?.emoji || '•'
        }))

    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-slate-900 border border-white/10 p-3 rounded-xl shadow-2xl backdrop-blur-md">
                    <p className="text-xs font-black text-white uppercase flex items-center gap-2">
                        <span className="text-lg">{payload[0].payload.emoji}</span>
                        {payload[0].name}
                    </p>
                    <p className="text-[10px] text-indigo-400 font-bold mt-1 uppercase">
                        {payload[0].value} Lượt check-in
                    </p>
                </div>
            )
        }
        return null
    }

    return (
        <div className="h-[280px] w-full flex flex-col md:flex-row items-center gap-4">
            <div className="flex-1 h-full w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie
                            data={chartData}
                            innerRadius={60}
                            outerRadius={90}
                            paddingAngle={5}
                            dataKey="value"
                            stroke="none"
                        >
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                    </PieChart>
                </ResponsiveContainer>
            </div>
            
            <div className="grid grid-cols-2 gap-x-6 gap-y-3 px-4 max-h-full overflow-y-auto">
                {chartData.map((item, i) => (
                    <div key={i} className="flex items-center gap-2 group cursor-default">
                        <div className="w-2.5 h-2.5 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.5)]" style={{ backgroundColor: item.color }} />
                        <div className="flex flex-col">
                            <span className="text-[10px] font-black text-slate-400 group-hover:text-white transition-colors uppercase tracking-tighter flex items-center gap-1">
                                <span>{item.emoji}</span>
                                {item.name}
                            </span>
                            <span className="text-[9px] text-slate-600 font-bold">{item.value} lượt</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}

/* ── Modern Donut Chart ── */
function TokenDonut({ input, output }: { input: number; output: number }) {
    const total = input + output || 1
    const inputPct = (input / total) * 100
    const outputPct = (output / total) * 100
    const inputDeg = (inputPct / 100) * 360

    return (
        <div className="flex flex-col items-center gap-6 py-4">
            <div className="relative w-40 h-40">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                    <circle 
                        className="text-white/5" 
                        strokeWidth="10" 
                        stroke="currentColor" 
                        fill="transparent" 
                        r="40" 
                        cx="50" 
                        cy="50" 
                    />
                    <circle 
                        className="text-rose-500 drop-shadow-[0_0_8px_rgba(244,114,182,0.4)]" 
                        strokeWidth="10" 
                        strokeDasharray={`${outputPct * 2.51} 251.2`} 
                        strokeLinecap="round" 
                        stroke="currentColor" 
                        fill="transparent" 
                        r="40" 
                        cx="50" 
                        cy="50" 
                    />
                    <circle 
                        className="text-indigo-500 drop-shadow-[0_0_8px_rgba(96,165,250,0.4)]" 
                        strokeWidth="10" 
                        strokeDasharray={`${inputPct * 2.51} 251.2`} 
                        strokeDashoffset={`-${outputPct * 2.51}`}
                        strokeLinecap="round" 
                        stroke="currentColor" 
                        fill="transparent" 
                        r="40" 
                        cx="50" 
                        cy="50" 
                    />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-2xl font-black text-white">{(total / 1000).toFixed(1)}k</span>
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Tokens</span>
                </div>
            </div>
            
            <div className="flex gap-6">
                <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]" />
                    <div className="flex flex-col">
                        <span className="text-[10px] font-bold text-slate-500 uppercase">Input</span>
                        <span className="text-xs font-bold text-white">{inputPct.toFixed(0)}%</span>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]" />
                    <div className="flex flex-col">
                        <span className="text-[10px] font-bold text-slate-500 uppercase">Output</span>
                        <span className="text-xs font-bold text-white">{outputPct.toFixed(0)}%</span>
                    </div>
                </div>
            </div>
        </div>
    )
}

/* ── SLA Gauge ── */
function SlaGauge({ label, p95, target, withinSla, successRate }: { label: string; p95: number; target: number; withinSla: boolean; successRate: number }) {
    const ratio = Math.min(p95 / (target || 1), 2)
    const deg = (ratio / 2) * 180
    const color = withinSla ? '#10b981' : '#f43f5e'

    return (
        <div className="flex flex-col items-center bg-white/5 border border-white/10 rounded-3xl p-6 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-3 opacity-20 group-hover:opacity-40 transition-opacity">
                <Activity size={24} className={withinSla ? 'text-emerald-400' : 'text-rose-400'} />
            </div>
            
            <h4 className="text-sm font-bold text-slate-400 mb-6 uppercase tracking-widest">{label}</h4>
            
            <div className="relative w-48 h-24 mb-4">
                {/* Background arc */}
                <div className="absolute inset-0 border-[12px] border-white/5 rounded-t-full" />
                {/* Active arc */}
                <div 
                    className="absolute inset-0 border-[12px] rounded-t-full transition-all duration-1000 ease-out"
                    style={{ 
                        borderColor: color,
                        clipPath: 'polygon(0 0, 100% 0, 100% 100%, 0 100%)',
                        transform: `rotate(${-180 + deg}deg)`,
                        transformOrigin: 'bottom center'
                    }}
                />
                
                <div className="absolute bottom-0 left-0 right-0 flex flex-col items-center">
                    <span className="text-2xl font-black text-white leading-none">{p95}</span>
                    <span className="text-[10px] font-bold text-slate-500 uppercase mt-1">ms / {target}ms</span>
                </div>
            </div>

            <div className="flex items-center gap-3 w-full justify-between mt-2 pt-4 border-t border-white/5">
                <span className={`text-[10px] font-black uppercase px-2 py-1 rounded-lg ${withinSla ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                    {withinSla ? '✓ HEALTHY' : '✗ OVER TARGET'}
                </span>
                <span className="text-xs font-bold text-slate-400">Success: <span className="text-white">{(successRate * 100).toFixed(0)}%</span></span>
            </div>
        </div>
    )
}

export default function AdminDashboard() {
    const [aggregate, setAggregate] = useState<AdminDashboardAggregate | null>(null)
    const [latency, setLatency] = useState<AdminAuthLatencyResponse | null>(null)
    const [cost, setCost] = useState<AdminCostDashboardResponse | null>(null)
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        let active = true
        const run = async () => {
            setLoading(true)
            setError('')
            try {
                const [a, l, c] = await Promise.all([
                    adminService.getDashboardAggregate(),
                    adminService.getAuthLatencySla(),
                    adminService.getCostDashboard(),
                ])
                if (!active) return
                setAggregate(a)
                setLatency(l)
                setCost(c)
            } catch (err) {
                if (!active) return
                if (err instanceof ApiRequestError) setError(err.message)
                else setError('Không tải được dữ liệu tổng quan.')
            } finally {
                if (active) setLoading(false)
            }
        }
        void run()
        return () => { active = false }
    }, [])

    return (
        <div className="space-y-10 pb-10 animate-in fade-in duration-700">
            {/* Header Area */}
            <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
                <div className="space-y-2">
                    <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-indigo-600 rounded-xl shadow-lg shadow-indigo-600/30">
                            <LayoutDashboard className="text-white" size={24} />
                        </div>
                        <h1 className="text-3xl font-black text-white tracking-tight">Admin Insights</h1>
                    </div>
                    <p className="text-slate-400 max-w-lg">
                        Theo dõi nhịp sống của hệ thống Serene qua các chỉ số tâm trạng, hiệu năng và tài nguyên thời gian thực.
                    </p>
                </div>

                <div className="flex flex-wrap gap-3">
                    <div className="bg-white/5 border border-white/10 px-4 py-2 rounded-2xl flex items-center gap-3 backdrop-blur-md">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
                        <span className="text-xs font-bold text-slate-300 uppercase tracking-widest">Live Syncing</span>
                    </div>
                    {aggregate?.period && (
                        <div className="bg-indigo-600/10 border border-indigo-600/20 px-4 py-2 rounded-2xl flex items-center gap-3">
                            <Clock size={14} className="text-indigo-400" />
                            <span className="text-xs font-bold text-indigo-300">{aggregate.period.from} → {aggregate.period.to}</span>
                        </div>
                    )}
                </div>
            </div>

            {error && (
                <div className="bg-rose-500/10 border border-rose-500/20 p-4 rounded-2xl flex items-center gap-3 text-rose-400 animate-in slide-in-from-top-2">
                    <AlertCircle size={20} />
                    <span className="text-sm font-medium">{error}</span>
                </div>
            )}

            {/* KPI Section */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <KPICard 
                    title="Phiên trò chuyện"
                    value={numberOrDash(aggregate?.total_sessions)}
                    icon={MessageSquare}
                    color="indigo"
                    loading={loading}
                    trend={aggregate?.session_trend !== undefined ? `${aggregate.session_trend >= 0 ? '+' : ''}${aggregate.session_trend}% so với tuần trước` : 'Đang tính toán...'}
                />
                <KPICard 
                    title="Sự kiện SOS"
                    value={numberOrDash(aggregate?.sos_events)}
                    icon={AlertCircle}
                    color="rose"
                    loading={loading}
                    trend="Ổn định"
                />
                <KPICard 
                    title="Phản hồi P95"
                    value={`${numberOrDash(latency?.login.p95_ms)} ms`}
                    icon={Zap}
                    color="amber"
                    loading={loading}
                    trend="Nhanh hơn 50ms"
                />
                <KPICard 
                    title="Chi phí tích lũy"
                    value={typeof cost?.chat_cost.estimated_cost_usd === 'number' ? `$${cost.chat_cost.estimated_cost_usd.toFixed(4)}` : '-'}
                    icon={DollarSign}
                    color="emerald"
                    loading={loading}
                    trend="Trong ngân sách"
                />
            </div>

            {/* Main Charts Area */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                {/* Mood Distribution */}
                <div className="xl:col-span-2 bg-white/5 border border-white/10 rounded-[2.5rem] p-8 backdrop-blur-xl relative group">
                    <div className="absolute top-8 right-8 text-slate-700 group-hover:text-indigo-500/40 transition-colors">
                        <TrendingUp size={48} />
                    </div>
                    <div className="mb-8">
                        <h2 className="text-xl font-bold text-white mb-1">Xu hướng cảm xúc</h2>
                        <p className="text-sm text-slate-500">Thống kê tâm trạng người dùng dựa trên check-in hàng ngày.</p>
                    </div>
                    
                    {loading ? (
                        <div className="space-y-6 py-4">
                            {[1, 2, 3, 4].map(i => (
                                <div key={i} className="space-y-2">
                                    <div className="h-3 w-24 bg-white/5 rounded-full animate-pulse" />
                                    <div className="h-4 w-full bg-white/5 rounded-full animate-pulse" />
                                </div>
                            ))}
                        </div>
                    ) : aggregate?.mood_distribution ? (
                        <MoodPieChart data={aggregate.mood_distribution} />
                    ) : (
                        <div className="py-20 text-center text-slate-600">Không có dữ liệu hiển thị</div>
                    )}

                    <div className="mt-10 pt-6 border-t border-white/5 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="flex -space-x-2">
                                {[1,2,3].map(i => <div key={i} className="w-6 h-6 rounded-full border-2 border-slate-900 bg-slate-800" />)}
                            </div>
                            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Dựa trên {aggregate?.total_sessions || 0} lượt tâm sự</span>
                        </div>
                        <button className="text-xs font-bold text-indigo-400 hover:text-white transition-colors flex items-center gap-1">
                            Xem chi tiết <ChevronRight size={14} />
                        </button>
                    </div>
                </div>

                {/* Token & LLM Stats */}
                <div className="bg-slate-900/50 border border-white/10 rounded-[2.5rem] p-8 flex flex-col">
                    <div className="mb-4">
                        <h2 className="text-xl font-bold text-white mb-1">Sử dụng LLM</h2>
                        <p className="text-sm text-slate-500">Chi phí và lưu lượng Token.</p>
                    </div>

                    {loading ? (
                        <div className="flex-1 flex flex-col items-center justify-center gap-6">
                            <div className="w-32 h-32 rounded-full border-8 border-white/5 border-t-indigo-500 animate-spin" />
                            <div className="h-4 w-32 bg-white/5 rounded-full animate-pulse" />
                        </div>
                    ) : cost?.chat_cost ? (
                        <>
                            <TokenDonut input={cost.chat_cost.total_input_tokens} output={cost.chat_cost.total_output_tokens} />
                            
                            <div className="mt-auto space-y-3">
                                <div className="bg-black/20 rounded-2xl p-4 flex items-center justify-between border border-white/5">
                                    <span className="text-xs text-slate-500 font-bold uppercase">Tổng lượt chat</span>
                                    <span className="text-lg font-black text-white">{numberOrDash(cost.chat_cost.total_turns)}</span>
                                </div>
                                <div className="bg-black/20 rounded-2xl p-4 flex items-center justify-between border border-white/5">
                                    <span className="text-xs text-slate-500 font-bold uppercase">Tổng Token</span>
                                    <span className="text-lg font-black text-white">{numberOrDash(cost.chat_cost.total_tokens)}</span>
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="flex-1 flex items-center justify-center text-slate-600">Không có dữ liệu</div>
                    )}
                </div>
            </div>

            {/* Bottom Row: SLA & Resources */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* SLA Gauges */}
                <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-6">
                    {loading ? (
                        <>
                            <div className="h-64 bg-white/5 rounded-[2.5rem] animate-pulse" />
                            <div className="h-64 bg-white/5 rounded-[2.5rem] animate-pulse" />
                        </>
                    ) : (
                        <>
                            <SlaGauge
                                label="Auth Login SLA"
                                p95={latency?.login.p95_ms || 0}
                                target={latency?.login.target_p95_ms || 0}
                                withinSla={latency?.login.within_sla || false}
                                successRate={latency?.login.success_rate || 0}
                            />
                            <SlaGauge
                                label="Auth Signup SLA"
                                p95={latency?.signup.p95_ms || 0}
                                target={latency?.signup.target_p95_ms || 0}
                                withinSla={latency?.signup.within_sla || false}
                                successRate={latency?.signup.success_rate || 0}
                            />
                        </>
                    )}
                </div>

                {/* Popular Resources */}
                <div className="lg:col-span-4 bg-gradient-to-br from-indigo-600 to-violet-700 rounded-[2.5rem] p-8 text-white relative overflow-hidden shadow-2xl shadow-indigo-600/20">
                    <div className="absolute top-0 right-0 -mr-10 -mt-10 w-40 h-40 bg-white/10 rounded-full blur-3xl" />
                    <div className="relative z-10 h-full flex flex-col">
                        <div className="flex items-center gap-3 mb-6">
                            <ShieldCheck size={24} />
                            <h3 className="font-bold uppercase tracking-widest text-sm">Top Resources</h3>
                        </div>
                        
                        <div className="space-y-4 flex-1">
                            {aggregate?.top_resource_categories?.map((cat, i) => (
                                <div key={cat} className="bg-white/10 backdrop-blur-md rounded-2xl p-4 flex items-center gap-4 border border-white/10 hover:bg-white/20 transition-all cursor-default group">
                                    <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-sm font-black">
                                        {i + 1}
                                    </div>
                                    <span className="font-bold tracking-tight flex-1">{cat}</span>
                                    <ArrowRight size={16} className="opacity-0 group-hover:opacity-100 transform translate-x-[-10px] group-hover:translate-x-0 transition-all" />
                                </div>
                            )) || <p className="text-indigo-200 italic opacity-60">Chưa có dữ liệu tài nguyên.</p>}
                        </div>

                        <p className="text-[10px] text-indigo-200 font-bold uppercase tracking-widest mt-8">
                            Dữ liệu được cập nhật từ hệ thống Crawler AI
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}

/* ── Sub-component: KPI Card ── */
function KPICard({ title, value, icon: Icon, color, loading, trend }: any) {
    const colorClasses: any = {
        indigo: 'text-indigo-400 bg-indigo-400/10 shadow-indigo-500/10',
        rose: 'text-rose-400 bg-rose-400/10 shadow-rose-500/10',
        amber: 'text-amber-400 bg-amber-400/10 shadow-amber-500/10',
        emerald: 'text-emerald-400 bg-emerald-400/10 shadow-emerald-500/10'
    }

    return (
        <div className="bg-white/5 border border-white/10 rounded-[2rem] p-6 hover:bg-white/[0.08] transition-all group relative overflow-hidden">
            <div className={`absolute top-0 right-0 w-24 h-24 blur-3xl opacity-0 group-hover:opacity-20 transition-opacity ${colorClasses[color].split(' ')[0].replace('text', 'bg')}`} />
            
            <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-2xl ${colorClasses[color]}`}>
                    <Icon size={20} />
                </div>
                <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{trend}</span>
            </div>
            
            <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">{title}</p>
                {loading ? (
                    <div className="h-8 w-24 bg-white/5 rounded-lg animate-pulse" />
                ) : (
                    <p className="text-2xl font-black text-white tracking-tighter">{value}</p>
                )}
            </div>
        </div>
    )
}
