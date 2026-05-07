import './AdminDashboard.css'
import { useEffect, useState } from 'react'
import { ApiRequestError } from '../../api/types'
import {
    adminService,
    type AdminAuthLatencyResponse,
    type AdminCostDashboardResponse,
    type AdminDashboardAggregate,
} from '../../services/adminService'

function numberOrDash(value: number | undefined): string {
    if (typeof value !== 'number' || Number.isNaN(value)) return '-'
    return value.toLocaleString('vi-VN')
}

/* ── Mini Bar Chart ── */
function MoodBarChart({ data }: { data: Record<string, number> }) {
    const entries = Object.entries(data)
    const max = Math.max(...entries.map(([, v]) => v), 1)

    const MOOD_LABELS: Record<string, { label: string; color: string; emoji: string }> = {
        great: { label: 'Rất tốt', color: '#34d399', emoji: '😊' },
        okay: { label: 'Ổn', color: '#60a5fa', emoji: '🙂' },
        stressed: { label: 'Căng thẳng', color: '#fbbf24', emoji: '😰' },
        struggling: { label: 'Khó khăn', color: '#f87171', emoji: '😞' },
    }

    return (
        <div className="dash-mood-chart">
            {entries.map(([key, value]) => {
                const info = MOOD_LABELS[key] || { label: key, color: '#94a3b8', emoji: '•' }
                const pct = Math.round((value / max) * 100)
                return (
                    <div key={key} className="dash-mood-bar-row">
                        <div className="dash-mood-bar-label">
                            <span className="dash-mood-emoji">{info.emoji}</span>
                            <span>{info.label}</span>
                        </div>
                        <div className="dash-mood-bar-track">
                            <div
                                className="dash-mood-bar-fill"
                                style={{ width: `${pct}%`, background: info.color }}
                            />
                        </div>
                        <span className="dash-mood-bar-value">{value}</span>
                    </div>
                )
            })}
        </div>
    )
}

/* ── Donut Chart ── */
function TokenDonut({ input, output }: { input: number; output: number }) {
    const total = input + output || 1
    const inputPct = (input / total) * 100
    const outputPct = (output / total) * 100
    const inputDeg = (inputPct / 100) * 360

    return (
        <div className="dash-donut-container">
            <div
                className="dash-donut"
                style={{
                    background: `conic-gradient(#60a5fa 0deg ${inputDeg}deg, #f472b6 ${inputDeg}deg 360deg)`,
                }}
            >
                <div className="dash-donut-inner">
                    <span className="dash-donut-total">{(total / 1000).toFixed(1)}k</span>
                    <span className="dash-donut-sub">tokens</span>
                </div>
            </div>
            <div className="dash-donut-legend">
                <div className="dash-donut-legend-item">
                    <span className="dash-donut-dot" style={{ background: '#60a5fa' }} />
                    <span>Input ({inputPct.toFixed(0)}%)</span>
                </div>
                <div className="dash-donut-legend-item">
                    <span className="dash-donut-dot" style={{ background: '#f472b6' }} />
                    <span>Output ({outputPct.toFixed(0)}%)</span>
                </div>
            </div>
        </div>
    )
}

/* ── SLA Gauge ── */
function SlaGauge({ label, p95, target, withinSla, successRate }: { label: string; p95: number; target: number; withinSla: boolean; successRate: number }) {
    const ratio = Math.min(p95 / (target || 1), 2)
    const deg = ratio * 180
    const color = withinSla ? '#34d399' : '#f87171'

    return (
        <div className="dash-sla-gauge">
            <p className="dash-sla-label">{label}</p>
            <div className="dash-sla-meter">
                <div className="dash-sla-meter-bg" />
                <div
                    className="dash-sla-meter-fill"
                    style={{
                        transform: `rotate(${Math.min(deg, 180)}deg)`,
                        background: color,
                    }}
                />
                <div className="dash-sla-meter-center">
                    <span className="dash-sla-value" style={{ color }}>{p95}ms</span>
                    <span className="dash-sla-target">mục tiêu {target}ms</span>
                </div>
            </div>
            <div className="dash-sla-footer">
                <span className={`dash-sla-badge ${withinSla ? 'ok' : 'fail'}`}>
                    {withinSla ? '✓ Đạt SLA' : '✗ Vượt SLA'}
                </span>
                <span className="dash-sla-rate">Tỉ lệ: {(successRate * 100).toFixed(0)}%</span>
            </div>
        </div>
    )
}

/* ═══════ MAIN COMPONENT ═══════ */
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
        return () => {
            active = false
        }
    }, [])

    return (
        <section className="dash-root">
            {/* ── Header ── */}
            <header className="dash-header">
                <div>
                    <h1 className="dash-title">Tổng quan hệ thống</h1>
                    <p className="dash-subtitle">
                        Thống kê phiên, cảm xúc, hiệu suất xác thực và chi phí vận hành.
                    </p>
                </div>
                {aggregate?.period && (
                    <span className="dash-period-badge">
                        📅 {aggregate.period.from} → {aggregate.period.to}
                    </span>
                )}
            </header>

            {error && <p className="dash-error">{error}</p>}

            {/* ── KPI Cards ── */}
            <div className="dash-kpi-grid">
                <div className="dash-kpi-card">
                    <div className="dash-kpi-icon" style={{ background: 'rgba(96,165,250,0.12)', color: '#60a5fa' }}>📊</div>
                    <div>
                        <p className="dash-kpi-label">Tổng phiên trò chuyện</p>
                        <p className="dash-kpi-value">{loading ? '...' : numberOrDash(aggregate?.total_sessions)}</p>
                    </div>
                </div>
                <div className="dash-kpi-card">
                    <div className="dash-kpi-icon" style={{ background: 'rgba(248,113,113,0.12)', color: '#f87171' }}>🚨</div>
                    <div>
                        <p className="dash-kpi-label">Sự kiện SOS</p>
                        <p className="dash-kpi-value">{loading ? '...' : numberOrDash(aggregate?.sos_events)}</p>
                    </div>
                </div>
                <div className="dash-kpi-card">
                    <div className="dash-kpi-icon" style={{ background: 'rgba(251,191,36,0.12)', color: '#fbbf24' }}>⚡</div>
                    <div>
                        <p className="dash-kpi-label">Auth P95 (Login)</p>
                        <p className="dash-kpi-value">{loading ? '...' : `${numberOrDash(latency?.login.p95_ms)} ms`}</p>
                    </div>
                </div>
                <div className="dash-kpi-card">
                    <div className="dash-kpi-icon" style={{ background: 'rgba(52,211,153,0.12)', color: '#34d399' }}>💰</div>
                    <div>
                        <p className="dash-kpi-label">Chi phí ước tính</p>
                        <p className="dash-kpi-value">
                            {loading ? '...' : typeof cost?.chat_cost.estimated_cost_usd === 'number' ? `$${cost.chat_cost.estimated_cost_usd.toFixed(4)}` : '-'}
                        </p>
                    </div>
                </div>
            </div>

            {/* ── Charts Row ── */}
            <div className="dash-charts-grid">
                {/* Mood Distribution */}
                <div className="dash-card">
                    <h2 className="dash-card-title">Phân bố cảm xúc</h2>
                    <p className="dash-card-desc">Tâm trạng người dùng trong giai đoạn.</p>
                    {aggregate?.mood_distribution ? (
                        <MoodBarChart data={aggregate.mood_distribution} />
                    ) : (
                        <p className="dash-placeholder">{loading ? 'Đang tải...' : 'Không có dữ liệu'}</p>
                    )}
                </div>

                {/* Token Usage */}
                <div className="dash-card">
                    <h2 className="dash-card-title">Sử dụng Token LLM</h2>
                    <p className="dash-card-desc">Phân bố token input/output từ chat AI.</p>
                    {cost?.chat_cost ? (
                        <>
                            <TokenDonut input={cost.chat_cost.total_input_tokens} output={cost.chat_cost.total_output_tokens} />
                            <div className="dash-token-stats">
                                <div className="dash-token-stat">
                                    <span className="dash-token-stat-label">Tổng lượt</span>
                                    <span className="dash-token-stat-value">{numberOrDash(cost.chat_cost.total_turns)}</span>
                                </div>
                                <div className="dash-token-stat">
                                    <span className="dash-token-stat-label">Tổng token</span>
                                    <span className="dash-token-stat-value">{numberOrDash(cost.chat_cost.total_tokens)}</span>
                                </div>
                            </div>
                        </>
                    ) : (
                        <p className="dash-placeholder">{loading ? 'Đang tải...' : 'Không có dữ liệu'}</p>
                    )}
                </div>
            </div>

            {/* ── SLA Gauges ── */}
            <div className="dash-card">
                <h2 className="dash-card-title">Hiệu suất xác thực (SLA)</h2>
                <p className="dash-card-desc">Giám sát thời gian phản hồi API đăng nhập và đăng ký.</p>
                {latency ? (
                    <div className="dash-sla-grid">
                        <SlaGauge
                            label="Đăng nhập"
                            p95={latency.login.p95_ms}
                            target={latency.login.target_p95_ms}
                            withinSla={latency.login.within_sla}
                            successRate={latency.login.success_rate}
                        />
                        <SlaGauge
                            label="Đăng ký"
                            p95={latency.signup.p95_ms}
                            target={latency.signup.target_p95_ms}
                            withinSla={latency.signup.within_sla}
                            successRate={latency.signup.success_rate}
                        />
                    </div>
                ) : (
                    <p className="dash-placeholder">{loading ? 'Đang tải...' : 'Không có dữ liệu'}</p>
                )}
            </div>

            {/* ── Top Categories ── */}
            {aggregate?.top_resource_categories && aggregate.top_resource_categories.length > 0 && (
                <div className="dash-card">
                    <h2 className="dash-card-title">Tài nguyên phổ biến nhất</h2>
                    <div className="dash-top-cats">
                        {aggregate.top_resource_categories.map((cat, i) => (
                            <span key={cat} className="dash-top-cat-chip">
                                {i === 0 ? '🥇' : i === 1 ? '🥈' : '🥉'} {cat}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </section>
    )
}
