import { useMemo } from 'react'

/* ─────────── Types ─────────── */
export type AgentStep = 'idle' | 'keyword_generation' | 'youtube_search' | 'content_moderation' | 'db_insertion' | 'done'
export type StepStatus = 'pending' | 'active' | 'completed' | 'error'

export type AgentStepData = {
    keywords?: string[]
    videos_found?: number
    approved?: number
    rejected?: number
    inserted?: number
    results?: AgentResult[]
}

export type AgentResult = {
    title: string
    status: 'inserted' | 'existed'
    thumbnail: string
    url: string
}

type Props = {
    currentStep: AgentStep
    stepStatuses: Record<AgentStep, StepStatus>
    stepData: Record<string, AgentStepData>
}

/* ─────────── Node config ─────────── */
const NODES = [
    { id: 'agent' as const, label: '🤖 AI Agent', desc: 'Orchestrator', x: 250, y: 30 },
    { id: 'keyword_generation' as const, label: '🔑 Keyword Gen', desc: 'Sinh từ khóa', x: 80, y: 170 },
    { id: 'youtube_search' as const, label: '🔍 YouTube Search', desc: 'Tìm video', x: 420, y: 170 },
    { id: 'content_moderation' as const, label: '🛡️ Moderator', desc: 'Kiểm duyệt AI', x: 80, y: 330 },
    { id: 'db_insertion' as const, label: '💾 DB Insert', desc: 'Lưu Database', x: 420, y: 330 },
] as const

/* Edges: from → to */
const EDGES = [
    { from: 'agent', to: 'keyword_generation' },
    { from: 'keyword_generation', to: 'youtube_search' },
    { from: 'youtube_search', to: 'content_moderation' },
    { from: 'content_moderation', to: 'db_insertion' },
]

function getNodeById(id: string) {
    return NODES.find((n) => n.id === id)
}

function getStepStatusForNode(nodeId: string, stepStatuses: Record<AgentStep, StepStatus>): StepStatus {
    if (nodeId === 'agent') {
        // Agent is active whenever anything is running
        const vals = Object.values(stepStatuses)
        if (vals.includes('active')) return 'active'
        if (stepStatuses.done === 'completed') return 'completed'
        return 'pending'
    }
    return stepStatuses[nodeId as AgentStep] ?? 'pending'
}

/* ─────────── Component ─────────── */
export default function AgentFlowDiagram({ currentStep, stepStatuses, stepData }: Props) {
    /* Memoize edge activity state */
    const edgeStates = useMemo(() => {
        return EDGES.map((edge) => {
            const fromStatus = getStepStatusForNode(edge.from, stepStatuses)
            const toStatus = getStepStatusForNode(edge.to, stepStatuses)
            const isActive = fromStatus === 'completed' && toStatus === 'active'
            const isCompleted = fromStatus === 'completed' && toStatus === 'completed'
            return { ...edge, isActive, isCompleted }
        })
    }, [stepStatuses])

    return (
        <div className="agent-flow-container">
            <div className="agent-flow-title">
                <span className="agent-flow-title-icon">⚡</span>
                Agent Workflow
                {currentStep !== 'idle' && currentStep !== 'done' && (
                    <span className="agent-flow-running-badge">Running</span>
                )}
                {currentStep === 'done' && (
                    <span className="agent-flow-done-badge">Completed</span>
                )}
            </div>

            <svg className="agent-flow-svg" viewBox="0 0 540 430" preserveAspectRatio="xMidYMid meet">
                {/* Definitions */}
                <defs>
                    {/* Glow filter for active nodes */}
                    <filter id="glow-active" x="-50%" y="-50%" width="200%" height="200%">
                        <feGaussianBlur stdDeviation="6" result="blur" />
                        <feMerge>
                            <feMergeNode in="blur" />
                            <feMergeNode in="SourceGraphic" />
                        </feMerge>
                    </filter>
                    <filter id="glow-completed" x="-50%" y="-50%" width="200%" height="200%">
                        <feGaussianBlur stdDeviation="4" result="blur" />
                        <feMerge>
                            <feMergeNode in="blur" />
                            <feMergeNode in="SourceGraphic" />
                        </feMerge>
                    </filter>

                    {/* Animated gradient for active edges */}
                    <linearGradient id="edge-active-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#34d399" stopOpacity="0">
                            <animate attributeName="offset" values="-0.3;1" dur="1.5s" repeatCount="indefinite" />
                        </stop>
                        <stop offset="30%" stopColor="#34d399" stopOpacity="1">
                            <animate attributeName="offset" values="0;1.3" dur="1.5s" repeatCount="indefinite" />
                        </stop>
                        <stop offset="60%" stopColor="#34d399" stopOpacity="0">
                            <animate attributeName="offset" values="0.3;1.6" dur="1.5s" repeatCount="indefinite" />
                        </stop>
                    </linearGradient>

                    {/* Particle (dot) animation marker */}
                    <circle id="particle-dot" r="4" fill="#34d399">
                        <animate attributeName="opacity" values="1;0.4;1" dur="0.8s" repeatCount="indefinite" />
                    </circle>
                </defs>

                {/* ───── Edges ───── */}
                {edgeStates.map((edge, i) => {
                    const fromNode = getNodeById(edge.from)
                    const toNode = getNodeById(edge.to)
                    if (!fromNode || !toNode) return null

                    const x1 = fromNode.x + 70
                    const y1 = fromNode.y + 50
                    const x2 = toNode.x + 70
                    const y2 = toNode.y + 10

                    const pathId = `edge-path-${i}`
                    const midX = (x1 + x2) / 2
                    const midY = (y1 + y2) / 2
                    const d = `M ${x1} ${y1} Q ${midX} ${midY - 15} ${x2} ${y2}`

                    return (
                        <g key={pathId}>
                            {/* Base edge */}
                            <path
                                id={pathId}
                                d={d}
                                fill="none"
                                stroke={edge.isCompleted ? '#34d39980' : edge.isActive ? '#34d39950' : '#ffffff15'}
                                strokeWidth="2"
                                strokeDasharray={edge.isActive ? '6,4' : 'none'}
                                className={edge.isActive ? 'agent-edge-dash-anim' : ''}
                            />
                            {/* Active glow overlay */}
                            {edge.isActive && (
                                <>
                                    <path d={d} fill="none" stroke="url(#edge-active-gradient)" strokeWidth="3" />
                                    {/* Animated particle */}
                                    <circle r="4" fill="#34d399" filter="url(#glow-active)">
                                        <animateMotion dur="1.5s" repeatCount="indefinite" path={d} />
                                        <animate attributeName="opacity" values="1;0.3;1" dur="0.8s" repeatCount="indefinite" />
                                    </circle>
                                    <circle r="2.5" fill="#6ee7b7">
                                        <animateMotion dur="1.5s" repeatCount="indefinite" path={d} begin="0.4s" />
                                    </circle>
                                </>
                            )}
                            {/* Completed checkmark on edge */}
                            {edge.isCompleted && (
                                <circle r="3" fill="#34d399" opacity="0.6">
                                    <animateMotion dur="2.5s" repeatCount="indefinite" path={d} />
                                </circle>
                            )}
                        </g>
                    )
                })}

                {/* ───── Nodes ───── */}
                {NODES.map((node) => {
                    const status = getStepStatusForNode(node.id, stepStatuses)
                    const isActive = status === 'active'
                    const isCompleted = status === 'completed'

                    let fillColor = 'rgba(255,255,255,0.04)'
                    let strokeColor = 'rgba(255,255,255,0.12)'
                    let textColor = 'rgba(255,255,255,0.4)'

                    if (isActive) {
                        fillColor = 'rgba(52,211,153,0.12)'
                        strokeColor = '#34d399'
                        textColor = '#6ee7b7'
                    } else if (isCompleted) {
                        fillColor = 'rgba(52,211,153,0.06)'
                        strokeColor = 'rgba(52,211,153,0.5)'
                        textColor = '#a7f3d0'
                    }

                    const nodeData = stepData[node.id] || {}

                    return (
                        <g key={node.id} filter={isActive ? 'url(#glow-active)' : isCompleted ? 'url(#glow-completed)' : undefined}>
                            {/* Node rect */}
                            <rect
                                x={node.x}
                                y={node.y}
                                width="140"
                                height="60"
                                rx="14"
                                fill={fillColor}
                                stroke={strokeColor}
                                strokeWidth={isActive ? 2 : 1}
                                className={isActive ? 'agent-node-pulse' : ''}
                            />
                            {/* Label */}
                            <text
                                x={node.x + 70}
                                y={node.y + 26}
                                textAnchor="middle"
                                fill={textColor}
                                fontSize="13"
                                fontWeight="600"
                            >
                                {node.label}
                            </text>
                            {/* Desc / Data */}
                            <text
                                x={node.x + 70}
                                y={node.y + 45}
                                textAnchor="middle"
                                fill={isCompleted ? '#a7f3d080' : 'rgba(255,255,255,0.25)'}
                                fontSize="10"
                            >
                                {isCompleted && node.id === 'keyword_generation' && nodeData.keywords
                                    ? `${nodeData.keywords.length} keywords`
                                    : isCompleted && node.id === 'youtube_search' && nodeData.videos_found != null
                                    ? `${nodeData.videos_found} videos`
                                    : isCompleted && node.id === 'content_moderation' && nodeData.approved != null
                                    ? `✓${nodeData.approved} / ✗${nodeData.rejected ?? 0}`
                                    : isCompleted && node.id === 'db_insertion' && nodeData.inserted != null
                                    ? `${nodeData.inserted} inserted`
                                    : isActive
                                    ? 'Processing...'
                                    : node.desc}
                            </text>
                            {/* Status indicator */}
                            {isCompleted && (
                                <circle cx={node.x + 130} cy={node.y + 10} r="6" fill="#34d399">
                                    <animate attributeName="opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite" />
                                </circle>
                            )}
                            {isActive && (
                                <circle cx={node.x + 130} cy={node.y + 10} r="5" fill="#fbbf24">
                                    <animate attributeName="r" values="4;6;4" dur="1s" repeatCount="indefinite" />
                                    <animate attributeName="opacity" values="1;0.5;1" dur="1s" repeatCount="indefinite" />
                                </circle>
                            )}
                        </g>
                    )
                })}
            </svg>

            {/* Data preview under the diagram */}
            {stepData.keyword_generation?.keywords && (
                <div className="agent-flow-data-row">
                    <span className="agent-flow-data-label">🔑 Keywords:</span>
                    <div className="agent-flow-keyword-chips">
                        {stepData.keyword_generation.keywords.map((kw, i) => (
                            <span key={i} className="agent-flow-chip">{kw}</span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
