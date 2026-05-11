/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import { motion } from 'framer-motion'
import { 
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, AreaChart, Area
} from 'recharts'
import { 
    Activity,
    TrendingUp, 
    MessageCircle, 
    Zap, 
    BrainCircuit,
    ChevronRight,
    Users,
    ShieldAlert,
    Info,
    Download,
    X
} from 'lucide-react'

import './AdminAnalytics.css'
import './AdminCommon.css'

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']

// allow flexible payload shape for charts tooltip
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="chart-tooltip">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">{label}</p>
                {payload.map((entry: any, index: number) => (
                    <div key={index} className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color || entry.fill }} />
                        <span className="text-xs font-bold text-white">
                            {entry.name}: {entry.value.toLocaleString()}
                        </span>
                    </div>
                ))}
            </div>
        )
    }
    return null
}

const TypewriterContent = ({ text }: { text: string }) => {
    const [displayedText, setDisplayedText] = useState('')
    const [index, setIndex] = useState(0)

    // avoid cascading renders warning: resetting when `text` changes is intentional
    useEffect(() => {
        const id = setTimeout(() => {
            setDisplayedText('')
            setIndex(0)
        }, 0)
        return () => clearTimeout(id)
    }, [text])

    useEffect(() => {
        if (index < text.length) {
            const timeout = setTimeout(() => {
                setDisplayedText(prev => prev + text[index])
                setIndex(prev => prev + 1)
            }, 30)
            return () => clearTimeout(timeout)
        }
    }, [index, text])

    return <p className="text-slate-300 leading-relaxed font-medium">{displayedText}</p>
}

const MetricInfo = ({ text }: { text: string }) => (
    <div className="group relative inline-block ml-1 align-middle">
        <Info size={12} className="text-slate-600 cursor-help hover:text-indigo-400 transition-colors" />
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-[10px] text-slate-300 w-48 opacity-0 group-hover:opacity-100 pointer-events-none transition-all z-50 shadow-2xl">
            {text}
        </div>
    </div>
)

const AIInsightCard = ({ insight, onAction, refreshing }: { insight: any, onAction: (type: string) => void, refreshing?: boolean }) => {
    if (!insight && !refreshing) return null
    return (
        <motion.div 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`ana-card !p-0 overflow-hidden border-indigo-500/20 bg-indigo-500/[0.02] ${refreshing ? 'opacity-60 pointer-events-none' : ''}`}
        >
            <div className="flex flex-col lg:flex-row">
                <div className="p-6 lg:w-2/3 border-b lg:border-b-0 lg:border-r border-white/5">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <div className="p-1.5 bg-indigo-500/20 text-indigo-400 rounded-lg">
                                <BrainCircuit size={16} className={refreshing ? 'animate-spin' : ''} />
                            </div>
                            <h3 className="text-sm font-black text-white tracking-widest uppercase">{insight?.title || 'Đang phân tích dữ liệu...'}</h3>
                        </div>
                        <button 
                            onClick={() => onAction('refresh')}
                            className="text-[9px] font-black text-indigo-400 uppercase tracking-widest hover:text-indigo-300 transition-colors flex items-center gap-1.5"
                        >
                            <Activity size={10} className={refreshing ? 'animate-spin' : ''} /> Phân tích lại
                        </button>
                    </div>
                    <div className="text-sm text-slate-300 leading-relaxed font-medium mb-6 min-h-[60px]">
                        {refreshing ? (
                            <div className="space-y-2">
                                <div className="admin-skeleton h-3 w-full" />
                                <div className="admin-skeleton h-3 w-4/5" />
                                <div className="admin-skeleton h-3 w-2/3" />
                            </div>
                        ) : (
                            <TypewriterContent text={insight?.content || ''} />
                        )}
                    </div>
                    <div className="flex gap-3">
                        <button 
                            onClick={() => onAction('pdf')}
                            className="px-5 py-2 bg-indigo-500 rounded-xl text-[10px] font-black text-white uppercase hover:bg-indigo-600 transition-all flex items-center gap-2"
                        >
                            <Download size={12} /> Xuất báo cáo PDF
                        </button>
                    </div>
                </div>
                <div className="p-6 lg:w-1/3 bg-white/[0.01]">
                    <h4 className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-4">Đề xuất tối ưu</h4>
                    <div className="grid grid-cols-1 gap-2">
                        {[
                            { icon: Users, label: 'Phân khúc', desc: 'Nhóm thiền buổi tối', color: 'emerald' },
                            { icon: ShieldAlert, label: 'Cảnh báo', desc: 'Hỗ trợ rủi ro cao', color: 'rose' }
                        ].map((act, i) => (
                            <div key={i} className="flex items-center gap-3 p-3 bg-white/5 rounded-xl border border-white/5 hover:border-indigo-500/20 transition-all cursor-pointer">
                                <div className={`p-2 bg-${act.color}-500/10 text-${act.color}-500 rounded-lg`}>
                                    <act.icon size={12} />
                                </div>
                                <div className="min-w-0">
                                    <p className="text-[10px] font-black text-white uppercase truncate">{act.label}</p>
                                    <p className="text-[9px] text-slate-500 font-bold truncate">{act.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </motion.div>
    )
}

export default function AdminAnalytics() {
    const [moodDist, setMoodDist] = useState<any[]>([])
    const [, setMoodTrend] = useState<any[]>([])
    const [clinical, setClinical] = useState<any>(null)
    const [resourceData, setResourceData] = useState<any>(null)
    const [chatMetrics, setChatMetrics] = useState<any>(null)
    const [aiInsight, setAiInsight] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [refreshingAI, setRefreshingAI] = useState(false)
    const [toast, setToast] = useState<{ message: string, type: 'success' | 'info' } | null>(null)

    const handleAction = async (type: string) => {
        if (type === 'pdf') {
            setToast({ message: "Đang chuẩn bị bản in PDF...", type: 'info' })
            setTimeout(() => {
                window.print()
                setToast(null)
            }, 1000)
        } else if (type === 'refresh') {
            setRefreshingAI(true)
            try {
                const res = await adminService.getAIInsights(true)
                if (res?.insight) setAiInsight(res.insight)
                setToast({ message: "Đã cập nhật phân tích chiến lược mới!", type: 'success' })
                setTimeout(() => setToast(null), 3000)
            } finally {
                setRefreshingAI(false)
            }
        }
    }

    const loadData = async () => {
        setLoading(true)
        try {
            const [mood, trend, clin, res, chat, ai] = await Promise.all([
                adminService.getMoodAnalytics(),
                adminService.getMoodTrend(),
                adminService.getClinicalAnalytics(),
                adminService.getResourceAnalytics(),
                adminService.getChatMetrics(),
                adminService.getAIInsights()
            ])

            if (mood?.distribution) setMoodDist(Object.entries(mood.distribution).map(([name, value]) => ({ name, value })))
            if (trend?.trend) setMoodTrend(trend.trend)
            if (clin) setClinical(clin)
            if (res) setResourceData(res)
            if (chat) setChatMetrics(chat)
            if (ai?.insight) setAiInsight(ai.insight)
        } catch (err) {
            console.error("Analytics Load Error:", err)
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
        visible: { opacity: 1, y: 0 }
    }

    if (loading) return (
        <div className="analytics-root p-10 space-y-12">
            <div className="flex justify-between items-end">
                <div className="space-y-4">
                    <div className="admin-skeleton h-10 w-80" />
                    <div className="admin-skeleton h-4 w-64" />
                </div>
                <div className="admin-skeleton h-10 w-32" />
            </div>

            <div className="admin-skeleton h-48 w-full rounded-[3rem]" />

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
                {[1, 2, 3, 4].map(i => (
                    <div key={i} className="ana-card !p-6 flex items-center gap-5">
                        <div className="admin-skeleton admin-skeleton-circle !w-14 !h-14" />
                        <div className="space-y-2 flex-1">
                            <div className="admin-skeleton h-3 w-1/2" />
                            <div className="admin-skeleton h-6 w-3/4" />
                        </div>
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                <div className="admin-skeleton h-[400px] w-full rounded-[3rem]" />
                <div className="admin-skeleton h-[400px] w-full rounded-[3rem]" />
            </div>
        </div>
    )
    return (
        <motion.div variants={containerVariants} initial="hidden" animate="visible" className="analytics-root">
            {toast && (
                <motion.div 
                    initial={{ opacity: 0, y: 50 }} 
                    animate={{ opacity: 1, y: 0 }} 
                    className={`fixed bottom-8 right-8 z-[100] px-6 py-4 rounded-2xl border shadow-2xl flex items-center gap-3 ${
                        toast.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400'
                    }`}
                >
                    <div className={`p-1.5 rounded-lg ${toast.type === 'success' ? 'bg-emerald-500/20' : 'bg-indigo-500/20'}`}>
                        {toast.type === 'success' ? <Zap size={16} /> : <Activity size={16} />}
                    </div>
                    <span className="text-sm font-black uppercase tracking-tight">{toast.message}</span>
                    <button onClick={() => setToast(null)} className="ml-4 opacity-50 hover:opacity-100"><X size={14} /></button>
                </motion.div>
            )}

            <header className="analytics-header">
                <div>
                    <h1 className="text-5xl font-black text-white tracking-tighter uppercase mb-2">Intelligence Center</h1>
                    <p className="text-[10px] text-slate-500 font-black uppercase tracking-[0.4em] flex items-center gap-2">
                        Control Panel <MetricInfo text="Trung tâm điều khiển và phân tích dữ liệu AI thời gian thực." />
                    </p>
                </div>
                <div className="flex gap-4">
                    <button onClick={loadData} className="px-8 py-3 bg-white/5 border border-white/10 rounded-2xl text-[10px] font-black text-white uppercase hover:bg-white/10 transition-all tracking-widest flex items-center gap-2">
                        <Activity size={14} className={loading ? 'animate-spin' : ''} />
                        Làm mới dữ liệu
                    </button>
                </div>
            </header>

            <div className="mb-4">
                <AIInsightCard insight={aiInsight} onAction={handleAction} refreshing={refreshingAI} />
            </div>

            {/* Top KPI row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-4">
                {[
                    { label: 'Tin nhắn AI', value: chatMetrics?.total_messages, icon: MessageCircle, color: 'indigo', info: 'Tổng số tin nhắn hệ thống AI đã phản hồi trong 30 ngày.' },
                    { label: 'Độ sâu TB', value: chatMetrics?.avg_depth, icon: BrainCircuit, color: 'emerald', info: 'Số lượng tin nhắn trung bình trong một cuộc hội thoại.' },
                    { label: 'Chi phí thực', value: `$${chatMetrics?.real_metrics?.actual_cost_usd?.toFixed(4) || '0.0000'}`, icon: Zap, color: 'amber', info: 'Tổng chi phí API Token dựa trên giá GPT-4o thực tế.' },
                    { label: 'Crisis Risk', value: (clinical?.crisis_distribution?.['high'] || 0), icon: ShieldAlert, color: 'rose', info: 'Số lượng người dùng có biểu hiện rủi ro tâm lý cao cần can thiệp.' }
                ].map((kpi, i) => (
                    <motion.div key={i} variants={itemVariants} className="ana-card !p-5 flex items-center gap-4">
                        <div className={`p-3 bg-${kpi.color}-500/10 text-${kpi.color}-400 rounded-xl border border-${kpi.color}-500/10 flex-shrink-0`}>
                            <kpi.icon size={20} />
                        </div>
                        <div className="min-w-0 overflow-hidden">
                            <p className="text-[9px] text-slate-500 font-black uppercase tracking-widest mb-1 flex items-center gap-1">
                                {kpi.label} <MetricInfo text={kpi.info} />
                            </p>
                            <p className="text-xl xl:text-2xl font-black text-white tracking-tighter truncate" title={kpi.value?.toString()}>
                                {kpi.value}
                            </p>
                        </div>
                    </motion.div>
                ))}
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-4">
                {/* Chat Volume Area Chart */}
                <motion.div variants={itemVariants} className="xl:col-span-2 ana-card">
                    <div className="section-header">
                        <div>
                            <h2 className="section-title">Lưu lượng hội thoại</h2>
                            <p className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mt-1">30 Ngày gần nhất</p>
                        </div>
                        <div className="flex gap-4">
                            <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-indigo-500" />
                                <span className="text-[10px] text-slate-500 font-black uppercase">Tin nhắn</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-emerald-500" />
                                <span className="text-[10px] text-slate-500 font-black uppercase">Hội thoại</span>
                            </div>
                        </div>
                    </div>
                    <div className="h-[350px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chatMetrics?.daily_stats || []}>
                                <defs>
                                    <linearGradient id="colorMsg" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                                <XAxis dataKey="date" tickFormatter={(v) => v.split('-').slice(1).join('/')} stroke="rgba(255,255,255,0.2)" fontSize={10} />
                                <YAxis stroke="rgba(255,255,255,0.2)" fontSize={10} />
                                <Tooltip content={<CustomTooltip />} />
                                <Area type="monotone" dataKey="messages" name="Tin nhắn" stroke="#6366f1" strokeWidth={3} fillOpacity={1} fill="url(#colorMsg)" animationDuration={2000} />
                                <Area type="monotone" dataKey="conversations" name="Cuộc trò chuyện" stroke="#10b981" strokeWidth={3} fill="transparent" animationDuration={2000} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>

                {/* Growth Forecast Card */}
                <motion.div variants={itemVariants} className="ana-card bg-indigo-500/[0.05] border-indigo-500/20">
                    <div className="flex items-center justify-between mb-8">
                        <h2 className="text-xl font-black text-white uppercase tracking-tight">Dự báo 30d</h2>
                        <div className="p-2 bg-indigo-500/20 rounded-xl text-indigo-400">
                            <TrendingUp size={20} />
                        </div>
                    </div>
                    
                    <div className="space-y-8">
                        <div>
                            <p className="text-[10px] text-slate-500 font-black uppercase tracking-[0.2em] mb-2">Tin nhắn dự kiến</p>
                            <p className="text-4xl font-black text-white tracking-tighter">
                                +{chatMetrics?.forecast?.projected_messages_30d?.toLocaleString()}
                            </p>
                            <div className="flex items-center gap-2 mt-2">
                                <span className="text-emerald-500 text-[10px] font-black">↑ {chatMetrics?.forecast?.growth_rate}%</span>
                                <span className="text-[10px] text-slate-600 font-bold uppercase">vs Tháng trước</span>
                            </div>
                        </div>

                        <div className="p-6 bg-white/[0.03] rounded-3xl border border-white/5">
                            <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mb-4">Chi phí LLM ước tính</p>
                            <div className="flex items-end justify-between">
                                <span className="text-2xl font-black text-white">${chatMetrics?.forecast?.projected_cost_30d?.toFixed(2)}</span>
                                <span className="text-[10px] text-indigo-400 font-black uppercase tracking-widest bg-indigo-500/10 px-2 py-1 rounded-md">Budget Safe</span>
                            </div>
                            <div className="w-full h-1.5 bg-white/5 rounded-full mt-4 overflow-hidden">
                                <div className="h-full bg-indigo-500 w-[65%]" />
                            </div>
                        </div>

                        <div className="pt-4">
                            <p className="text-xs text-slate-400 font-medium leading-relaxed italic">
                                "Dựa trên tốc độ hiện tại, hệ thống sẽ cần nâng cấp hạn mức API vào tuần thứ 3 của tháng tới."
                            </p>
                        </div>
                    </div>
                </motion.div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-10">
                {/* Mood Distribution */}
                <motion.div variants={itemVariants} className="ana-card !p-6">
                    <div className="section-header !mb-6">
                        <h2 className="section-title">Phân bổ tâm trạng</h2>
                        <Users size={18} className="text-slate-600" />
                    </div>
                    <div className="flex flex-col lg:flex-row items-center gap-6">
                        <div className="w-full lg:w-1/2 h-40">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={moodDist}
                                        innerRadius={45}
                                        outerRadius={65}
                                        paddingAngle={5}
                                        dataKey="value"
                                    >
                                        {moodDist.map((_, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Pie>
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="w-full lg:w-1/2 space-y-2">
                            {moodDist.slice(0, 5).map((m, i) => {
                                const total = moodDist.reduce((acc, curr) => acc + curr.value, 0)
                                const percent = ((m.value / total) * 100).toFixed(1)
                                return (
                                    <div key={i} className="flex items-center justify-between">
                                        <div className="flex items-center gap-2 min-w-0">
                                            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                                            <span className="text-[10px] font-black text-slate-400 uppercase truncate">{m.name}</span>
                                        </div>
                                        <span className="text-[10px] font-black text-white ml-2">{percent}%</span>
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                </motion.div>

                {/* PHQ-9 Severity Bar Chart */}
                <motion.div variants={itemVariants} className="ana-card !p-6">
                    <div className="section-header !mb-6">
                        <h2 className="section-title">Sức khỏe tâm thần</h2>
                        <ShieldAlert size={18} className="text-rose-500" />
                    </div>
                    <div className="h-40 w-full mb-4">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={Object.entries(clinical?.phq9_distribution || {}).map(([name, value]) => ({ name, value }))}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                                <XAxis dataKey="name" stroke="rgba(255,255,255,0.2)" fontSize={9} />
                                <YAxis stroke="rgba(255,255,255,0.2)" fontSize={9} />
                                <Bar dataKey="value" fill="#f59e0b" radius={[4, 4, 0, 0]} barSize={24} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                    <p className="text-[9px] text-slate-500 font-bold uppercase tracking-[0.2em] text-center">Chỉ số PHQ-9 (30 Ngày)</p>
                </motion.div>

                {/* Top Resources Ranking */}
                <motion.div variants={itemVariants} className="ana-card !p-6">
                    <div className="section-header !mb-6">
                        <h2 className="section-title">Nội dung phổ biến</h2>
                        <ChevronRight size={18} className="text-slate-600" />
                    </div>
                    <div className="space-y-2">
                        {(resourceData?.top_played || []).length > 0 ? resourceData.top_played.slice(0, 4).map((res: any, i: number) => (
                            <div key={i} className="flex items-center justify-between p-3 bg-white/5 rounded-xl border border-white/5">
                                <div className="flex items-center gap-3 min-w-0">
                                    <span className="text-[10px] font-black text-slate-500 w-4">#{i+1}</span>
                                    <p className="text-[10px] font-black text-white uppercase truncate">{res.title}</p>
                                </div>
                                <span className="text-[9px] text-indigo-400 font-black">{res.count}</span>
                            </div>
                        )) : (
                            <div className="h-32 flex flex-col items-center justify-center text-slate-600">
                                <Activity size={24} className="mb-2 opacity-20" />
                                <span className="text-[10px] font-black uppercase tracking-widest">Chưa có dữ liệu</span>
                            </div>
                        )}
                    </div>
                </motion.div>
            </div>
        </motion.div>
    )
}
