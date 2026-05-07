import './AdminCrisisLogs.css'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'react-toastify'
import { ApiRequestError } from '../../api/types'
import { adminService, type AdminCrisisLog } from '../../services/adminService'

const SEVERITY_CONFIG: Record<string, { label: string; color: string; bg: string; icon: string }> = {
    critical: { label: 'Nghiêm trọng', color: '#f87171', bg: 'rgba(248,113,113,0.1)', icon: '🔴' },
    high: { label: 'Cao', color: '#fb923c', bg: 'rgba(251,146,60,0.1)', icon: '🟠' },
    medium: { label: 'Trung bình', color: '#fbbf24', bg: 'rgba(251,191,36,0.1)', icon: '🟡' },
    low: { label: 'Thấp', color: '#34d399', bg: 'rgba(52,211,153,0.1)', icon: '🟢' },
}

function getSeverity(mucDo: string) {
    return SEVERITY_CONFIG[mucDo] || SEVERITY_CONFIG['medium']
}

function formatTime(iso: string): string {
    const d = new Date(iso)
    return d.toLocaleString('vi-VN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    })
}

function formatRelative(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime()
    const minutes = Math.floor(diff / 60000)
    if (minutes < 60) return `${minutes} phút trước`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours} giờ trước`
    const days = Math.floor(hours / 24)
    return `${days} ngày trước`
}

type FilterStatus = 'all' | 'pending' | 'reviewed'

export default function AdminCrisisLogs() {
    const [logs, setLogs] = useState<AdminCrisisLog[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [notes, setNotes] = useState<Record<string, string>>({})
    const [busyId, setBusyId] = useState<string | null>(null)
    const [filterStatus, setFilterStatus] = useState<FilterStatus>('all')
    const [expandedId, setExpandedId] = useState<string | null>(null)

    const load = async () => {
        setLoading(true)
        setError('')
        try {
            const data = await adminService.getCrisisLogs()
            setLogs(data.logs)
        } catch (err) {
            if (err instanceof ApiRequestError) setError(err.message)
            else setError('Không tải được nhật ký khẩn.')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        void load()
    }, [])

    const review = async (logId: string, reviewed: boolean) => {
        setBusyId(logId)
        try {
            await adminService.reviewCrisisLog(logId, {
                reviewed,
                note: notes[logId] || null,
            })
            setLogs((prev) => prev.map((item) => (item.log_id === logId ? { ...item, reviewed } : item)))
            toast.success('Đã cập nhật trạng thái.')
        } catch (err) {
            if (err instanceof ApiRequestError && err.handledByModal) return
            if (err instanceof ApiRequestError) toast.error(err.message)
            else toast.error('Không thể cập nhật.')
        } finally {
            setBusyId(null)
        }
    }

    const filteredLogs = useMemo(() => {
        if (filterStatus === 'pending') return logs.filter((l) => !l.reviewed)
        if (filterStatus === 'reviewed') return logs.filter((l) => l.reviewed)
        return logs
    }, [logs, filterStatus])

    const stats = useMemo(() => {
        const total = logs.length
        const pending = logs.filter((l) => !l.reviewed).length
        const reviewed = logs.filter((l) => l.reviewed).length
        const critical = logs.filter((l) => l.muc_do === 'critical').length
        return { total, pending, reviewed, critical }
    }, [logs])

    return (
        <section className="crisis-root">
            {/* ── Header ── */}
            <header className="crisis-header">
                <div>
                    <h1 className="crisis-title">Nhật ký sự kiện khẩn</h1>
                    <p className="crisis-subtitle">Theo dõi và xử lý các sự kiện khẩn cấp từ người dùng.</p>
                </div>
                <button type="button" onClick={() => void load()} className="crisis-refresh-btn">
                    🔄 Tải lại
                </button>
            </header>

            {error && <p className="crisis-error">{error}</p>}

            {/* ── Stats Summary ── */}
            <div className="crisis-stats-grid">
                <div className="crisis-stat-card">
                    <span className="crisis-stat-icon">📋</span>
                    <div>
                        <p className="crisis-stat-value">{stats.total}</p>
                        <p className="crisis-stat-label">Tổng cộng</p>
                    </div>
                </div>
                <div className="crisis-stat-card crisis-stat-pending">
                    <span className="crisis-stat-icon">⏳</span>
                    <div>
                        <p className="crisis-stat-value">{stats.pending}</p>
                        <p className="crisis-stat-label">Chờ xử lý</p>
                    </div>
                </div>
                <div className="crisis-stat-card crisis-stat-reviewed">
                    <span className="crisis-stat-icon">✅</span>
                    <div>
                        <p className="crisis-stat-value">{stats.reviewed}</p>
                        <p className="crisis-stat-label">Đã xem xét</p>
                    </div>
                </div>
                <div className="crisis-stat-card crisis-stat-critical">
                    <span className="crisis-stat-icon">🚨</span>
                    <div>
                        <p className="crisis-stat-value">{stats.critical}</p>
                        <p className="crisis-stat-label">Nghiêm trọng</p>
                    </div>
                </div>
            </div>

            {/* ── Filter Tabs ── */}
            <div className="crisis-filter-bar">
                <div className="crisis-filter-tabs">
                    {(['all', 'pending', 'reviewed'] as FilterStatus[]).map((f) => (
                        <button
                            key={f}
                            className={`crisis-filter-tab ${filterStatus === f ? 'active' : ''}`}
                            onClick={() => setFilterStatus(f)}
                        >
                            {f === 'all' ? 'Tất cả' : f === 'pending' ? '⏳ Chờ xử lý' : '✅ Đã xem xét'}
                            <span className="crisis-filter-count">
                                {f === 'all' ? stats.total : f === 'pending' ? stats.pending : stats.reviewed}
                            </span>
                        </button>
                    ))}
                </div>
            </div>

            {loading && <p className="crisis-loading">Đang tải dữ liệu...</p>}

            {/* ── Timeline ── */}
            <div className="crisis-timeline">
                {filteredLogs.map((item) => {
                    const sev = getSeverity(item.muc_do)
                    const isExpanded = expandedId === item.log_id

                    return (
                        <div key={item.log_id} className={`crisis-timeline-item ${item.reviewed ? 'reviewed' : 'pending'}`}>
                            {/* Timeline dot */}
                            <div className="crisis-timeline-dot" style={{ background: sev.color, boxShadow: `0 0 10px ${sev.color}40` }} />

                            {/* Card */}
                            <div className="crisis-timeline-card" onClick={() => setExpandedId(isExpanded ? null : item.log_id)}>
                                <div className="crisis-card-header">
                                    <div className="crisis-card-left">
                                        <span className="crisis-severity-badge" style={{ background: sev.bg, color: sev.color }}>
                                            {sev.icon} {sev.label}
                                        </span>
                                        <span className="crisis-card-id">{item.log_id}</span>
                                    </div>
                                    <div className="crisis-card-right">
                                        <span className={`crisis-review-badge ${item.reviewed ? 'done' : 'wait'}`}>
                                            {item.reviewed ? '✓ Đã xem xét' : '⏳ Chờ xử lý'}
                                        </span>
                                        <span className="crisis-card-chevron">{isExpanded ? '▲' : '▼'}</span>
                                    </div>
                                </div>
                                <div className="crisis-card-meta">
                                    <span>📍 Phiên: {item.session_id.slice(0, 16)}...</span>
                                    <span>🕐 {formatTime(item.triggered_at)}</span>
                                    <span className="crisis-card-relative">{formatRelative(item.triggered_at)}</span>
                                </div>

                                {/* Expanded content */}
                                {isExpanded && (
                                    <div className="crisis-card-expanded" onClick={(e) => e.stopPropagation()}>
                                        <textarea
                                            value={notes[item.log_id] ?? ''}
                                            onChange={(e) => setNotes((prev) => ({ ...prev, [item.log_id]: e.target.value }))}
                                            placeholder="Ghi chú xử lý (tuỳ chọn)..."
                                            rows={3}
                                            className="crisis-note-input"
                                        />
                                        <div className="crisis-card-actions">
                                            <button
                                                type="button"
                                                disabled={busyId === item.log_id}
                                                onClick={() => void review(item.log_id, true)}
                                                className="crisis-btn-approve"
                                            >
                                                ✓ Đánh dấu đã xem xét
                                            </button>
                                            <button
                                                type="button"
                                                disabled={busyId === item.log_id}
                                                onClick={() => void review(item.log_id, false)}
                                                className="crisis-btn-unreview"
                                            >
                                                ↺ Bỏ xem xét
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )
                })}

                {!loading && filteredLogs.length === 0 && (
                    <div className="crisis-empty">
                        <p>🎉 Không có sự kiện khẩn nào {filterStatus !== 'all' ? 'trong bộ lọc này' : ''}.</p>
                    </div>
                )}
            </div>
        </section>
    )
}
