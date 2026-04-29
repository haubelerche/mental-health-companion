import { useEffect, useState } from 'react'
import { toast } from 'react-toastify'
import { ApiRequestError } from '../../api/types'
import { adminService, type AdminCrisisLog } from '../../services/adminService'

export default function AdminCrisisLogs() {
    const [logs, setLogs] = useState<AdminCrisisLog[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [notes, setNotes] = useState<Record<string, string>>({})
    const [busyId, setBusyId] = useState<string | null>(null)

    const load = async () => {
        setLoading(true)
        setError('')
        try {
            const data = await adminService.getCrisisLogs()
            setLogs(data.logs)
        } catch (err) {
            if (err instanceof ApiRequestError) setError(err.message)
            else setError('Không tải được crisis logs.')
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
            toast.success('Đã cập nhật trạng thái review.')
        } catch (err) {
            if (err instanceof ApiRequestError) toast.error(err.message)
            else toast.error('Không thể review log.')
        } finally {
            setBusyId(null)
        }
    }

    return (
        <section className="space-y-4">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="font-display text-3xl text-serene-ink">Crisis logs</h1>
                    <p className="text-sm text-serene-muted">Review nhanh các sự kiện khẩn để theo dõi vận hành.</p>
                </div>
                <button type="button" onClick={() => void load()} className="rounded-lg border border-serene-primary/20 px-3 py-2 text-sm hover:bg-serene-primary/10">
                    Tải lại
                </button>
            </header>

            {error ? <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
            {loading ? <p className="text-sm text-serene-muted">Đang tải...</p> : null}

            <div className="space-y-3">
                {logs.map((item) => (
                    <article key={item.log_id} className="rounded-2xl bg-white/80 p-4 shadow">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <div>
                                <p className="text-sm font-semibold text-serene-ink">{item.log_id}</p>
                                <p className="text-xs text-serene-muted">Session: {item.session_id}</p>
                                <p className="text-xs text-serene-muted">Level: {item.muc_do}</p>
                            </div>
                            <span className={`rounded-full px-2 py-1 text-xs ${item.reviewed ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                                {item.reviewed ? 'Reviewed' : 'Pending'}
                            </span>
                        </div>
                        <p className="mt-2 text-xs text-serene-muted">Triggered: {new Date(item.triggered_at).toLocaleString('vi-VN')}</p>
                        <textarea
                            value={notes[item.log_id] ?? ''}
                            onChange={(event) => setNotes((prev) => ({ ...prev, [item.log_id]: event.target.value }))}
                            placeholder="Ghi chú review (tuỳ chọn)"
                            rows={2}
                            className="mt-3 w-full rounded-xl border border-serene-primary/20 bg-white p-2 text-sm outline-none"
                        />
                        <div className="mt-2 flex gap-2">
                            <button
                                type="button"
                                disabled={busyId === item.log_id}
                                onClick={() => void review(item.log_id, true)}
                                className="rounded-lg bg-serene-primary px-3 py-2 text-sm text-serene-on-primary disabled:opacity-60"
                            >
                                Đánh dấu reviewed
                            </button>
                            <button
                                type="button"
                                disabled={busyId === item.log_id}
                                onClick={() => void review(item.log_id, false)}
                                className="rounded-lg border border-serene-primary/20 px-3 py-2 text-sm text-serene-ink disabled:opacity-60"
                            >
                                Bỏ reviewed
                            </button>
                        </div>
                    </article>
                ))}
                {!loading && logs.length === 0 ? (
                    <p className="rounded-xl bg-white/70 px-3 py-2 text-sm text-serene-muted">Chưa có crisis logs.</p>
                ) : null}
            </div>
        </section>
    )
}
