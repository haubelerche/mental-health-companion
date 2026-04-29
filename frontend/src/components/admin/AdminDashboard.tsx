import { useEffect, useState } from 'react'
import { ApiRequestError } from '../../api/types'
import { adminService, type AdminAuthLatencyResponse, type AdminCostDashboardResponse, type AdminDashboardAggregate } from '../../services/adminService'

function numberOrDash(value: number | undefined): string {
    if (typeof value !== 'number' || Number.isNaN(value)) return '-'
    return value.toLocaleString('vi-VN')
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
                else setError('Không tải được dashboard admin.')
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
        <section className="space-y-4">
            <header>
                <h1 className="font-display text-3xl text-serene-ink">Admin dashboard</h1>
                <p className="text-sm text-serene-muted">Tổng quan sessions, sự kiện SOS, SLA auth và chi phí chat.</p>
            </header>

            {error ? <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}

            <div className="grid gap-3 md:grid-cols-4">
                <article className="rounded-2xl bg-white/80 p-4 shadow">
                    <p className="text-xs text-serene-muted">Total sessions</p>
                    <p className="mt-1 text-2xl font-semibold text-serene-ink">{loading ? '...' : numberOrDash(aggregate?.total_sessions)}</p>
                </article>
                <article className="rounded-2xl bg-white/80 p-4 shadow">
                    <p className="text-xs text-serene-muted">SOS events</p>
                    <p className="mt-1 text-2xl font-semibold text-serene-ink">{loading ? '...' : numberOrDash(aggregate?.sos_events)}</p>
                </article>
                <article className="rounded-2xl bg-white/80 p-4 shadow">
                    <p className="text-xs text-serene-muted">Auth login p95 (ms)</p>
                    <p className="mt-1 text-2xl font-semibold text-serene-ink">{loading ? '...' : numberOrDash(latency?.login.p95_ms)}</p>
                </article>
                <article className="rounded-2xl bg-white/80 p-4 shadow">
                    <p className="text-xs text-serene-muted">Estimated cost (USD)</p>
                    <p className="mt-1 text-2xl font-semibold text-serene-ink">
                        {loading ? '...' : typeof cost?.chat_cost.estimated_cost_usd === 'number' ? `$${cost.chat_cost.estimated_cost_usd.toFixed(4)}` : '-'}
                    </p>
                </article>
            </div>

            <div className="grid gap-3 lg:grid-cols-2">
                <article className="rounded-2xl bg-white/80 p-4 shadow">
                    <h2 className="text-sm font-semibold text-serene-ink">Mood distribution</h2>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                        {Object.entries(aggregate?.mood_distribution ?? {}).map(([key, value]) => (
                            <div key={key} className="rounded-xl border border-serene-primary/15 px-3 py-2">
                                <p className="text-serene-muted">{key}</p>
                                <p className="font-semibold text-serene-ink">{numberOrDash(value)}</p>
                            </div>
                        ))}
                    </div>
                </article>
                <article className="rounded-2xl bg-white/80 p-4 shadow">
                    <h2 className="text-sm font-semibold text-serene-ink">Auth latency SLA</h2>
                    <div className="mt-2 space-y-2 text-sm">
                        <div className="rounded-xl border border-serene-primary/15 px-3 py-2">
                            <p className="text-serene-muted">Login</p>
                            <p className="text-serene-ink">
                                p95 {numberOrDash(latency?.login.p95_ms)} / target {numberOrDash(latency?.login.target_p95_ms)} —{' '}
                                {latency?.login.within_sla ? 'within SLA' : 'out of SLA'}
                            </p>
                        </div>
                        <div className="rounded-xl border border-serene-primary/15 px-3 py-2">
                            <p className="text-serene-muted">Signup</p>
                            <p className="text-serene-ink">
                                p95 {numberOrDash(latency?.signup.p95_ms)} / target {numberOrDash(latency?.signup.target_p95_ms)} —{' '}
                                {latency?.signup.within_sla ? 'within SLA' : 'out of SLA'}
                            </p>
                        </div>
                    </div>
                </article>
            </div>
        </section>
    )
}
