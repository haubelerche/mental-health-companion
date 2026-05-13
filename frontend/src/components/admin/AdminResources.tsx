/* eslint-disable @typescript-eslint/no-explicit-any */
import './AdminResources.css'
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
import AgentFlowDiagram, {
    type AgentStep,
    type StepStatus,
    type AgentStepData,
    type AgentResult,
} from './AgentFlowDiagram'
import { Brain, Info } from 'lucide-react'

/* ─────────── helpers ─────────── */
function toTagList(value: string): string[] {
    return value
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean)
}

const CATEGORY_LABELS: Record<string, string> = {
    meditate: '🧘 Thiền định',
    sleep: '🌙 Ngủ ngon',
    music: '🎵 Âm nhạc',
    work_study: '📚 Tập trung học',
    wisdom: '💡 Kiến thức tâm lý',
    movement: '🏃 Vận động nhẹ',
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

type TabMode = 'manual' | 'agent'

const INITIAL_STEP_STATUSES: Record<AgentStep, StepStatus> = {
    idle: 'pending',
    keyword_generation: 'pending',
    youtube_search: 'pending',
    content_moderation: 'pending',
    db_insertion: 'pending',
    done: 'pending',
}

/* ═══════════════════════════════════════════════════════════════
   AdminResources – Dual-mode: Manual + Agent
   ═══════════════════════════════════════════════════════════════ */
export default function AdminResources() {
    /* ───── shared state ───── */
    const [resources, setResources] = useState<AdminResource[]>([])
    const [categoryFilter, setCategoryFilter] = useState('')
    const [includeInactive, setIncludeInactive] = useState(true)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [busy, setBusy] = useState(false)
    const [editingId, setEditingId] = useState<string | null>(null)
    const [form, setForm] = useState(defaultForm)
    const [tagsInput, setTagsInput] = useState('')
    const [activeTab, setActiveTab] = useState<TabMode>('agent')
    const [page, setPage] = useState(0)
    const [total, setTotal] = useState(0)
    const limit = 20

    /* ───── agent state ───── */
    const [agentCategory, setAgentCategory] = useState('meditate')
    const [agentLimit, setAgentLimit] = useState(5)
    const [agentRunning, setAgentRunning] = useState(false)
    const [agentCurrentStep, setAgentCurrentStep] = useState<AgentStep>('idle')
    const [agentStepStatuses, setAgentStepStatuses] = useState<Record<AgentStep, StepStatus>>({ ...INITIAL_STEP_STATUSES })
    const [agentStepData, setAgentStepData] = useState<Record<string, AgentStepData>>({})
    const [agentResults, setAgentResults] = useState<AgentResult[]>([])
    const [suggestion, setSuggestion] = useState<any>(null)
    const [loadingSuggestion, setLoadingSuggestion] = useState(false)

    const submitLabel = useMemo(() => (editingId ? 'Cập nhật' : 'Tạo resource'), [editingId])

    /* ───── resource list ───── */
    const load = useCallback(async () => {
        setLoading(true)
        setError('')
        try {
            const data = await adminService.listResources({
                category: categoryFilter || undefined,
                include_inactive: includeInactive,
                limit: limit,
                offset: page * limit,
            })
            setResources(data.items)
            setTotal(data.total)
        } catch (err) {
            if (err instanceof ApiRequestError && err.handledByModal) return
            if (err instanceof ApiRequestError) setError(err.message)
            else setError('Không tải được resources.')
        } finally {
            setLoading(false)
        }
    }, [categoryFilter, includeInactive, page])

    useEffect(() => {
        void load()
    }, [load, page])

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
            if (err instanceof ApiRequestError && err.handledByModal) return
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
            if (err instanceof ApiRequestError && err.handledByModal) return
            if (err instanceof ApiRequestError) toast.error(err.message)
            else toast.error('Không thể xóa resource.')
        } finally {
            setBusy(false)
        }
    }

    const getSmartSuggestion = async () => {
        setLoadingSuggestion(true)
        try {
            const data = await adminService.getEmotionResourceSuggestion()
            setSuggestion(data)
            if (data.suggestions && data.suggestions.length > 0) {
                setAgentCategory(data.suggestions[0].category)
                toast.info(`Hệ thống gợi ý bổ sung thêm tài nguyên: ${CATEGORY_LABELS[data.suggestions[0].category]}`)
            }
        } catch (err) {
            if (err instanceof ApiRequestError && err.handledByModal) return
            toast.error('Không thể lấy gợi ý thông minh')
        } finally {
            setLoadingSuggestion(false)
        }
    }

    /* ═══════ Agent Crawl SSE ═══════ */
    const startAgentCrawl = async () => {
        setAgentRunning(true)
        setAgentCurrentStep('idle')
        setAgentStepStatuses({ ...INITIAL_STEP_STATUSES })
        setAgentStepData({})
        setAgentResults([])

        try {
            const response = await adminService.agentCrawlResources({
                category: agentCategory,
                limit: agentLimit,
            })

            if (!response.ok) {
                toast.error('Agent crawl failed.')
                setAgentRunning(false)
                return
            }

            const reader = response.body?.getReader()
            if (!reader) {
                toast.error('Không thể đọc stream.')
                setAgentRunning(false)
                return
            }

            const decoder = new TextDecoder()
            let buffer = ''

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n')
                buffer = lines.pop() || ''

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue
                    try {
                        const parsed = JSON.parse(line.slice(6))
                        const event = parsed.event as AgentStep
                        const data = parsed.data as AgentStepData & { status?: string }

                        if (data.status === 'started') {
                            setAgentCurrentStep(event)
                            setAgentStepStatuses((prev) => ({ ...prev, [event]: 'active' as StepStatus }))
                        } else if (data.status === 'completed') {
                            setAgentStepStatuses((prev) => ({ ...prev, [event]: 'completed' as StepStatus }))
                            setAgentStepData((prev) => ({ ...prev, [event]: data }))

                            if (event === 'done' && data.results) {
                                setAgentResults(data.results)
                            }
                        }
                    } catch {
                        /* skip malformed lines */
                    }
                }
            }

            setAgentCurrentStep('done')
            toast.success('Agent crawl hoàn tất!')
            // Refresh resource list
            void load()
        } catch (err) {
            if (err instanceof ApiRequestError && err.handledByModal) return
            if (err instanceof ApiRequestError) toast.error(err.message)
            else toast.error('Agent crawl gặp lỗi.')
        } finally {
            setAgentRunning(false)
        }
    }

    /* ═══════════════════════════════════════ RENDER ═══════════════════════════════════════ */
    return (
        <section className="admin-resources-root">
            {/* ───── Header ───── */}
            <header className="admin-res-header">
                <div>
                    <h1 className="admin-res-title">Resource Management</h1>
                    <p className="admin-res-subtitle">Quản lý tài nguyên bằng toàn bộ API admin resources.</p>
                </div>
                {/* Tab Switcher */}
                <div className="admin-res-tabs">
                    <button
                        className={`admin-res-tab ${activeTab === 'agent' ? 'active' : ''}`}
                        onClick={() => setActiveTab('agent')}
                    >
                        <span className="admin-res-tab-icon">🤖</span>
                        Agent Mode
                    </button>
                    <button
                        className={`admin-res-tab ${activeTab === 'manual' ? 'active' : ''}`}
                        onClick={() => setActiveTab('manual')}
                    >
                        <span className="admin-res-tab-icon">✏️</span>
                        Manual Mode
                    </button>
                </div>
            </header>

            {error ? <p className="admin-res-error">{error}</p> : null}

            {/* ═════════ TAB: MANUAL MODE ═════════ */}
            {activeTab === 'manual' && (
                <>
                    <article className="admin-res-card">
                        <h2 className="admin-res-card-title">{submitLabel}</h2>
                        <div className="admin-res-form-grid">
                            <input
                                value={form.title}
                                onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
                                placeholder="Title"
                                className="admin-res-input"
                            />
                            <select
                                value={form.category}
                                onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}
                                className="admin-res-input"
                            >
                                {ADMIN_RESOURCE_CATEGORIES.map((cat) => (
                                    <option key={cat} value={cat}>{CATEGORY_LABELS[cat] || cat}</option>
                                ))}
                            </select>
                            <select
                                value={form.format}
                                onChange={(e) => setForm((p) => ({ ...p, format: e.target.value }))}
                                className="admin-res-input"
                            >
                                {ADMIN_RESOURCE_FORMATS.map((fmt) => (
                                    <option key={fmt} value={fmt}>{fmt}</option>
                                ))}
                            </select>
                            <input
                                type="number"
                                min={1}
                                value={form.duration_sec}
                                onChange={(e) => setForm((p) => ({ ...p, duration_sec: Number(e.target.value) || 1 }))}
                                placeholder="Duration seconds"
                                className="admin-res-input"
                            />
                            <input
                                value={form.storage_key || ''}
                                onChange={(e) => setForm((p) => ({ ...p, storage_key: e.target.value }))}
                                placeholder="storage_key (optional nếu có external_url)"
                                className="admin-res-input admin-res-input-wide"
                            />
                            <input
                                value={form.external_url ?? ''}
                                onChange={(e) => setForm((p) => ({ ...p, external_url: e.target.value }))}
                                placeholder="external_url (YouTube URL nếu có)"
                                className="admin-res-input admin-res-input-wide"
                            />
                            <input
                                value={form.thumbnail_key ?? ''}
                                onChange={(e) => setForm((p) => ({ ...p, thumbnail_key: e.target.value }))}
                                placeholder="thumbnail_key (optional)"
                                className="admin-res-input admin-res-input-wide"
                            />
                            <input
                                value={tagsInput}
                                onChange={(e) => setTagsInput(e.target.value)}
                                placeholder="tags, cách nhau dấu phẩy"
                                className="admin-res-input admin-res-input-wide"
                            />
                            <textarea
                                value={form.description ?? ''}
                                onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                                rows={3}
                                placeholder="Description"
                                className="admin-res-input admin-res-input-wide"
                            />
                            <label className="admin-res-checkbox-label">
                                <input
                                    type="checkbox"
                                    checked={form.is_active}
                                    onChange={(e) => setForm((p) => ({ ...p, is_active: e.target.checked }))}
                                />
                                is_active
                            </label>
                        </div>
                        <div className="admin-res-form-actions">
                            <button type="button" disabled={busy} onClick={() => void submit()} className="admin-res-btn-primary">
                                {submitLabel}
                            </button>
                            {editingId ? (
                                <button type="button" onClick={resetForm} className="admin-res-btn-outline">
                                    Huỷ edit
                                </button>
                            ) : null}
                        </div>
                    </article>
                </>
            )}

            {/* ═════════ TAB: AGENT MODE ═════════ */}
            {activeTab === 'agent' && (
                <div className="admin-agent-section">

                    {/* Control Panel */}
                    <div className="admin-agent-control-panel">
                        <div className="admin-agent-control-header">
                            <div className="flex justify-between items-start">
                                <div>
                                    <h2 className="admin-agent-control-title">🤖 YouTube Auto Crawl Agent</h2>
                                    <p className="admin-agent-control-desc">
                                        Chỉ cần chọn chủ đề và số lượng, AI Agent sẽ tự động tìm kiếm, kiểm duyệt và lưu video phù hợp.
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    className={`admin-agent-smart-btn ${loadingSuggestion ? 'loading' : ''}`}
                                    disabled={loadingSuggestion || agentRunning}
                                    onClick={() => void getSmartSuggestion()}
                                >
                                    {loadingSuggestion ? <span className="admin-agent-spinner-sm" /> : <Brain size={18} />}
                                    <span>🧠 Gợi ý thông minh</span>
                                </button>
                            </div>
                        </div>

                        {suggestion && (
                            <div className="admin-agent-suggestion-panel">
                                <div className="flex items-start gap-3">
                                    <div className="p-2 bg-indigo-500/20 rounded-lg text-indigo-400">
                                        <Info size={20} />
                                    </div>
                                    <div className="space-y-2 flex-1">
                                        <p className="text-sm text-slate-300">
                                            Dựa trên phân tích <b>7 ngày gần nhất</b>, hệ thống nhận thấy:
                                        </p>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            {suggestion.suggestions.map((s: any, idx: number) => (
                                                <div key={idx} className="bg-white/5 p-3 rounded-lg border border-white/5">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${s.priority === 'high' ? 'bg-rose-500/20 text-rose-400' : 'bg-amber-500/20 text-amber-400'}`}>
                                                            {s.priority} priority
                                                        </span>
                                                        <span className="text-sm font-bold text-white">{CATEGORY_LABELS[s.category]}</span>
                                                    </div>
                                                    <p className="text-xs text-slate-400 leading-relaxed">{s.reason}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                        <div className="admin-agent-control-body">
                            <div className="admin-agent-field">
                                <label className="admin-agent-label">Chủ đề (Category)</label>
                                <select
                                    value={agentCategory}
                                    onChange={(e) => setAgentCategory(e.target.value)}
                                    className="admin-agent-select"
                                    disabled={agentRunning}
                                >
                                    {ADMIN_RESOURCE_CATEGORIES.map((cat) => (
                                        <option key={cat} value={cat}>{CATEGORY_LABELS[cat] || cat}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="admin-agent-field">
                                <label className="admin-agent-label">Số lượng video</label>
                                <input
                                    type="number"
                                    min={1}
                                    max={50}
                                    value={agentLimit}
                                    onChange={(e) => setAgentLimit(Math.max(1, Math.min(50, Number(e.target.value) || 1)))}
                                    className="admin-agent-input"
                                    disabled={agentRunning}
                                />
                            </div>
                            <button
                                type="button"
                                className="admin-agent-crawl-btn"
                                disabled={agentRunning}
                                onClick={() => void startAgentCrawl()}
                            >
                                {agentRunning ? (
                                    <>
                                        <span className="admin-agent-spinner"></span>
                                        Agent đang xử lý...
                                    </>
                                ) : (
                                    <>⚡ Auto Crawl</>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Agent Flow Diagram */}
                    <AgentFlowDiagram
                        currentStep={agentCurrentStep}
                        stepStatuses={agentStepStatuses}
                        stepData={agentStepData}
                    />

                    {/* Results Table */}
                    {agentResults.length > 0 && (
                        <div className="admin-agent-results">
                            <h3 className="admin-agent-results-title">
                                📋 Kết quả ({agentResults.filter((r) => r.status === 'inserted').length} mới /
                                {' '}{agentResults.filter((r) => r.status === 'existed').length} đã tồn tại)
                            </h3>
                            <div className="admin-agent-results-grid">
                                {agentResults.map((r, i) => (
                                    <div key={i} className={`admin-agent-result-card ${r.status}`}>
                                        <img
                                            src={r.thumbnail}
                                            alt={r.title}
                                            className="admin-agent-result-thumb"
                                            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                                        />
                                        <div className="admin-agent-result-info">
                                            <p className="admin-agent-result-title">{r.title}</p>
                                            <div className="admin-agent-result-meta">
                                                <span className={`admin-agent-result-badge ${r.status}`}>
                                                    {r.status === 'inserted' ? '✅ Đã thêm' : '⏭️ Đã tồn tại'}
                                                </span>
                                                <a href={r.url} target="_blank" rel="noopener noreferrer" className="admin-agent-result-link">
                                                    Xem ↗
                                                </a>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ═════════ RESOURCE LIST (shared) ═════════ */}
            <article className="admin-res-card">
                <div className="admin-res-list-header">
                    <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="admin-res-input" style={{ width: 'auto' }}>
                        <option value="">All categories</option>
                        {ADMIN_RESOURCE_CATEGORIES.map((cat) => (
                            <option key={cat} value={cat}>{CATEGORY_LABELS[cat] || cat}</option>
                        ))}
                    </select>
                    <label className="admin-res-checkbox-label">
                        <input type="checkbox" checked={includeInactive} onChange={(e) => setIncludeInactive(e.target.checked)} />
                        include inactive
                    </label>
                    <button type="button" onClick={() => { setPage(0); void load(); }} className="admin-res-btn-outline">
                        Refresh
                    </button>
                    
                    {/* Top Pagination Numbers Removed */}
                </div>
                <div className="admin-res-list-container">
                    {loading && (
                        <div className="admin-res-loading-overlay">
                            <div className="admin-res-loading-box">
                                <div className="admin-res-spinner" />
                                <p>Đang tải dữ liệu...</p>
                            </div>
                        </div>
                    )}
                    
                    <div className={`admin-res-grid ${loading ? 'admin-res-blur' : ''}`}>
                        {resources.map((item) => (
                            <div key={item.resource_id} className="admin-res-card">
                                <div className="admin-res-card-thumb-wrapper">
                                    {item.thumbnail_key ? (
                                        <img src={item.thumbnail_key} alt={item.title} className="admin-res-card-thumb" />
                                    ) : (
                                        <div className="admin-res-card-thumb-placeholder">
                                            <span>{item.format.toUpperCase()}</span>
                                        </div>
                                    )}
                                    {item.external_url && (
                                        <a href={item.external_url} target="_blank" rel="noreferrer" className="admin-res-card-play-overlay">
                                            <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48"><path d="M8 5v14l11-7z"/></svg>
                                        </a>
                                    )}
                                    <div className="admin-res-card-badge">
                                        {CATEGORY_LABELS[item.category] || item.category}
                                    </div>
                                </div>
                                
                                <div className="admin-res-card-content">
                                    <h3 className="admin-res-card-title" title={item.title}>
                                        {item.external_url ? (
                                            <a href={item.external_url} target="_blank" rel="noreferrer">{item.title}</a>
                                        ) : item.title}
                                    </h3>
                                    <div className="admin-res-card-meta">
                                        <span>ID: {item.resource_id.slice(-8)}</span>
                                        <span>•</span>
                                        <span>{item.duration_sec}s</span>
                                        <span>•</span>
                                        <span className={item.is_active ? 'text-emerald-500' : 'text-rose-500'}>
                                            {item.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </div>
                                    
                                    <div className="admin-res-card-actions">
                                        <button type="button" onClick={() => { startEdit(item); setActiveTab('manual') }} className="admin-res-card-btn-edit">
                                            Edit
                                        </button>
                                        <button type="button" disabled={busy} onClick={() => void remove(item.resource_id)} className="admin-res-card-btn-delete">
                                            Delete
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
            </div>

            {/* Bottom Pagination Numbers */}
                {!loading && total > limit && (
                    <div className="admin-res-pagination-bottom">
                        <p className="admin-res-pagination-info">
                            Trang <b>{page + 1}</b> / {Math.ceil(total / limit)} • {total} Tài nguyên
                        </p>
                        
                        <div className="admin-res-numbers-row">
                            <button
                                onClick={() => setPage(p => Math.max(0, p - 1))}
                                disabled={page === 0 || loading}
                                className="admin-res-sq-btn"
                            >
                                ‹
                            </button>

                            {(() => {
                                const totalPages = Math.ceil(total / limit);
                                const current = page + 1;
                                const range = [];
                                
                                if (totalPages <= 7) {
                                    for (let i = 1; i <= totalPages; i++) range.push(i);
                                } else {
                                    if (current <= 4) {
                                        range.push(1, 2, 3, 4, 5, '...', totalPages);
                                    } else if (current >= totalPages - 3) {
                                        range.push(1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
                                    } else {
                                        range.push(1, '...', current - 1, current, current + 1, '...', totalPages);
                                    }
                                }

                                return range.map((p, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => typeof p === 'number' && setPage(p - 1)}
                                        disabled={loading || p === '...'}
                                        className={`admin-res-sq-btn ${p === current ? 'active' : ''} ${p === '...' ? 'dots' : ''}`}
                                    >
                                        {p}
                                    </button>
                                ));
                            })()}

                            <button
                                onClick={() => setPage(p => p + 1)}
                                disabled={(page + 1) * limit >= total || loading}
                                className="admin-res-sq-btn"
                            >
                                ›
                            </button>
                        </div>
                    </div>
                )}
            </article>
        </section>
    )
}
