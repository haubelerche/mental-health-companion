import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'react-toastify'
import { ApiRequestError } from '../../api/types'
import {
    ADMIN_RESOURCE_CATEGORIES,
    ADMIN_RESOURCE_FORMATS,
    adminService,
    type AdminResource,
    type AdminResourceCreatePayload,
} from '../../services/adminService'

function toTagList(value: string): string[] {
    return value
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean)
}

const defaultForm: AdminResourceCreatePayload = {
    category: 'meditate',
    title: '',
    description: '',
    format: 'audio',
    duration_sec: 300,
    storage_key: '',
    external_url: '',
    thumbnail_key: '',
    tags: [],
    is_active: true,
}

export default function AdminResources() {
    const [resources, setResources] = useState<AdminResource[]>([])
    const [categoryFilter, setCategoryFilter] = useState('')
    const [includeInactive, setIncludeInactive] = useState(true)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [busy, setBusy] = useState(false)
    const [editingId, setEditingId] = useState<string | null>(null)
    const [form, setForm] = useState(defaultForm)
    const [tagsInput, setTagsInput] = useState('')

    const submitLabel = useMemo(() => (editingId ? 'Cập nhật' : 'Tạo resource'), [editingId])

    const load = useCallback(async () => {
        setLoading(true)
        setError('')
        try {
            const data = await adminService.listResources({
                category: categoryFilter || undefined,
                include_inactive: includeInactive,
                limit: 100,
                offset: 0,
            })
            setResources(data.items)
        } catch (err) {
            if (err instanceof ApiRequestError) setError(err.message)
            else setError('Không tải được resources.')
        } finally {
            setLoading(false)
        }
    }, [categoryFilter, includeInactive])

    useEffect(() => {
        void load()
    }, [load])

    const resetForm = () => {
        setEditingId(null)
        setForm(defaultForm)
        setTagsInput('')
    }

    const submit = async () => {
        const hasStorage = Boolean(form.storage_key?.trim())
        const hasExternal = Boolean(form.external_url?.trim())
        if (!form.title.trim() || (!hasStorage && !hasExternal)) {
            toast.error('Thiếu title hoặc storage_key / external_url.')
            return
        }
        setBusy(true)
        const payload = {
            ...form,
            storage_key: hasStorage ? form.storage_key?.trim() : null,
            external_url: hasExternal ? form.external_url?.trim() : null,
            thumbnail_key: form.thumbnail_key?.trim() || null,
            description: form.description?.trim() || null,
            tags: toTagList(tagsInput),
        }
        try {
            if (editingId) {
                await adminService.updateResource(editingId, payload)
                toast.success('Đã cập nhật resource.')
            } else {
                await adminService.createResource(payload)
                toast.success('Đã tạo resource.')
            }
            resetForm()
            await load()
        } catch (err) {
            if (err instanceof ApiRequestError) toast.error(err.message)
            else toast.error('Không thể lưu resource.')
        } finally {
            setBusy(false)
        }
    }

    const startEdit = (item: AdminResource) => {
        setEditingId(item.resource_id)
        setForm({
            category: item.category,
            title: item.title,
            description: item.description ?? '',
            format: item.format,
            duration_sec: item.duration_sec,
            storage_key: item.storage_key,
            external_url: item.external_url ?? '',
            thumbnail_key: item.thumbnail_key ?? '',
            tags: item.tags,
            is_active: item.is_active,
        })
        setTagsInput(item.tags.join(', '))
    }

    const remove = async (resourceId: string) => {
        if (!window.confirm(`Xóa resource ${resourceId}?`)) return
        setBusy(true)
        try {
            await adminService.deleteResource(resourceId)
            toast.success('Đã xóa resource.')
            await load()
        } catch (err) {
            if (err instanceof ApiRequestError) toast.error(err.message)
            else toast.error('Không thể xóa resource.')
        } finally {
            setBusy(false)
        }
    }

    return (
        <section className="space-y-4">
            <header>
                <h1 className="font-display text-3xl text-serene-ink">Admin resources</h1>
                <p className="text-sm text-serene-muted">Quản lý tài nguyên bằng toàn bộ API admin resources.</p>
            </header>

            {error ? <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}

            <article className="rounded-2xl bg-white/80 p-4 shadow">
                <h2 className="mb-3 text-sm font-semibold text-serene-ink">{submitLabel}</h2>
                <div className="grid gap-2 md:grid-cols-2">
                    <input
                        value={form.title}
                        onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
                        placeholder="Title"
                        className="rounded-lg border border-serene-primary/20 p-2 text-sm"
                    />
                    <select
                        value={form.category}
                        onChange={(event) => setForm((prev) => ({ ...prev, category: event.target.value }))}
                        className="rounded-lg border border-serene-primary/20 p-2 text-sm"
                    >
                        {ADMIN_RESOURCE_CATEGORIES.map((cat) => (
                            <option key={cat} value={cat}>{cat}</option>
                        ))}
                    </select>
                    <select
                        value={form.format}
                        onChange={(event) => setForm((prev) => ({ ...prev, format: event.target.value }))}
                        className="rounded-lg border border-serene-primary/20 p-2 text-sm"
                    >
                        {ADMIN_RESOURCE_FORMATS.map((fmt) => (
                            <option key={fmt} value={fmt}>{fmt}</option>
                        ))}
                    </select>
                    <input
                        type="number"
                        min={1}
                        value={form.duration_sec}
                        onChange={(event) => setForm((prev) => ({ ...prev, duration_sec: Number(event.target.value) || 1 }))}
                        placeholder="Duration seconds"
                        className="rounded-lg border border-serene-primary/20 p-2 text-sm"
                    />
                    <input
                        value={form.storage_key}
                        onChange={(event) => setForm((prev) => ({ ...prev, storage_key: event.target.value }))}
                        placeholder="storage_key (optional nếu có external_url)"
                        className="rounded-lg border border-serene-primary/20 p-2 text-sm md:col-span-2"
                    />
                    <input
                        value={form.external_url ?? ''}
                        onChange={(event) => setForm((prev) => ({ ...prev, external_url: event.target.value }))}
                        placeholder="external_url (YouTube URL nếu có)"
                        className="rounded-lg border border-serene-primary/20 p-2 text-sm md:col-span-2"
                    />
                    <input
                        value={form.thumbnail_key ?? ''}
                        onChange={(event) => setForm((prev) => ({ ...prev, thumbnail_key: event.target.value }))}
                        placeholder="thumbnail_key (optional)"
                        className="rounded-lg border border-serene-primary/20 p-2 text-sm md:col-span-2"
                    />
                    <input
                        value={tagsInput}
                        onChange={(event) => setTagsInput(event.target.value)}
                        placeholder="tags, cách nhau dấu phẩy"
                        className="rounded-lg border border-serene-primary/20 p-2 text-sm md:col-span-2"
                    />
                    <textarea
                        value={form.description ?? ''}
                        onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
                        rows={3}
                        placeholder="Description"
                        className="rounded-lg border border-serene-primary/20 p-2 text-sm md:col-span-2"
                    />
                    <label className="inline-flex items-center gap-2 text-sm text-serene-ink">
                        <input
                            type="checkbox"
                            checked={form.is_active}
                            onChange={(event) => setForm((prev) => ({ ...prev, is_active: event.target.checked }))}
                        />
                        is_active
                    </label>
                </div>
                <div className="mt-3 flex gap-2">
                    <button type="button" disabled={busy} onClick={() => void submit()} className="rounded-lg bg-serene-primary px-3 py-2 text-sm text-serene-on-primary disabled:opacity-60">
                        {submitLabel}
                    </button>
                    {editingId ? (
                        <button type="button" onClick={resetForm} className="rounded-lg border border-serene-primary/20 px-3 py-2 text-sm text-serene-ink">
                            Huỷ edit
                        </button>
                    ) : null}
                </div>
            </article>

            <article className="rounded-2xl bg-white/80 p-4 shadow">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                    <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)} className="rounded-lg border border-serene-primary/20 p-2 text-sm">
                        <option value="">All categories</option>
                        {ADMIN_RESOURCE_CATEGORIES.map((cat) => (
                            <option key={cat} value={cat}>{cat}</option>
                        ))}
                    </select>
                    <label className="inline-flex items-center gap-2 text-sm text-serene-ink">
                        <input type="checkbox" checked={includeInactive} onChange={(event) => setIncludeInactive(event.target.checked)} />
                        include inactive
                    </label>
                    <button type="button" onClick={() => void load()} className="rounded-lg border border-serene-primary/20 px-3 py-2 text-sm">
                        Refresh
                    </button>
                </div>
                {loading ? <p className="text-sm text-serene-muted">Đang tải resources...</p> : null}
                <div className="space-y-2">
                    {resources.map((item) => (
                        <div key={item.resource_id} className="rounded-xl border border-serene-primary/15 p-3 text-sm">
                            <div className="flex flex-wrap items-start justify-between gap-2">
                                <div>
                                    <p className="font-semibold text-serene-ink">{item.title}</p>
                                    <p className="text-serene-muted">{item.resource_id} • {item.category} • {item.format}</p>
                                    <p className="text-serene-muted">duration {item.duration_sec}s • {item.is_active ? 'active' : 'inactive'}</p>
                                </div>
                                <div className="flex gap-2">
                                    <button type="button" onClick={() => startEdit(item)} className="rounded-lg border border-serene-primary/20 px-3 py-1.5">Edit</button>
                                    <button type="button" disabled={busy} onClick={() => void remove(item.resource_id)} className="rounded-lg border border-rose-200 px-3 py-1.5 text-rose-700">Delete</button>
                                </div>
                            </div>
                        </div>
                    ))}
                    {!loading && resources.length === 0 ? <p className="text-sm text-serene-muted">Chưa có resource nào.</p> : null}
                </div>
            </article>
        </section>
    )
}
