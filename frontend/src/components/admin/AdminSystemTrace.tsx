import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, RefreshCw, ChevronDown, ChevronRight, Cpu } from 'lucide-react'
import { adminService, type AdminTraceRecord } from '../../services/adminService'
import './AdminSystemTrace.css'
import './AdminCommon.css'

const NODE_COLORS: Record<string, string> = {
    safety_gate: '#10b981',
    distress_router: '#f59e0b',
    analyst: '#8b5cf6',
    friend: '#6366f1',
    friend_stream: '#6366f1',
    run_non_sos_turn_total: '#64748b',
}

function distressBadge(score: number) {
    if (score >= 0.82) return { label: 'Cao', bg: '#ef4444' }
    if (score >= 0.55) return { label: 'Vừa', bg: '#f59e0b' }
    return { label: 'Thấp', bg: '#10b981' }
}

function formatTs(ts: number) {
    return new Date(ts * 1000).toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    })
}

function SpanRow({
    span,
    maxMs,
}: {
    span: { node: string; duration_ms: number; route_reason?: string }
    maxMs: number
}) {
    const color = NODE_COLORS[span.node] || '#64748b'
    const pct = Math.min(100, (span.duration_ms / (maxMs || 1)) * 100)
    return (
        <div className="flex items-center gap-4 py-2">
            <span
                className="text-[10px] font-black uppercase w-44 truncate"
                style={{ color }}
            >
                {span.node}
            </span>
            <div className="span-bar-track">
                <div
                    className="span-bar-fill"
                    style={{ width: `${pct}%`, backgroundColor: color }}
                />
            </div>
            <span className="text-[10px] font-black text-slate-300 w-16 text-right">
                {span.duration_ms.toFixed(0)} ms
            </span>
            {span.route_reason && (
                <span className="text-[9px] text-slate-500 font-medium italic">
                    {span.route_reason}
                </span>
            )}
        </div>
    )
}

function TraceRow({ trace }: { trace: AdminTraceRecord }) {
    const [open, setOpen] = useState(false)
    const badge = distressBadge(trace.distress_score)
    const spans = trace.routing_history || []
    const maxMs = Math.max(...spans.map((s) => s.duration_ms), 1)

    const routeColor =
        trace.route_decision === 'analyst'
            ? '#8b5cf6'
            : trace.route_decision === 'friend'
              ? '#6366f1'
              : '#64748b'

    return (
        <>
            <tr className="trace-row" onClick={() => setOpen((o) => !o)}>
                <td className="font-mono text-slate-500 text-[10px]">{formatTs(trace.ts)}</td>
                <td>
                    <span className="font-mono text-[10px] text-slate-400">
                        {trace.user_id_hash}
                    </span>
                </td>
                <td>
                    <span
                        className="distress-badge"
                        style={{
                            backgroundColor: `${badge.bg}20`,
                            color: badge.bg,
                            border: `1px solid ${badge.bg}40`,
                        }}
                    >
                        {trace.distress_score.toFixed(2)} · {badge.label}
                    </span>
                </td>
                <td>
                    <span
                        className="text-[10px] font-black uppercase"
                        style={{ color: routeColor }}
                    >
                        {trace.route_decision}
                    </span>
                </td>
                <td>
                    <span
                        className={`text-[11px] font-black ${
                            trace.total_ms > 3000
                                ? 'text-rose-400'
                                : trace.total_ms > 1500
                                  ? 'text-amber-400'
                                  : 'text-emerald-400'
                        }`}
                    >
                        {trace.total_ms.toFixed(0)} ms
                    </span>
                </td>
                <td>
                    {open ? (
                        <ChevronDown size={14} className="text-indigo-400" />
                    ) : (
                        <ChevronRight size={14} className="text-slate-500" />
                    )}
                </td>
            </tr>
            {open && (
                <tr>
                    <td colSpan={6} className="!p-0">
                        <AnimatePresence>
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="trace-detail"
                            >
                                {spans.length === 0 ? (
                                    <p className="text-[10px] text-slate-500 italic">
                                        Không có span chi tiết cho lượt này.
                                    </p>
                                ) : (
                                    <div>
                                        <p className="text-[9px] text-slate-500 font-black uppercase tracking-widest mb-3">
                                            Node Spans — {spans.length} bước
                                        </p>
                                        {spans.map((s, i) => (
                                            <SpanRow key={i} span={s} maxMs={maxMs} />
                                        ))}
                                    </div>
                                )}
                                <div className="mt-3 pt-3 border-t border-white/5 flex gap-8 text-[9px] text-slate-500 font-black uppercase tracking-widest">
                                    <span>
                                        Session:{' '}
                                        <span className="text-slate-300 font-mono">
                                            {trace.session_id.slice(0, 16)}…
                                        </span>
                                    </span>
                                    <span>
                                        Reply len:{' '}
                                        <span className="text-slate-300">{trace.reply_len} chars</span>
                                    </span>
                                </div>
                            </motion.div>
                        </AnimatePresence>
                    </td>
                </tr>
            )}
        </>
    )
}

export default function AdminSystemTrace() {
    const [traces, setTraces] = useState<AdminTraceRecord[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const loadTraces = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await adminService.getRecentTraces(100)
            setTraces(res.traces)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Không tải được traces.')
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        loadTraces()
    }, [loadTraces])

    return (
        <div className="trace-root">
            <div className="trace-header">
                <div>
                    <h1 className="text-4xl font-black text-white tracking-tighter uppercase mb-1 flex items-center gap-3">
                        <Cpu className="text-indigo-400" size={32} />
                        Luồng hệ thống
                    </h1>
                    <p className="text-[10px] text-slate-500 font-black uppercase tracking-[0.3em]">
                        {traces.length} lượt gần nhất · Latency per node · Route decisions
                    </p>
                </div>
                <button
                    onClick={loadTraces}
                    disabled={loading}
                    className="flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 rounded-2xl text-[10px] font-black text-white uppercase hover:bg-white/10 transition-all tracking-widest"
                >
                    <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                    Làm mới
                </button>
            </div>

            {error && (
                <div className="mb-6 px-6 py-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400 text-sm font-black uppercase">
                    {error}
                </div>
            )}

            {loading ? (
                <div className="space-y-2">
                    {Array.from({ length: 8 }).map((_, i) => (
                        <div key={i} className="admin-skeleton h-14 w-full rounded-2xl" />
                    ))}
                </div>
            ) : traces.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-32 text-slate-600">
                    <Activity size={40} className="mb-4 opacity-20" />
                    <p className="text-[11px] font-black uppercase tracking-widest">
                        Chưa có trace nào được ghi nhận
                    </p>
                    <p className="text-[10px] text-slate-700 mt-2">
                        Traces sẽ xuất hiện sau khi có cuộc hội thoại đầu tiên.
                    </p>
                </div>
            ) : (
                <table className="trace-table">
                    <thead>
                        <tr>
                            <th>Thời gian</th>
                            <th>User hash</th>
                            <th>Distress</th>
                            <th>Route</th>
                            <th>Tổng độ trễ</th>
                            <th />
                        </tr>
                    </thead>
                    <tbody>
                        {traces.map((trace) => (
                            <TraceRow key={trace.turn_id} trace={trace} />
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    )
}
