import './AdminDashboard.css'
import './AdminCommon.css'
import { useEffect, useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
    adminService,
    type AdminDashboardAggregate,
} from '../../services/adminService'
import { 
    MessageSquare, 
    TrendingUp, 
    TrendingDown,
    ChevronRight,
    BrainCircuit,
    Coins,
    History,
    Zap,
    Activity,
    ShieldAlert
} from 'lucide-react'

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

function numberOrDash(value: number | undefined): string {
    if (typeof value !== 'number' || Number.isNaN(value)) return '-'
    return value.toLocaleString('vi-VN')
}

function TrendBadge({ value }: { value: number }) {
    const isUp = value >= 0
    return (
        <div className={`flex items-center gap-1 text-[10px] font-black uppercase tracking-tighter ${isUp ? 'text-emerald-500' : 'text-rose-500'}`}>
            {isUp ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {Math.abs(value)}%
        </div>
    )
}

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

function MoodTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload?: { emoji?: string; name?: string; value?: number } }> }) {
    if (active && payload && payload.length) {
        const p = payload[0].payload ?? {}
        return (
            <div className="bg-slate-900/90 border border-white/10 p-4 rounded-2xl shadow-2xl backdrop-blur-xl">
                <p className="text-xs font-black text-white uppercase flex items-center gap-2">
                    <span className="text-xl">{p.emoji}</span>
                    {p.name}
                </p>
                <p className="text-[10px] text-indigo-400 font-black mt-1 uppercase tracking-tighter">
                    {p.value} Lượt check-in
                </p>
            </div>
        )
    }
    return null
}

/* ── Modern Mood Pie Chart ── */
function MoodPieChart({ data, loading }: { data: Record<string, number>, loading?: boolean }) {
    const chartData = useMemo(() => {
        return Object.entries(data)
            .filter(([, value]) => value > 0)
            .map(([key, value]) => ({
                name: MOOD_CONFIG[key]?.label || key,
                value,
                color: MOOD_CONFIG[key]?.color || '#64748b',
                emoji: MOOD_CONFIG[key]?.emoji || '•'
            }))
    }, [data])

    if (loading) {
        return (
            <div className="h-[280px] w-full flex flex-col md:flex-row items-center gap-8">
                <div className="flex-1 h-full w-full flex items-center justify-center">
                    <div className="admin-skeleton w-48 h-48 rounded-full" />
                </div>
                <div className="grid grid-cols-2 gap-4 px-6">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <div key={i} className="flex items-center gap-3">
                            <div className="admin-skeleton w-3 h-3 rounded-full" />
                            <div className="space-y-1">
                                <div className="admin-skeleton h-3 w-16" />
                                <div className="admin-skeleton h-2 w-10" />
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        )
    }

    // tooltip uses module-scoped component `MoodTooltip`

    return (
        <div className="h-[280px] w-full flex flex-col md:flex-row items-center gap-8">
            <div className="flex-1 h-full w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie
                            data={chartData}
                            innerRadius={65}
                            outerRadius={95}
                            paddingAngle={8}
                            dataKey="value"
                            stroke="none"
                            animationBegin={0}
                            animationDuration={1500}
                        >
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} className="hover:opacity-80 transition-opacity cursor-pointer focus:outline-none" />
                            ))}
                        </Pie>
                        <Tooltip content={<MoodTooltip />} />
                    </PieChart>
                </ResponsiveContainer>
            </div>
            
            <div className="grid grid-cols-2 gap-x-8 gap-y-4 px-6 max-h-full overflow-y-auto custom-scrollbar">
                {chartData.map((item, i) => (
                    <motion.div 
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1 }}
                        key={i} 
                        className="flex items-center gap-3 group cursor-default"
                    >
                        <div className="w-3 h-3 rounded-full shadow-[0_0_12px_rgba(0,0,0,0.8)]" style={{ backgroundColor: item.color }} />
                        <div className="flex flex-col">
                            <span className="text-[11px] font-black text-slate-400 group-hover:text-white transition-colors uppercase tracking-tight flex items-center gap-1.5">
                                <span className="text-sm">{item.emoji}</span>
                                {item.name}
                            </span>
                            <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest">{item.value} lượt</span>
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    )
}

/* ── Modern Donut Chart ── */
function TokenDonut({ input, output }: { input: number; output: number }) {
    const total = input + output || 1
    const inputPct = (input / total) * 100

    return (
        <div className="flex flex-col items-center gap-8 py-6">
            <div className="relative w-44 h-44 group">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                    <circle className="text-white/5" strokeWidth="10" stroke="currentColor" fill="transparent" r="40" cx="50" cy="50" />
                    <motion.circle 
                        initial={{ strokeDasharray: "0 251.2" }}
                        animate={{ strokeDasharray: `${(input / total) * 251.2} 251.2` }}
                        transition={{ duration: 2, ease: "easeOut" }}
                        className="text-indigo-500 drop-shadow-[0_0_12px_rgba(99,102,241,0.5)]" 
                        strokeWidth="10" 
                        strokeLinecap="round" 
                        stroke="currentColor" 
                        fill="transparent" 
                        r="40" 
                        cx="50" 
                        cy="50" 
                    />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-3xl font-black text-white">{Math.round(inputPct)}%</span>
                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-[0.2em]">Input Share</span>
                </div>
            </div>
            
            <div className="flex gap-10">
                <div className="flex flex-col items-center">
                    <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.6)]" />
                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Input</span>
                    </div>
                    <span className="text-sm font-black text-white">{numberOrDash(input)}</span>
                </div>
                <div className="flex flex-col items-center">
                    <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 rounded-full bg-slate-700" />
                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Output</span>
                    </div>
                    <span className="text-sm font-black text-white">{numberOrDash(output)}</span>
                </div>
            </div>
        </div>
    )
}

export default function AdminDashboard() {
    const [loading, setLoading] = useState(true)
    const [aggregate, setAggregate] = useState<AdminDashboardAggregate | null>(null)
    const navigate = useNavigate()

    const loadData = async () => {
        setLoading(true)
        try {
            const agg = await adminService.getDashboardAggregate()
            setAggregate(agg)
        } catch (err) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadData()
    }, [])

    const containerVariants = {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
    }

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' as const } }
    }

    const kpis = [
        { 
            label: 'Lượt tâm sự', 
            value: aggregate?.total_sessions, 
            trend: aggregate?.session_trend || 0,
            icon: MessageSquare, 
            color: 'indigo', 
            sub: 'Tổng số cuộc hội thoại' 
        },
        { 
            label: 'Trạng thái SOS', 
            value: aggregate?.sos_events, 
            trend: aggregate?.sos_trend || 0,
            icon: ShieldAlert, 
            color: aggregate?.sos_events && aggregate.sos_events > 0 ? 'rose' : 'emerald', 
            sub: 'Yêu cầu hỗ trợ khẩn cấp',
            glow: aggregate?.sos_events && aggregate.sos_events > 0
        },
        { 
            label: 'Độ sâu hội thoại', 
            value: aggregate?.avg_session_depth, 
            trend: aggregate?.depth_trend || 0,
            icon: BrainCircuit, 
            color: 'amber', 
            sub: 'TB tin nhắn mỗi phiên' 
        },
        { 
            label: 'Chi phí LLM', 
            value: `$${aggregate?.estimated_cost_usd?.toFixed(4) || '0.0000'}`, 
            trend: aggregate?.cost_trend || 0,
            icon: Coins, 
            color: 'blue', 
            sub: 'Ước tính phí vận hành' 
        }
    ]

    return (
        <motion.div variants={containerVariants} initial="hidden" animate="visible" className="dash-root space-y-10">
            {/* KPI Section */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
                {kpis.map((kpi, i) => (
                    <motion.div 
                        variants={itemVariants}
                        key={i} 
                        className={`relative group bg-slate-900/40 border border-white/10 rounded-[2.5rem] p-8 hover:bg-white/[0.05] transition-all overflow-hidden ${kpi.glow ? 'ring-2 ring-rose-500/50 shadow-[0_0_30px_rgba(244,63,94,0.3)] animate-pulse' : ''}`}
                    >
                        <div className={`absolute -right-4 -top-4 w-24 h-24 bg-${kpi.color}-500/5 rounded-full blur-3xl group-hover:bg-${kpi.color}-500/10 transition-colors`} />
                        <div className="flex items-start justify-between mb-6">
                            <div className={`p-4 bg-${kpi.color}-500/10 rounded-2xl border border-${kpi.color}-500/20`}>
                                <kpi.icon className={`text-${kpi.color}-400`} size={24} />
                            </div>
                            <TrendBadge value={kpi.trend} />
                        </div>
                        <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] mb-1">{kpi.label}</h3>
                        <div className="text-3xl font-black text-white tracking-tighter">
                            {loading ? <div className="admin-skeleton h-9 w-24" /> : kpi.value}
                        </div>
                        <p className="text-[10px] text-slate-500 font-bold uppercase mt-4 tracking-tight">{kpi.sub}</p>
                    </motion.div>
                ))}
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                <motion.div variants={itemVariants} className="xl:col-span-2 bg-slate-900/40 border border-white/10 rounded-[3rem] p-10 relative group">
                    <div className="mb-10">
                        <h2 className="text-2xl font-black text-white mb-2 uppercase tracking-tight">Xu hướng cảm xúc</h2>
                        <p className="text-sm text-slate-500 font-medium uppercase tracking-widest">Phân tích trạng thái cộng đồng dựa trên Daily Check-in.</p>
                    </div>
                    <MoodPieChart data={aggregate?.mood_distribution || {}} loading={loading} />
                    <div className="mt-12 pt-8 border-t border-white/5 flex flex-col md:flex-row md:items-center justify-between gap-6">
                        <div className="flex items-center gap-8">
                            <div className="flex flex-col">
                                <span className="text-xl font-black text-white">{aggregate?.total_sessions || 0}</span>
                                <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Tổng lượt tương tác</span>
                            </div>
                        </div>
                        <button 
                            onClick={() => navigate('/admin/analytics')}
                            className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-3 rounded-2xl text-xs font-black uppercase tracking-widest transition-all shadow-xl shadow-indigo-600/20 flex items-center gap-2 group"
                        >
                            Xem chi tiết <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />
                        </button>
                    </div>
                </motion.div>

                <motion.div variants={itemVariants} className="bg-slate-900/40 border border-white/10 rounded-[3rem] p-10 flex flex-col relative group overflow-hidden">
                    <div className="mb-8">
                        <div className="flex items-center justify-between mb-2">
                            <h2 className="text-2xl font-black text-white uppercase tracking-tight">Sử dụng LLM</h2>
                            <div className="p-2 bg-white/5 rounded-xl border border-white/10">
                                <Zap className="text-amber-400" size={20} />
                            </div>
                        </div>
                        <p className="text-sm text-slate-500 font-medium uppercase tracking-widest">Hiệu suất và chi phí Token.</p>
                    </div>

                    {loading ? (
                        <div className="flex-1 flex flex-col items-center justify-center gap-8 py-6">
                            <div className="admin-skeleton w-40 h-40 rounded-full" />
                            <div className="w-full space-y-4 mt-auto">
                                <div className="admin-skeleton h-20 w-full rounded-[2rem]" />
                                <div className="admin-skeleton h-20 w-full rounded-[2rem]" />
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col">
                            <TokenDonut 
                                input={aggregate?.total_input_tokens || 0} 
                                output={aggregate?.total_output_tokens || 0} 
                            />
                            <div className="mt-auto space-y-4">
                                <div className="bg-white/5 backdrop-blur-md rounded-[2rem] p-6 flex items-center justify-between border border-white/5">
                                    <div className="flex items-center gap-4">
                                        <div className="p-3 bg-indigo-500/10 rounded-2xl text-indigo-400"><History size={20} /></div>
                                        <span className="text-xs text-slate-400 font-black uppercase tracking-widest">Tổng lượt Chat</span>
                                    </div>
                                    <span className="text-2xl font-black text-white">{numberOrDash(aggregate?.total_turns)}</span>
                                </div>
                                <div className="bg-white/5 backdrop-blur-md rounded-[2rem] p-6 flex items-center justify-between border border-white/5">
                                    <div className="flex items-center gap-4">
                                        <div className="p-3 bg-emerald-500/10 rounded-2xl text-emerald-400"><Activity size={20} /></div>
                                        <span className="text-xs text-slate-400 font-black uppercase tracking-widest">Tổng Token</span>
                                    </div>
                                    <span className="text-2xl font-black text-white">{numberOrDash(aggregate?.total_tokens)}</span>
                                </div>
                            </div>
                        </div>
                    )}
                </motion.div>
            </div>
        </motion.div>
    )
}
